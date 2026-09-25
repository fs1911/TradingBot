"""
TradingBot — Main Orchestrator
────────────────────────────────────────────────────────────────────────────
The Bot class:
1. Loads all configuration
2. Initialises the broker adapter, strategies, risk manager, and reporter
3. Runs a continuous main loop:
   a. Fetch OHLCV data for each configured symbol
   b. Compute technical indicators
   c. Run all active strategies → collect signals
   d. Fuse signals (require multi-strategy agreement)
   e. Gate each signal through the risk manager
   f. Execute approved entries via the broker
   g. Monitor open positions (trailing stops, exits)
   h. Record results → performance reporter
4. Emits a daily report via Telegram (optional)
5. Runs weekly self-improvement hints
"""
from __future__ import annotations
import json
import math
import os
import time
import signal
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from loguru import logger

from .utils.helpers import load_config
from .utils.logger import setup_logger
from .indicators.technical import add_all_indicators
from .strategies.base_strategy import Signal, SignalType
from .strategies.ema_crossover import EMACrossoverStrategy
from .strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from .strategies.macd_momentum import MACDMomentumStrategy
from .strategies.bollinger_bounce import BollingerBounceStrategy
from .strategies.vwap_reversion import VWAPReversionStrategy
from .strategies.supertrend import SupertrendStrategy
from .strategies.breakout_momentum import BreakoutMomentumStrategy
from .strategies.congress_trades import CongressTradesStrategy
from .strategies.opening_range_breakout import LondonORBStrategy, NewYorkORBStrategy
from .strategies.judas_swing import JudasSwingStrategy
from .strategies.silver_bullet import SilverBulletStrategy
from .risk.risk_manager import RiskManager
from .data.news_sentiment import SentimentAnalyzer
from .monitoring.reporter import PerformanceReporter
from .monitoring.telegram_notifier import TelegramNotifier
from .monitoring.auto_tuner import AutoTuner
from .monitoring.journal_sync import JournalSyncer
from .monitoring.heartbeat import Heartbeat
from .brokers.base_broker import BaseBroker, Order, OrderSide, OrderType


STRATEGY_REGISTRY = {
    "ema_crossover": EMACrossoverStrategy,
    "rsi_mean_reversion": RSIMeanReversionStrategy,
    "macd_momentum": MACDMomentumStrategy,
    "bollinger_bounce": BollingerBounceStrategy,
    "vwap_reversion": VWAPReversionStrategy,
    "supertrend": SupertrendStrategy,
    "breakout_momentum": BreakoutMomentumStrategy,
    "congress_mirror": CongressTradesStrategy,
    "london_orb": LondonORBStrategy,
    "newyork_orb": NewYorkORBStrategy,
    "judas_swing": JudasSwingStrategy,
    "silver_bullet": SilverBulletStrategy,
}


class TradingBot:
    """Main trading bot — initialise once and call run()."""

    def __init__(self, config_override: Optional[dict] = None):
        # Load config files
        self.bot_cfg = load_config("bot_config")
        self.strategy_cfg = load_config("strategy_config")
        self.risk_cfg = load_config("risk_config")
        if config_override:
            self._merge(self.bot_cfg, config_override)

        # (Auto-tuned parameter overlay removed 2026-08-06 — tuning is gone,
        #  the AutoTuner is detection-only now.)

        env = self.bot_cfg["bot"].get("environment", "paper")
        log_level = os.environ.get("LOG_LEVEL", "INFO")
        setup_logger(log_level=log_level)
        logger.info(f"TradingBot initialising — environment={env}")

        # Broker
        self.broker = self._init_broker()

        # Strategies
        active = self.bot_cfg.get("active_strategies", ["ema_crossover"])
        self.strategies = []
        for name in active:
            if name not in STRATEGY_REGISTRY:
                logger.warning(f"Unknown strategy: {name}")
                continue
            params = self.strategy_cfg.get(name, {})
            self.strategies.append(STRATEGY_REGISTRY[name](params))
            logger.info(f"Strategy loaded: {name}")

        # Risk manager
        self.risk_manager = RiskManager(self.risk_cfg)

        # Auxiliary
        self.sentiment = SentimentAnalyzer()
        self.reporter = PerformanceReporter()
        self.telegram = TelegramNotifier()

        # Self-learning components (initialised after strategies are built)
        _cfg_root = Path(__file__).parent.parent / "config"
        _log_root = Path(__file__).parent.parent / "logs"
        self.auto_tuner = AutoTuner(
            base_config_path=_cfg_root / "strategy_config.yaml",
            tuned_config_path=_cfg_root / "strategy_config_tuned.yaml",
            journal_path=_log_root / "trading_journal.csv",
            strategies=self.strategies,
            telegram=self.telegram,
        )
        self.journal_syncer = JournalSyncer(
            journal_path=_log_root / "trading_journal.csv",
        )
        self.heartbeat = Heartbeat()
        self._last_heartbeat: Optional[datetime] = None
        self._equity_history_path = _log_root / "equity_history.csv"
        self._pnl_baseline: Optional[float] = None  # equity when tracking began

        # Config shortcuts
        broker_key = self.bot_cfg.get("broker", "alpaca")
        self.market_cfg = self.bot_cfg.get("markets", {}).get(broker_key, {})
        self.symbols: list[str] = self.market_cfg.get("symbols", [])
        self.timeframe: str = self.market_cfg.get("timeframe", "1Hour")
        self.loop_interval = self.bot_cfg["bot"].get("loop_interval_seconds", 60)

        # State
        self._running = False
        self._open_trades: dict[str, dict] = {}   # symbol → trade info
        self._last_daily_report: str = ""
        self._last_morning_report: str = ""
        self._market_trend: str = "neutral"       # Updated each tick from SPY
        self._cooldown_path = Path(__file__).parent.parent / "logs" / "sl_cooldowns.json"
        self._sl_cooldown: dict[str, datetime] = self._load_sl_cooldowns()

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Sync any positions already open on the broker (survive restarts)
        self._load_existing_positions()
        self.telegram.startup(self.symbols, self.timeframe)

        logger.info(f"TradingBot ready — symbols={self.symbols}, timeframe={self.timeframe}")

    # ── Public entry point ────────────────────────────────────────────────────

    def _run_startup_backtest(self) -> None:
        """One-off out-of-sample backtest of the active strategies on real Alpaca
        history, pushed to GitHub as backtest_results.md. Runs in a background
        thread so it never blocks trading. The honest edge test.

        Runs the OOS test PER ASSET CLASS (equities / metals / energy / crypto)
        so we can see whether an edge exists in a specific market — not just the
        crypto-pooled result. An asset class only earns live trading if a
        strategy survives OOS here."""
        try:
            from .backtest.oos_runner import run_and_report
            active = self.bot_cfg.get("active_strategies", [])
            universes = self.bot_cfg.get("backtest_universes")
            # Fallback to the old crypto-only behaviour if no universes configured
            if not universes:
                universes = {"crypto": [s for s in self.symbols if "/" in s]}

            sections = [f"# Grouped OOS Edge Test — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
                        "",
                        "Same honest out-of-sample test, run separately per asset class. "
                        "A strategy earns live trading only if its edge survives OOS "
                        "(PF > 1.15, positive expectancy) net of costs.", ""]
            for group, syms in universes.items():
                logger.info(f"Startup backtest: OOS on '{group}' ({len(syms)} symbols)…")
                report = run_and_report(
                    get_ohlcv=self.broker.get_ohlcv,
                    active_strategies=active,
                    registry=STRATEGY_REGISTRY,
                    strategy_cfg=self.strategy_cfg,
                    symbols=syms,
                    timeframe=self.timeframe,
                )
                sections.append(f"## {group.upper()}")
                sections.append(report)
                sections.append("")
            full = "\n".join(sections)
            self.heartbeat._put_file("backtest_results.md", full.encode(),
                                     "Grouped OOS edge test (equities/metals/energy/crypto)")
            logger.info("Startup backtest: grouped report pushed to backtest_results.md")
        except Exception as e:
            logger.error(f"Startup backtest failed: {e}")

    def _run_trend_backtest(self) -> None:
        """Daily-bar trend-following edge test on real Alpaca history, pushed to
        GitHub as trend_backtest_results.md. Background thread. Tests whether the
        one retail hypothesis with documented merit — long-horizon trend/momentum
        — survives out-of-sample on equities/metals/energy/crypto."""
        try:
            from .backtest.trend_follow import run_trend_report
            universes = self.bot_cfg.get("backtest_universes")
            if not universes:
                universes = {"crypto": [s for s in self.symbols if "/" in s]}
            logger.info(f"Trend backtest: daily OOS on {len(universes)} asset classes…")
            report = run_trend_report(get_ohlcv=self.broker.get_ohlcv, universes=universes)
            self.heartbeat._put_file("trend_backtest_results.md", report.encode(),
                                     "Daily trend-following edge test (equities/metals/energy/crypto)")
            logger.info("Trend backtest: report pushed to trend_backtest_results.md")
        except Exception as e:
            logger.error(f"Trend backtest failed: {e}")

    def _run_benchmark(self) -> None:
        """The decisive test: daily trend systems vs simple Buy&Hold per asset
        class, on return AND drawdown, pushed to benchmark_results.md. Separates a
        real (risk-adjusted) edge from market beta on a hindsight-selected universe."""
        try:
            from .backtest.trend_follow import run_benchmark_report
            universes = self.bot_cfg.get("backtest_universes")
            if not universes:
                universes = {"crypto": [s for s in self.symbols if "/" in s]}
            logger.info(f"Benchmark: Trend vs Buy&Hold on {len(universes)} asset classes…")
            report = run_benchmark_report(get_ohlcv=self.broker.get_ohlcv, universes=universes)
            self.heartbeat._put_file("benchmark_results.md", report.encode(),
                                     "Trend vs Buy&Hold benchmark (equities/metals/energy/crypto)")
            logger.info("Benchmark: report pushed to benchmark_results.md")
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")

    def _run_experiment40(self) -> None:
        """Experiment #40: trend following across asset classes (broad ETF universe and
        long mutual-fund universe). Yahoo adjclose, 20s timeouts.
        → experiment40_results.md."""
        try:
            from .backtest.experiments_35 import fetch_yahoo_daily
            from .backtest.experiments_40 import run_experiment40_report
            cfg = self.bot_cfg.get("experiment40", {})
            universes = {}
            for name, spec in cfg.get("universes", {}).items():
                prices = {t: fetch_yahoo_daily(t, "1970-01-01", timeout=20)
                          for t in spec.get("tickers", [])}
                universes[name] = (prices, spec.get("equity", ""))
            irx = fetch_yahoo_daily("^IRX", "1970-01-01", timeout=20)
            report = run_experiment40_report(universes, irx)
            self.heartbeat._put_file("experiment40_results.md", report.encode(),
                                     "Experiment #40: multi-asset trend following")
            logger.info("Experiment #40: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #40 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment40_results.md",
                                         f"# Experiment #40 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #40 failure traceback")
            except Exception:
                pass

    def _run_experiment39(self) -> None:
        """Experiment #39: PutWrite + trend — Sharpe-difference bootstrap, equal-risk
        leverage, robustness grid. Yahoo, 20s timeouts. → experiment39_results.md."""
        try:
            from .backtest.experiments_35 import fetch_yahoo_daily
            from .backtest.experiments_39 import run_experiment39_report
            series = {"PUT": fetch_yahoo_daily("^PUT", "1986-01-01", timeout=20),
                      "SP500TR": fetch_yahoo_daily("^SP500TR", "1987-12-01", timeout=20),
                      "IRX": fetch_yahoo_daily("^IRX", "1986-01-01", timeout=20)}
            report = run_experiment39_report(series)
            self.heartbeat._put_file("experiment39_results.md", report.encode(),
                                     "Experiment #39: is PutWrite+trend really better")
            logger.info("Experiment #39: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #39 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment39_results.md",
                                         f"# Experiment #39 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #39 failure traceback")
            except Exception:
                pass

    def _run_experiment38(self) -> None:
        """Experiment #38: PutWrite premium + 200d trend insurance combinations vs
        S&P 500 TR, with T-bill cash. Yahoo, 20s timeouts. → experiment38_results.md."""
        try:
            from .backtest.experiments_35 import fetch_yahoo_daily
            from .backtest.experiments_38 import run_experiment38_report
            series = {"PUT": fetch_yahoo_daily("^PUT", "1986-01-01", timeout=20),
                      "SP500TR": fetch_yahoo_daily("^SP500TR", "1987-12-01", timeout=20),
                      "IRX": fetch_yahoo_daily("^IRX", "1986-01-01", timeout=20)}
            report = run_experiment38_report(series)
            self.heartbeat._put_file("experiment38_results.md", report.encode(),
                                     "Experiment #38: premium + insurance combined")
            logger.info("Experiment #38: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #38 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment38_results.md",
                                         f"# Experiment #38 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #38 failure traceback")
            except Exception:
                pass

    def _run_experiment37(self) -> None:
        """Experiment #37: volatility risk premium — VIX vs realised vol since 1990,
        PutWrite/BuyWrite/SVXY vs S&P 500 TR. Yahoo, 20s timeouts.
        → experiment37_results.md."""
        try:
            from .backtest.experiments_35 import fetch_yahoo_daily
            from .backtest.experiments_37 import run_experiment37_report
            syms = {"VIX": ("^VIX", "1990-01-01"), "GSPC": ("^GSPC", "1989-11-01"),
                    "SP500TR": ("^SP500TR", "1987-12-01"), "PUT": ("^PUT", "1986-01-01"),
                    "BXM": ("^BXM", "1986-01-01"), "SVXY": ("SVXY", "2011-01-01")}
            series = {k: fetch_yahoo_daily(sym, start, timeout=20) for k, (sym, start) in syms.items()}
            report = run_experiment37_report(series)
            self.heartbeat._put_file("experiment37_results.md", report.encode(),
                                     "Experiment #37: volatility risk premium")
            logger.info("Experiment #37: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #37 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment37_results.md",
                                         f"# Experiment #37 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #37 failure traceback")
            except Exception:
                pass

    def _run_experiment36(self) -> None:
        """Experiment #36: calendar anomalies on daily S&P 500 since 1927, before vs
        after publication. 20s timeout. → experiment36_results.md."""
        try:
            from .backtest.experiments_35 import fetch_yahoo_daily
            from .backtest.experiments_36 import run_experiment36_report
            close = fetch_yahoo_daily("^GSPC", "1927-12-01", timeout=20)
            report = run_experiment36_report(close)
            self.heartbeat._put_file("experiment36_results.md", report.encode(),
                                     "Experiment #36: calendar anomalies before/after publication")
            logger.info("Experiment #36: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #36 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment36_results.md",
                                         f"# Experiment #36 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #36 failure traceback")
            except Exception:
                pass

    def _run_experiment35(self) -> None:
        """Experiment #35: trend filter on Shiller monthly averages vs true month-end
        S&P 500 closes since 1927 (Working-effect check). 20s timeouts.
        → experiment35_results.md."""
        try:
            from .backtest.experiments_34 import fetch_shiller
            from .backtest.experiments_35 import fetch_yahoo_daily, run_experiment35_report
            shiller, _ = fetch_shiller(timeout=20)
            daily = fetch_yahoo_daily("^GSPC", "1927-12-01", timeout=20)
            report = run_experiment35_report(shiller, daily)
            self.heartbeat._put_file("experiment35_results.md", report.encode(),
                                     "Experiment #35: averaging artefact check")
            logger.info("Experiment #35: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #35 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment35_results.md",
                                         f"# Experiment #35 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #35 failure traceback")
            except Exception:
                pass

    def _run_experiment34(self) -> None:
        """Experiment #34: Shiller CAPE since 1871 — predictive power, CAPE-conditional
        trend filter, CAPE-based allocation. 20s download timeout.
        → experiment34_results.md."""
        try:
            from .backtest.experiments_34 import fetch_shiller, run_experiment34_report
            df, src = fetch_shiller(timeout=20)
            report = run_experiment34_report(df, src)
            self.heartbeat._put_file("experiment34_results.md", report.encode(),
                                     "Experiment #34: Shiller CAPE")
            logger.info("Experiment #34: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #34 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment34_results.md",
                                         f"# Experiment #34 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #34 failure traceback")
            except Exception:
                pass

    def _run_experiment33(self) -> None:
        """Experiment #33: trend filter with T-bill cash yield, dividends, SMA
        robustness and trend-aware savings plans. Long history via the #32 fetcher
        (20s timeout). → experiment33_results.md."""
        try:
            from .backtest.experiments_32 import fetch_long_history
            from .backtest.experiments_33 import run_experiment33_report
            cfg = self.bot_cfg.get("experiment33", {})
            assets = cfg.get("assets", [])
            irx, _ = fetch_long_history("", cfg.get("cash_yahoo", "^IRX"), timeout=20)

            def fetch(a: dict):
                return fetch_long_history(a.get("stooq", ""), a.get("yahoo", ""), timeout=20)

            report = run_experiment33_report(fetch=fetch, assets=assets, irx=irx)
            self.heartbeat._put_file("experiment33_results.md", report.encode(),
                                     "Experiment #33: trend filter judged fairly")
            logger.info("Experiment #33: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #33 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment33_results.md",
                                         f"# Experiment #33 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #33 failure traceback")
            except Exception:
                pass

    def _run_experiment32(self) -> None:
        """Experiment #32: decades of index history (Stooq → Yahoo, 20s timeout) —
        drawdown signal at -20/-35/-50% and trend filters vs buy & hold.
        → experiment32_results.md."""
        try:
            from .backtest.experiments_32 import fetch_long_history, run_experiment32_report
            cfg = self.bot_cfg.get("experiment32", {})
            assets = cfg.get("assets", [])

            def fetch(a: dict):
                return fetch_long_history(a.get("stooq", ""), a.get("yahoo", ""), timeout=20)

            report = run_experiment32_report(fetch=fetch, assets=assets,
                                             horizon=int(cfg.get("horizon", 90)))
            self.heartbeat._put_file("experiment32_results.md", report.encode(),
                                     "Experiment #32: decades of history")
            logger.info("Experiment #32: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #32 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment32_results.md",
                                         f"# Experiment #32 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #32 failure traceback")
            except Exception:
                pass

    def _run_experiment31(self) -> None:
        """Experiment #31: stress test of the deep-drawdown signal (baseline, episodes,
        OOS halves, broader universe, DCA vs dip-reserve). Native broker prices.
        → experiment31_results.md."""
        try:
            import pandas as pd
            from .backtest.experiments_31 import run_experiment31_report
            cfg = self.bot_cfg.get("experiment31", {})
            symbols = cfg.get("symbols", ["SPY", "QQQ", "BTC/USD", "ETH/USD"])
            horizon = int(cfg.get("horizon", 90))

            def fetch_prices(sym: str) -> pd.Series:
                df = self.broker.get_ohlcv(sym, "1Day", 2500)
                if df is None or len(df) == 0:
                    return pd.Series(dtype=float)
                return df["close"].sort_index()

            report = run_experiment31_report(fetch_prices=fetch_prices, symbols=symbols,
                                             horizon=horizon)
            self.heartbeat._put_file("experiment31_results.md", report.encode(),
                                     "Experiment #31: drawdown signal stress test")
            logger.info("Experiment #31: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #31 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment31_results.md",
                                         f"# Experiment #31 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #31 failure traceback")
            except Exception:
                pass

    def _run_experiment30(self) -> None:
        """Experiment #30: valuation gauges (drawdown-from-ATH & 200d MA) as a
        Finanzradar overlay. Uses the native broker price path (no ccxt).
        → experiment30_results.md."""
        try:
            import pandas as pd
            from .backtest.experiments_30 import run_experiment30_report
            cfg = self.bot_cfg.get("experiment30", {})
            symbols = cfg.get("symbols", ["SPY", "QQQ", "BTC/USD", "ETH/USD"])
            horizon = int(cfg.get("horizon", 90))

            def fetch_prices(sym: str) -> pd.Series:
                df = self.broker.get_ohlcv(sym, "1Day", 2500)
                if df is None or len(df) == 0:
                    return pd.Series(dtype=float)
                return df["close"].sort_index()

            report = run_experiment30_report(fetch_prices=fetch_prices, symbols=symbols,
                                             horizon=horizon)
            self.heartbeat._put_file("experiment30_results.md", report.encode(),
                                     "Experiment #30: valuation gauges for Finanzradar")
            logger.info("Experiment #30: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #30 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment30_results.md",
                                         f"# Experiment #30 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #30 failure traceback")
            except Exception:
                pass

    def _run_experiment29(self) -> None:
        """Experiment #29: funding rate as a froth gauge — a Finanzradar sentiment
        signal (predictive buckets + a 'step aside when hot' filter).
        → experiment29_results.md."""
        try:
            import pandas as pd
            from .backtest.experiments_24 import open_swap_exchange, page_funding_history
            from .backtest.experiments_29 import run_experiment29_report
            cfg = self.bot_cfg.get("experiment29", {})
            symbols = cfg.get("symbols", ["BTC/USDT:USDT", "ETH/USDT:USDT"])
            exchanges = cfg.get("exchanges", ["bybit", "binance", "okx"])
            ex = exid = None
            for cand in exchanges:
                try:
                    e = open_swap_exchange(cand)
                    if len(page_funding_history(e, "BTC/USDT:USDT")) > 100:
                        ex, exid = e, cand
                        break
                except Exception as err:
                    logger.warning(f"Exp29: exchange {cand} unusable: {err}")
            if ex is None:
                raise RuntimeError("No usable exchange for funding+prices")

            def fetch_funding(sym: str) -> pd.Series:
                return page_funding_history(ex, sym)

            def fetch_prices(sym: str) -> pd.Series:
                ohlcv = ex.fetch_ohlcv(sym, "1d", limit=1500)
                if not ohlcv:
                    return pd.Series(dtype=float)
                return pd.Series({pd.to_datetime(r[0], unit="ms", utc=True): float(r[4])
                                  for r in ohlcv if r[4] is not None}).sort_index()

            report = run_experiment29_report(fetch_funding=fetch_funding,
                                             fetch_prices=fetch_prices, symbols=symbols)
            report = report.replace("signal) (", f"signal) [data: {exid}] (", 1)
            self.heartbeat._put_file("experiment29_results.md", report.encode(),
                                     "Experiment #29: funding froth signal")
            logger.info(f"Experiment #29: report pushed (exchange={exid})")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #29 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment29_results.md",
                                         f"# Experiment #29 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #29 failure traceback")
            except Exception:
                pass

    def _run_experiment28(self) -> None:
        """Experiment #28: dated quarterly-futures calendar basis — low-turnover carry
        AND a Finanzradar froth signal (basis vs forward returns).
        → experiment28_results.md."""
        try:
            from .backtest.experiments_28 import (
                build_dated_basis_fetcher, run_experiment28_report)
            cfg = self.bot_cfg.get("experiment28", {})
            symbols = cfg.get("symbols", ["BTC/USDT:USDT", "ETH/USDT:USDT"])
            exchanges = tuple(cfg.get("exchanges", ["okx", "binance", "bybit"]))
            fetch_basis = build_dated_basis_fetcher(exchanges=exchanges)
            report = run_experiment28_report(fetch_basis=fetch_basis, symbols=symbols)
            self.heartbeat._put_file("experiment28_results.md", report.encode(),
                                     "Experiment #28: dated-futures calendar basis")
            logger.info("Experiment #28: report pushed")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #28 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment28_results.md",
                                         f"# Experiment #28 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #28 failure traceback")
            except Exception:
                pass

    def _run_experiment27(self) -> None:
        """Experiment #27: cross-exchange funding differential (low-turnover,
        perp-vs-perp carry) through the full rigor battery. → experiment27_results.md."""
        try:
            from .backtest.experiments_24 import open_swap_exchange, page_funding_history
            from .backtest.experiments_27 import run_experiment27_report
            cfg = self.bot_cfg.get("experiment27", {})
            symbols = cfg.get("symbols", ["BTC/USDT:USDT", "ETH/USDT:USDT"])
            exchanges = cfg.get("exchanges", ["bybit", "binance", "okx"])
            clients = {}
            for exid in exchanges:
                try:
                    clients[exid] = open_swap_exchange(exid)
                except Exception as e:
                    logger.warning(f"Exp27: exchange {exid} unusable: {e}")
            if len(clients) < 2:
                raise RuntimeError(f"Need ≥2 usable exchanges, got {list(clients)}")

            def fetch_multi(symbol: str) -> dict:
                out = {}
                for exid, ex in clients.items():
                    try:
                        s = page_funding_history(ex, symbol)
                        if len(s):
                            out[exid] = s
                    except Exception:
                        pass
                return out

            report = run_experiment27_report(fetch_multi=fetch_multi, symbols=symbols)
            report = report.replace("differential (", f"differential [venues: "
                                    f"{','.join(clients)}] (", 1)
            self.heartbeat._put_file("experiment27_results.md", report.encode(),
                                     "Experiment #27: cross-exchange funding differential")
            logger.info(f"Experiment #27: report pushed (venues={list(clients)})")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #27 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment27_results.md",
                                         f"# Experiment #27 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #27 failure traceback")
            except Exception:
                pass

    def _run_experiment26(self) -> None:
        """Experiment #26: broader / cross-sectional structural carry (broad basket,
        carry-weighted tilt, dispersion spread) through the full rigor battery.
        → experiment26_results.md."""
        try:
            from .backtest.experiments_24 import build_ccxt_funding_fetcher
            from .backtest.experiments_26 import run_experiment26_report
            cfg = self.bot_cfg.get("experiment26", {})
            symbols = cfg.get("symbols", ["BTC/USDT:USDT", "ETH/USDT:USDT"])
            exchanges = tuple(cfg.get("exchanges",
                              self.bot_cfg.get("experiment24", {}).get("exchanges",
                              ["bybit", "binance", "okx"])))
            fetch_funding, exid = build_ccxt_funding_fetcher(exchange_ids=exchanges)
            report = run_experiment26_report(fetch_funding=fetch_funding, symbols=symbols)
            report = report.replace("carry (", f"carry [data: {exid}] (", 1)
            self.heartbeat._put_file("experiment26_results.md", report.encode(),
                                     "Experiment #26: broader structural carry")
            logger.info(f"Experiment #26: report pushed (exchange={exid})")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #26 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment26_results.md",
                                         f"# Experiment #26 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #26 failure traceback")
            except Exception:
                pass

    def _run_experiment25(self) -> None:
        """Experiment #25: funding carry net of a concrete Bybit-style cost model
        plus the capital required for a target income. → experiment25_results.md."""
        try:
            from .backtest.experiments_24 import build_ccxt_funding_fetcher
            from .backtest.experiments_25 import run_experiment25_report
            cfg = self.bot_cfg.get("experiment25", {})
            symbols = cfg.get("symbols", self.bot_cfg.get("experiment24", {}).get(
                "symbols", ["BTC/USDT:USDT", "ETH/USDT:USDT", "DOGE/USDT:USDT"]))
            exchanges = tuple(cfg.get("exchanges",
                              self.bot_cfg.get("experiment24", {}).get("exchanges",
                              ["bybit", "binance", "okx"])))
            target = float(cfg.get("target_annual_chf", 3650.0))
            spot_vol = float(cfg.get("spot_vol_annual", 0.6))
            fetch_funding, exid = build_ccxt_funding_fetcher(exchange_ids=exchanges)
            report = run_experiment25_report(fetch_funding=fetch_funding, symbols=symbols,
                                             spot_vol_annual=spot_vol, target_annual=target)
            report = report.replace("costs (", f"costs [data: {exid}] (", 1)
            self.heartbeat._put_file("experiment25_results.md", report.encode(),
                                     "Experiment #25: funding carry net of costs")
            logger.info(f"Experiment #25: report pushed (exchange={exid})")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #25 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment25_results.md",
                                         f"# Experiment #25 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #25 failure traceback")
            except Exception:
                pass

    def _run_experiment24(self) -> None:
        """Experiment #24: crypto funding-rate carry (delta-neutral, structural
        premium). Fetches public perpetual funding history via ccxt and runs the
        daily carry through the full rigor battery. → experiment24_results.md."""
        try:
            from .backtest.experiments_24 import (
                build_ccxt_funding_fetcher, run_experiment24_report)
            cfg = self.bot_cfg.get("experiment24", {})
            symbols = cfg.get("symbols", ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"])
            exchanges = tuple(cfg.get("exchanges", ["bybit", "binance", "okx"]))
            fetch_funding, exid = build_ccxt_funding_fetcher(exchange_ids=exchanges)
            report = run_experiment24_report(fetch_funding=fetch_funding, symbols=symbols)
            report = report.replace("carry (", f"carry [data: {exid}] (", 1)
            self.heartbeat._put_file("experiment24_results.md", report.encode(),
                                     "Experiment #24: crypto funding-rate carry")
            logger.info(f"Experiment #24: report pushed (exchange={exid})")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #24 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment24_results.md",
                                         f"# Experiment #24 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #24 failure traceback")
            except Exception:
                pass

    def _run_experiment23(self) -> None:
        """Experiment #23: rebalancing premium (volatility harvesting) — excess of
        periodically-rebalanced equal weight over buy&hold, through the full rigor
        battery. → experiment23_results.md."""
        try:
            from .backtest.experiments_23 import run_experiment23_report
            universe = self.bot_cfg.get("experiment23", {}).get(
                "universe", self.bot_cfg.get("experiment20", {}).get("universe", []))
            report = run_experiment23_report(get_ohlcv=self.broker.get_ohlcv, universe=universe)
            self.heartbeat._put_file("experiment23_results.md", report.encode(),
                                     "Experiment #23: rebalancing premium")
            logger.info("Experiment #23: report pushed to experiment23_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #23 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment23_results.md",
                                         f"# Experiment #23 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #23 failure traceback")
            except Exception:
                pass

    def _run_experiment22(self) -> None:
        """Experiment #22: is long-only momentum alpha or beta? Excess return over
        an equal-weight-universe benchmark through the full rigor battery.
        → experiment22_results.md."""
        try:
            from .backtest.experiments_22 import run_experiment22_report
            universe = self.bot_cfg.get("experiment22", {}).get(
                "universe", self.bot_cfg.get("experiment20", {}).get("universe", []))
            report = run_experiment22_report(get_ohlcv=self.broker.get_ohlcv, universe=universe)
            self.heartbeat._put_file("experiment22_results.md", report.encode(),
                                     "Experiment #22: long-only momentum alpha vs beta")
            logger.info("Experiment #22: report pushed to experiment22_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #22 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment22_results.md",
                                         f"# Experiment #22 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #22 failure traceback")
            except Exception:
                pass

    def _run_experiment21(self) -> None:
        """Experiment #21: momentum refinements (vol-scaled / residual / vol-managed /
        regime-filtered / long-only) through the full rigor battery.
        → experiment21_results.md."""
        try:
            from .backtest.experiments_21 import run_experiment21_report
            universe = self.bot_cfg.get("experiment21", {}).get(
                "universe", self.bot_cfg.get("experiment20", {}).get("universe", []))
            report = run_experiment21_report(get_ohlcv=self.broker.get_ohlcv, universe=universe)
            self.heartbeat._put_file("experiment21_results.md", report.encode(),
                                     "Experiment #21: momentum refinements")
            logger.info("Experiment #21: report pushed to experiment21_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #21 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment21_results.md",
                                         f"# Experiment #21 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #21 failure traceback")
            except Exception:
                pass

    def _run_experiment20(self) -> None:
        """Experiment #20: cross-sectional long/short over many individual stocks
        (short-term reversal + 12-1 momentum) through the full rigor battery.
        → experiment20_results.md."""
        try:
            from .backtest.experiments_20 import run_experiment20_report
            universe = self.bot_cfg.get("experiment20", {}).get("universe", [])
            report = run_experiment20_report(get_ohlcv=self.broker.get_ohlcv, universe=universe)
            self.heartbeat._put_file("experiment20_results.md", report.encode(),
                                     "Experiment #20: cross-sectional long/short")
            logger.info("Experiment #20: report pushed to experiment20_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #20 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment20_results.md",
                                         f"# Experiment #20 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #20 failure traceback")
            except Exception:
                pass

    def _run_experiment19(self) -> None:
        """Experiment #19: broad-universe scan (indices/sectors/metals/energy/
        agriculture/currencies/bonds/crypto) — structure diagnostics + RSI(2) through
        the full rigor battery. → experiment19_results.md."""
        try:
            from .backtest.experiments_19 import run_experiment19_report
            groups = self.bot_cfg.get("experiment19", {}).get("groups", {})
            report = run_experiment19_report(get_ohlcv=self.broker.get_ohlcv, groups=groups)
            self.heartbeat._put_file("experiment19_results.md", report.encode(),
                                     "Experiment #19: broad-universe scan")
            logger.info("Experiment #19: report pushed to experiment19_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #19 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment19_results.md",
                                         f"# Experiment #19 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #19 failure traceback")
            except Exception:
                pass

    def _run_experiment18(self) -> None:
        """Experiment #18: intraday (5-min) mean reversion — a new data regime,
        judged by the full rigor battery. → experiment18_results.md."""
        try:
            from .backtest.experiments_18 import run_experiment18_report
            cfg = self.bot_cfg.get("experiment18", {})
            report = run_experiment18_report(
                get_ohlcv=self.broker.get_ohlcv,
                symbols=cfg.get("symbols", ["SPY", "QQQ", "BTC/USD"]),
                timeframe=cfg.get("timeframe", "5Min"))
            self.heartbeat._put_file("experiment18_results.md", report.encode(),
                                     "Experiment #18: intraday mean reversion")
            logger.info("Experiment #18: report pushed to experiment18_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #18 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment18_results.md",
                                         f"# Experiment #18 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #18 failure traceback")
            except Exception:
                pass

    def _run_experiment17(self) -> None:
        """Experiment #17: regime-conditional RSI(2) mean reversion (apply only in
        high-vol regime) — can conditioning rescue the real-but-weak effect?
        → experiment17_results.md."""
        try:
            from .backtest.experiments_17 import run_experiment17_report
            symbols = self.bot_cfg.get("experiment17", {}).get("symbols", ["SPY", "QQQ"])
            report = run_experiment17_report(get_ohlcv=self.broker.get_ohlcv, symbols=symbols)
            self.heartbeat._put_file("experiment17_results.md", report.encode(),
                                     "Experiment #17: regime-conditional mean reversion")
            logger.info("Experiment #17: report pushed to experiment17_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #17 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment17_results.md",
                                         f"# Experiment #17 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #17 failure traceback")
            except Exception:
                pass

    def _run_experiment16(self) -> None:
        """Experiment #16: volume-based signals + stocks/bonds dual momentum,
        under the full rigor battery. → experiment16_results.md."""
        try:
            from .backtest.experiments_16 import run_experiment16_report
            cfg = self.bot_cfg.get("experiment16", {})
            report = run_experiment16_report(
                get_ohlcv=self.broker.get_ohlcv,
                volume_symbols=cfg.get("volume_symbols", []),
                dual_momentum=cfg.get("dual_momentum"),
            )
            self.heartbeat._put_file("experiment16_results.md", report.encode(),
                                     "Experiment #16: volume signals + dual momentum")
            logger.info("Experiment #16: report pushed to experiment16_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #16 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment16_results.md",
                                         f"# Experiment #16 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #16 failure traceback")
            except Exception:
                pass

    def _run_experiment15(self) -> None:
        """Experiment #15: walk-forward logistic-regression ML on price features,
        judged by the full rigor battery. → experiment15_results.md."""
        try:
            from .backtest.experiments_15 import run_experiment15_report
            symbols = self.bot_cfg.get("experiment15", {}).get("symbols", ["SPY", "QQQ"])
            report = run_experiment15_report(get_ohlcv=self.broker.get_ohlcv, symbols=symbols)
            self.heartbeat._put_file("experiment15_results.md", report.encode(),
                                     "Experiment #15: machine-learning prediction")
            logger.info("Experiment #15: report pushed to experiment15_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #15 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment15_results.md",
                                         f"# Experiment #15 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #15 failure traceback")
            except Exception:
                pass

    def _run_experiment14(self) -> None:
        """Experiment #14 (final agenda item): volatility-targeting risk overlay vs
        buy-and-hold. → experiment14_results.md."""
        try:
            from .backtest.experiments_14 import run_experiment14_report
            symbols = self.bot_cfg.get("experiment14", {}).get("symbols", ["SPY", "QQQ", "BTC/USD"])
            report = run_experiment14_report(get_ohlcv=self.broker.get_ohlcv, symbols=symbols)
            self.heartbeat._put_file("experiment14_results.md", report.encode(),
                                     "Experiment #14: volatility targeting")
            logger.info("Experiment #14: report pushed to experiment14_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #14 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment14_results.md",
                                         f"# Experiment #14 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #14 failure traceback")
            except Exception:
                pass

    def _run_experiment13(self) -> None:
        """Experiment #13: RSI(2) parameter-robustness grid + cost stress on the
        indices that survived exp #12. → experiment13_results.md."""
        try:
            from .backtest.experiments_13 import run_experiment13_report
            symbols = self.bot_cfg.get("experiment13", {}).get("symbols", ["SPY", "QQQ"])
            report = run_experiment13_report(get_ohlcv=self.broker.get_ohlcv, symbols=symbols)
            self.heartbeat._put_file("experiment13_results.md", report.encode(),
                                     "Experiment #13: RSI(2) parameter robustness")
            logger.info("Experiment #13: report pushed to experiment13_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #13 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment13_results.md",
                                         f"# Experiment #13 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #13 failure traceback")
            except Exception:
                pass

    def _run_experiment12(self) -> None:
        """Experiment #12: turn-of-month, overnight drift, RSI(2) reversal, low-vol
        anomaly — under the strong rigor battery. → experiment12_results.md."""
        try:
            from .backtest.experiments_12 import run_experiment12_report
            cfg = self.bot_cfg.get("experiment12", {})
            report = run_experiment12_report(
                get_ohlcv=self.broker.get_ohlcv,
                index_symbols=cfg.get("index_symbols", []),
                lowvol_universe=cfg.get("lowvol_universe", []),
            )
            self.heartbeat._put_file("experiment12_results.md", report.encode(),
                                     "Experiment #12: documented anomalies under the strong battery")
            logger.info("Experiment #12: report pushed to experiment12_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #12 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment12_results.md",
                                         f"# Experiment #12 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #12 failure traceback")
            except Exception:
                pass

    def _run_experiment11(self) -> None:
        """Experiment #11: seasonality, lead-lag, term-structure, weekday effects,
        each judged by the STRONG rigor battery (bootstrap p-value + multiple-testing
        haircut + regime stability). → experiment11_results.md."""
        try:
            from .backtest.experiments_11 import run_experiment11_report
            cfg = self.bot_cfg.get("experiment11", {})
            report = run_experiment11_report(
                get_ohlcv=self.broker.get_ohlcv,
                seasonality_symbols=cfg.get("seasonality_symbols", []),
                lead_lag_pairs=[(p["leader"], p["target"]) for p in cfg.get("lead_lag_pairs", [])],
                term_structure=cfg.get("term_structure"),
                weekday_symbols=cfg.get("weekday_symbols", []),
            )
            self.heartbeat._put_file("experiment11_results.md", report.encode(),
                                     "Experiment #11: hypotheses under the strong rigor battery")
            logger.info("Experiment #11: report pushed to experiment11_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #11 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment11_results.md",
                                         f"# Experiment #11 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #11 failure traceback")
            except Exception:
                pass

    def _run_experiment10(self) -> None:
        """Experiment #10: GLD/GDX parameter-robustness grid (overfit check) +
        dollar-index ratios (commodity vs USD strength via UUP). → experiment10_results.md."""
        try:
            from .backtest.research import run_experiment10_report
            rp = self.bot_cfg.get("param_robust_pair", {"a": "GLD", "b": "GDX"})
            usd = self.bot_cfg.get("usd_ratio_experiments", [])
            usd_pairs = [(e["a"], e["b"]) for e in usd]
            logger.info("Experiment #10: GLD/GDX robustness + dollar ratios…")
            report = run_experiment10_report(
                get_ohlcv=self.broker.get_ohlcv,
                robust_pair=(rp["a"], rp["b"]), usd_pairs=usd_pairs)
            self.heartbeat._put_file("experiment10_results.md", report.encode(),
                                     "Experiment #10: GLD/GDX robustness + dollar ratios")
            logger.info("Experiment #10: report pushed to experiment10_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Experiment #10 failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("experiment10_results.md",
                                         f"# Experiment #10 — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Experiment #10 failure traceback")
            except Exception:
                pass

    def _run_ratio_research(self) -> None:
        """Experiment #9: inter-commodity ratio mean reversion (economically-linked
        pairs like gold/silver), cost sweep + walk-forward. → ratio_research_results.md."""
        try:
            from .backtest.research import run_ratio_research
            experiments = self.bot_cfg.get("ratio_experiments", [])
            pairs = [(e["a"], e["b"]) for e in experiments] if experiments else []
            if not pairs:
                logger.warning("Ratio research: no ratio_experiments configured")
                return
            logger.info(f"Ratio research: {len(pairs)} commodity ratios…")
            report = run_ratio_research(get_ohlcv=self.broker.get_ohlcv, experiments=pairs)
            self.heartbeat._put_file("ratio_research_results.md", report.encode(),
                                     "Commodity-ratio research (experiment #9)")
            logger.info("Ratio research: report pushed to ratio_research_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Ratio research failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("ratio_research_results.md",
                                         f"# Commodity-Ratio Research — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Ratio research failure traceback")
            except Exception:
                pass

    def _run_pairs_stress(self) -> None:
        """Stress-test the pairs stat-arb edge: economically-sensible pairs only,
        cost-sensitivity sweep (incl. short borrow fees), leave-one-out robustness.
        Pushed to pairs_stress_results.md."""
        try:
            from .backtest.quant_research import run_pairs_stress_report
            groups = self.bot_cfg.get("pairs_groups")
            if not groups:
                logger.warning("Pairs stress: no pairs_groups configured")
                return
            logger.info(f"Pairs stress: {len(groups)} economic groups…")
            report = run_pairs_stress_report(get_ohlcv=self.broker.get_ohlcv, groups=groups)
            self.heartbeat._put_file("pairs_stress_results.md", report.encode(),
                                     "Pairs stat-arb stress test")
            logger.info("Pairs stress: report pushed to pairs_stress_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Pairs stress failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("pairs_stress_results.md",
                                         f"# Pairs Stat-Arb Stress Test — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Pairs stress failure traceback")
            except Exception:
                pass

    def _run_quant(self) -> None:
        """Quant research: market-structure diagnostics (Hurst/variance-ratio) +
        statistical-arbitrage pairs trading (market-neutral mean reversion),
        OOS + walk-forward. Pushed to quant_results.md."""
        try:
            from .backtest.quant_research import run_quant_report
            symbols = self.bot_cfg.get("quant_universe")
            if not symbols:
                # flatten the backtest universes as a fallback
                uni = self.bot_cfg.get("backtest_universes", {})
                symbols = sorted({s for lst in uni.values() for s in lst})
            logger.info(f"Quant research: analysing {len(symbols)} symbols…")
            report = run_quant_report(get_ohlcv=self.broker.get_ohlcv, symbols=symbols)
            self.heartbeat._put_file("quant_results.md", report.encode(),
                                     "Quant research (structure + stat-arb pairs)")
            logger.info("Quant research: report pushed to quant_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Quant research failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("quant_results.md",
                                         f"# Quant Research — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Quant research failure traceback")
            except Exception:
                pass

    def _run_vol_premium(self) -> None:
        """Volatility risk-premium edge test via a short-VIX ETF (SVXY), naive and
        trend-filtered, vs holding SPY, with tail metrics + walk-forward. Pushed to
        vol_premium_results.md."""
        try:
            from .backtest.vol_premium import run_vol_report
            cfg = self.bot_cfg.get("vol_premium", {})
            candidates = cfg.get("short_vol_candidates", ["SVXY", "VXX", "VIXY"])
            benchmark = cfg.get("benchmark", "SPY")
            logger.info(f"Vol premium: testing {candidates} vs {benchmark}…")
            report = run_vol_report(get_ohlcv=self.broker.get_ohlcv,
                                    short_vol_candidates=candidates, benchmark=benchmark)
            self.heartbeat._put_file("vol_premium_results.md", report.encode(),
                                     "Volatility risk-premium edge test")
            logger.info("Vol premium: report pushed to vol_premium_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Vol premium failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("vol_premium_results.md",
                                         f"# Volatility Risk-Premium — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Vol premium failure traceback")
            except Exception:
                pass

    def _run_rotation(self) -> None:
        """Small-basket rotation edge test (e.g. Bitcoin/Gold/Dollar) vs holding
        each asset alone, OOS + walk-forward, pushed to rotation_results.md."""
        try:
            from .backtest.basket_rotation import run_rotation_report
            baskets = self.bot_cfg.get("rotation_baskets")
            if not baskets:
                logger.warning("Rotation: no baskets configured")
                return
            logger.info(f"Rotation: testing {len(baskets)} basket(s)…")
            report = run_rotation_report(get_ohlcv=self.broker.get_ohlcv, baskets=baskets)
            self.heartbeat._put_file("rotation_results.md", report.encode(),
                                     "Basket rotation edge test (BTC/Gold/Dollar)")
            logger.info("Rotation: report pushed to rotation_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Rotation failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("rotation_results.md",
                                         f"# Basket Rotation — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "Rotation failure traceback")
            except Exception:
                pass

    def _run_xsec(self) -> None:
        """Cross-sectional momentum edge test (relative-strength rotation) vs
        equal-weight Buy&Hold, per asset class with enough names, OOS +
        walk-forward, pushed to xsec_results.md."""
        try:
            from .backtest.xsec_momentum import run_xsec_report
            universes = self.bot_cfg.get("backtest_universes")
            if not universes:
                universes = {"crypto": [s for s in self.symbols if "/" in s]}
            logger.info(f"XSec momentum: testing {len(universes)} asset classes…")
            report = run_xsec_report(get_ohlcv=self.broker.get_ohlcv, universes=universes)
            self.heartbeat._put_file("xsec_results.md", report.encode(),
                                     "Cross-sectional momentum edge test")
            logger.info("XSec momentum: report pushed to xsec_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"XSec momentum failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file("xsec_results.md",
                                         f"# Cross-Sectional Momentum — FAILED\n\n```\n{tb}\n```\n".encode(),
                                         "XSec failure traceback")
            except Exception:
                pass

    def _run_walkforward(self) -> None:
        """Metals walk-forward robustness test: rolling windows across full daily
        history, Trend vs Buy&Hold per window, pushed to walkforward_results.md.
        Separates a robust all-regime edge from one lucky recent window."""
        try:
            from .backtest.trend_follow import run_walkforward_report
            universes = self.bot_cfg.get("backtest_universes", {})
            metals = universes.get("metals", [])
            if not metals:
                logger.warning("Walk-forward: no metals universe configured")
                return
            logger.info(f"Walk-forward: rolling windows on {len(metals)} metals symbols…")
            report = run_walkforward_report(get_ohlcv=self.broker.get_ohlcv, symbols=metals)
            self.heartbeat._put_file("walkforward_results.md", report.encode(),
                                     "Metals walk-forward robustness test")
            logger.info("Walk-forward: report pushed to walkforward_results.md")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Walk-forward failed: {e}\n{tb}")
            try:
                self.heartbeat._put_file(
                    "walkforward_results.md",
                    f"# Metals Walk-Forward — FAILED\n\n```\n{tb}\n```\n".encode(),
                    "Walk-forward failure traceback")
            except Exception:
                pass

    def run(self) -> None:
        """Start the main trading loop (blocking)."""
        logger.info("Bot started — entering main loop")
        self._running = True

        if self.bot_cfg.get("bot", {}).get("run_backtest_on_start", False):
            import threading
            threading.Thread(target=self._run_startup_backtest, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_trend_backtest_on_start", False):
            import threading
            threading.Thread(target=self._run_trend_backtest, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_benchmark_on_start", False):
            import threading
            threading.Thread(target=self._run_benchmark, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_walkforward_on_start", False):
            import threading
            threading.Thread(target=self._run_walkforward, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_xsec_on_start", False):
            import threading
            threading.Thread(target=self._run_xsec, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_rotation_on_start", False):
            import threading
            threading.Thread(target=self._run_rotation, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_vol_premium_on_start", False):
            import threading
            threading.Thread(target=self._run_vol_premium, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_quant_on_start", False):
            import threading
            threading.Thread(target=self._run_quant, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_pairs_stress_on_start", False):
            import threading
            threading.Thread(target=self._run_pairs_stress, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_ratio_research_on_start", False):
            import threading
            threading.Thread(target=self._run_ratio_research, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment10_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment10, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment11_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment11, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment12_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment12, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment13_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment13, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment14_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment14, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment15_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment15, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment16_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment16, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment17_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment17, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment18_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment18, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment19_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment19, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment20_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment20, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment21_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment21, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment22_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment22, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment23_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment23, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment24_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment24, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment25_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment25, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment26_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment26, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment27_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment27, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment28_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment28, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment29_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment29, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment30_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment30, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment31_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment31, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment32_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment32, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment33_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment33, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment34_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment34, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment35_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment35, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment36_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment36, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment37_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment37, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment38_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment38, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment39_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment39, daemon=True).start()

        if self.bot_cfg.get("bot", {}).get("run_experiment40_on_start", False):
            import threading
            threading.Thread(target=self._run_experiment40, daemon=True).start()

        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Unhandled error in main loop: {e}", exc_info=True)
            time.sleep(self.loop_interval)

    def run_once(self) -> None:
        """Run a single tick (useful for testing or cron-based scheduling)."""
        self._tick()

    # ── Main loop tick ────────────────────────────────────────────────────────

    def _tick(self) -> None:
        now = datetime.now(timezone.utc)
        logger.debug(f"Tick @ {now.strftime('%H:%M:%S UTC')}")

        # Refresh account state
        try:
            account = self.broker.get_account()
        except Exception as e:
            logger.error(f"Failed to fetch account: {e}")
            return

        # Daily reset & drawdown checks
        self.risk_manager.daily_reset(account)
        self.risk_manager.metrics.open_positions = len(self._open_trades)

        # Hourly heartbeat — makes "is the bot alive & trading?" observable anytime
        self._maybe_heartbeat(now, account)

        # Auto-heal paused/stopped states — bot recovers without user intervention
        self._auto_recover()

        status = self.risk_manager.status_summary()
        if status["state"] in ("stopped", "paused"):
            logger.warning(f"Bot state={status['state']} — skipping entries")
            self._manage_open_positions(account)
            return

        try:
            market_open = self.broker.is_market_open()
        except Exception as e:
            logger.warning(f"Market open check failed ({e}) — assuming open")
            market_open = True

        # Process each symbol — crypto runs 24/7, stocks only when market is open
        for symbol in self.symbols:
            try:
                is_crypto = "/" in symbol
                if not is_crypto and not market_open:
                    logger.debug(f"{symbol}: market closed — skipping")
                    continue
                self._process_symbol(symbol, account)
            except Exception as e:
                logger.error("Error processing {}: {}", symbol, repr(e))

        # Manage exits on existing positions
        try:
            self._manage_open_positions(account)
        except Exception as e:
            logger.error(f"Position management error: {e}")

        # Daily report at 20:00 UTC (22:00 Swiss time) — after US market close
        if now.hour == 20 and now.minute < 2:
            today = now.strftime("%Y-%m-%d")
            if self._last_daily_report != today:
                self._last_daily_report = today
                report = self.reporter.daily_report()
                report["account_equity"] = account.equity
                self.telegram.daily_report(report)

                # Self-learning: analyse journal + auto-adjust params
                try:
                    self.auto_tuner.run()
                except Exception as e:
                    logger.error(f"AutoTuner failed: {e}")

                # Sync journal to GitHub so it's accessible for external review
                try:
                    self.journal_syncer.push()
                except Exception as e:
                    logger.error(f"JournalSync failed: {e}")

        # Morning report at 03:30 UTC (05:30 Swiss time) — 4-minute window prevents misses
        if now.hour == 3 and 28 <= now.minute <= 31:
            today = now.strftime("%Y-%m-%d")
            if self._last_morning_report != today:
                self._last_morning_report = today
                self._send_morning_report()

    def _process_symbol(self, symbol: str, account) -> None:
        # Fetch OHLCV
        df = self.broker.get_ohlcv(symbol, self.timeframe, limit=300)
        if df.empty or len(df) < 50:
            logger.debug(f"{symbol}: insufficient data ({len(df)} bars)")
            return

        # Indicators
        all_params = {}
        for s in self.strategies:
            all_params.update(self.strategy_cfg.get(s.name, {}))
        df = add_all_indicators(df, all_params)

        # Update market trend from SPY (processed first in the symbol list)
        if symbol == "SPY":
            row = df.iloc[-1]
            ema50 = row.get("ema_50", row["close"])
            self._market_trend = "bullish" if row["close"] > ema50 else "bearish"
            logger.debug(f"Market trend: {self._market_trend} (SPY={row['close']:.2f} EMA50={ema50:.2f})")

        # Already in a position for this symbol — skip new entries
        if symbol in self._open_trades:
            return

        # SL cooldown: skip re-entry if symbol was stopped out recently
        cooldown_until = self._sl_cooldown.get(symbol)
        if cooldown_until and datetime.now(timezone.utc) < cooldown_until:
            logger.debug(f"{symbol}: SL cooldown active until {cooldown_until.strftime('%H:%M UTC')} — skipping")
            return

        is_crypto = "/" in symbol

        # Session filter: avoid first N min of open and last N min before close for stocks
        if not is_crypto:
            sf = self.risk_cfg.get("session_filter", {})
            if sf.get("enabled"):
                avoid_open = sf.get("avoid_open_minutes", 15)
                avoid_close = sf.get("avoid_close_minutes", 30)
                us = self.bot_cfg.get("sessions", {}).get("us_stocks", {})
                now_utc = datetime.now(timezone.utc)
                try:
                    oh, om = map(int, us.get("start", "13:30").split(":"))
                    ch, cm = map(int, us.get("end", "20:00").split(":"))
                    open_ts = now_utc.replace(hour=oh, minute=om, second=0, microsecond=0)
                    close_ts = now_utc.replace(hour=ch, minute=cm, second=0, microsecond=0)
                    if now_utc < open_ts + timedelta(minutes=avoid_open):
                        logger.debug(f"{symbol}: within first {avoid_open} min of session — skip entry")
                        return
                    if now_utc > close_ts - timedelta(minutes=avoid_close):
                        logger.debug(f"{symbol}: within last {avoid_close} min before close — skip entry")
                        return
                except Exception:
                    pass  # Don't block trading if session parse fails

        # Collect signals from all strategies
        raw_signals: list[Signal] = []
        for strategy in self.strategies:
            try:
                raw_signals.extend(strategy.generate_signals(df, symbol))
            except Exception as e:
                logger.error(f"Strategy {strategy.name} failed for {symbol}: {e}")

        # Crypto: only trend-following strategies (supertrend + breakout_momentum)
        # Mean reversion strategies produce too many false signals on 24/7 volatile crypto
        if is_crypto:
            crypto_strats = set(self.bot_cfg.get("crypto_strategies", ["supertrend", "breakout_momentum"]))
            raw_signals = [s for s in raw_signals if s.strategy in crypto_strats]

        if not raw_signals:
            return

        # Sentiment filter (optional — skip if APIs not configured)
        sentiment_score = self.sentiment.get_sentiment(symbol)
        filtered = self._sentiment_filter(raw_signals, sentiment_score)

        # Signal fusion
        fusion_cfg = self.strategy_cfg.get("signal_fusion", {})
        entry = self._fuse_signals(filtered, fusion_cfg)
        if entry is None:
            return

        # Market breadth filter: don't fight SPY's macro direction for US stocks
        is_etf_or_stock = not is_crypto
        if is_etf_or_stock and symbol != "SPY" and self._market_trend != "neutral":
            if self._market_trend == "bearish" and entry.signal == SignalType.LONG:
                logger.debug(f"{symbol}: skipping LONG — SPY in bearish trend")
                return
            if self._market_trend == "bullish" and entry.signal == SignalType.SHORT:
                logger.debug(f"{symbol}: skipping SHORT — SPY in bullish trend")
                return

        # Risk gate
        if not self.risk_manager.approve_signal(entry, account):
            return

        # Position sizing
        try:
            current_price = self.broker.get_current_price(symbol)
        except Exception as e:
            logger.error(f"Price fetch failed for {symbol}: {e}")
            return

        qty = self.risk_manager.calculate_position_size(account, entry, current_price)
        if qty <= 0:
            return

        # Hard safety cap right before execution: no single position may exceed
        # max_position_size_pct of equity, regardless of how cheap the asset is.
        # Belt-and-suspenders on top of the risk manager's own cap.
        max_pos_pct = self.risk_cfg.get("risk", {}).get("max_position_size_pct", 5.0) / 100
        if current_price > 0 and max_pos_pct > 0:
            cap_qty = (account.equity * max_pos_pct) / current_price
            if qty > cap_qty:
                logger.warning(
                    f"{symbol}: qty {qty:.4f} exceeds {max_pos_pct:.0%}-of-equity cap "
                    f"(${account.equity * max_pos_pct:.0f}) — clamping to {cap_qty:.4f}"
                )
                qty = cap_qty
        if qty <= 0:
            return

        # Execute order
        side = OrderSide.BUY if entry.signal == SignalType.LONG else OrderSide.SELL

        # Alpaca rejects fractional short orders for stocks — floor to whole shares
        if side == OrderSide.SELL and "/" not in symbol:
            qty = math.floor(qty)
            if qty <= 0:
                logger.debug(f"{symbol}: short qty rounds to 0 whole shares — skipping")
                return
        order = Order(symbol=symbol, side=side, qty=qty, order_type=OrderType.MARKET)
        order = self.broker.place_order(order)

        if order.order_id:
            # Sanitise SL/TP: a level on the wrong side of entry is a broken
            # signal (e.g. a long with tp <= entry). Left in place it produces a
            # guaranteed instant loss that closes the moment the min-hold gate
            # releases and gets mislabelled "tp". Drop the bad level instead of
            # trading it; the position then relies on the valid levels + time.
            sl, tp = entry.stop_loss, entry.take_profit
            if entry.signal == SignalType.LONG:
                if sl is not None and sl >= current_price:
                    logger.warning(f"{symbol}: dropping invalid long SL {sl} >= entry {current_price:.4f}")
                    sl = None
                if tp is not None and tp <= current_price:
                    logger.warning(f"{symbol}: dropping invalid long TP {tp} <= entry {current_price:.4f}")
                    tp = None
            else:
                if sl is not None and sl <= current_price:
                    logger.warning(f"{symbol}: dropping invalid short SL {sl} <= entry {current_price:.4f}")
                    sl = None
                if tp is not None and tp >= current_price:
                    logger.warning(f"{symbol}: dropping invalid short TP {tp} >= entry {current_price:.4f}")
                    tp = None
            self._open_trades[symbol] = {
                "order_id": order.order_id,
                "entry_price": current_price,
                "side": side,
                "qty": qty,
                "sl": sl,
                "tp": tp,
                "strategy": entry.strategy,
                "opened_at": datetime.now(timezone.utc),
            }
            self.risk_manager.metrics.open_positions += 1
            self.telegram.trade_entered(
                symbol=symbol, side=side.value, qty=qty, price=current_price,
                strategy=entry.strategy, sl=entry.stop_loss, tp=entry.take_profit,
            )
            logger.info(
                f"ENTERED {side.value.upper()} {symbol} @ {current_price:.4f} "
                f"qty={qty:.4f} sl={entry.stop_loss} tp={entry.take_profit} "
                f"via {entry.strategy}"
            )

    def _load_sl_cooldowns(self) -> dict[str, datetime]:
        """Restore SL cooldowns from disk so restarts don't bypass them."""
        result: dict[str, datetime] = {}
        if not self._cooldown_path.exists():
            return result
        try:
            with open(self._cooldown_path) as f:
                raw = json.load(f)
            now = datetime.now(timezone.utc)
            for sym, ts in raw.items():
                until = datetime.fromisoformat(ts)
                if until > now:
                    result[sym] = until
            logger.info(f"Restored {len(result)} active SL cooldowns from disk")
        except Exception as e:
            logger.warning(f"Could not load SL cooldowns: {e}")
        return result

    def _save_sl_cooldowns(self) -> None:
        """Persist current SL cooldowns to disk."""
        now = datetime.now(timezone.utc)
        active = {sym: ts.isoformat() for sym, ts in self._sl_cooldown.items() if ts > now}
        try:
            self._cooldown_path.parent.mkdir(exist_ok=True)
            with open(self._cooldown_path, "w") as f:
                json.dump(active, f)
        except Exception as e:
            logger.warning(f"Could not save SL cooldowns: {e}")

    def _get_pnl_baseline(self, current_equity: float) -> float:
        """Equity at the moment P&L tracking began — the honest baseline. Read
        from the first row of equity_history.csv (durable, survives restarts) so
        realized P&L is always consistent with the account value, not an in-memory
        counter that resets on restart. Falls back to current equity on first run."""
        if self._pnl_baseline is not None:
            return self._pnl_baseline
        try:
            with open(self._equity_history_path) as f:
                next(f)  # header
                first = next(f)
                self._pnl_baseline = float(first.split(",")[1])
        except (StopIteration, FileNotFoundError, ValueError, IndexError):
            self._pnl_baseline = current_equity
        return self._pnl_baseline

    def _maybe_heartbeat(self, now: datetime, account) -> None:
        """Push a status snapshot to GitHub at most once per hour."""
        if self._last_heartbeat and (now - self._last_heartbeat).total_seconds() < 3600:
            return
        self._last_heartbeat = now
        try:
            m = self.risk_manager.metrics
            # Mark-to-market on open positions — reveals losses the trade journal
            # (which only records closed trades) never shows.
            unrealized = 0.0
            pos_detail: list[dict] = []
            try:
                for p in self.broker.get_positions():
                    # Use the broker's own unrealized P&L (Alpaca computes it from
                    # market value − cost basis). The old recompute from entry_price
                    # produced absurd values (e.g. +$83k on 0.04 BTC) whenever a
                    # stored entry price was corrupt. Fall back to the recompute only
                    # if the broker value is missing/non-finite, and ignore any
                    # single position whose |unrealized| exceeds account equity
                    # (physically impossible → corrupt data, don't let it poison the total).
                    u = p.unrealized_pnl
                    if u is None or not math.isfinite(u):
                        direction = 1 if p.side.value == "buy" else -1
                        u = (p.current_price - p.entry_price) * abs(p.qty) * direction
                    if abs(u) > max(account.equity, 1.0):
                        logger.warning(f"Heartbeat: implausible unrealized {u:.0f} on "
                                       f"{p.symbol} (equity {account.equity:.0f}) — skipping")
                        continue
                    unrealized += u
                    pos_detail.append({
                        "symbol": p.symbol,
                        "side": p.side.value,
                        "qty": round(abs(p.qty), 4),
                        "unrealized_usd": round(u, 2),
                    })
            except Exception as e:
                logger.warning(f"Heartbeat: could not read positions: {e}")

            # Realized P&L derived from the account itself, not an in-memory
            # counter: total P&L = equity - baseline; realized = total - unrealized.
            # This can never diverge from the account value (the old m.total_pnl
            # counter reset on every restart and understated closed losses).
            baseline = self._get_pnl_baseline(account.equity)
            realized_true = (account.equity - baseline) - unrealized

            status = self.heartbeat.build_status(
                state=m.state.value,
                open_positions=len(pos_detail) or len(self._open_trades),
                trades_today=m.trades_today,
                equity=account.equity,
                market_trend=self._market_trend,
                daily_pnl=m.daily_pnl,
                realized_pnl=realized_true,
                unrealized_pnl=unrealized,
                positions=pos_detail,
            )
            self.heartbeat.push(status)
            self.heartbeat.append_history(self._equity_history_path, status)
            # Sync the journal hourly (not only at 20:00) so the branch copy is
            # at most ~1h stale and a redeploy can't lose much.
            try:
                self.journal_syncer.push()
            except Exception as e:
                logger.warning(f"Hourly journal sync failed: {e}")
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")

    def _auto_recover(self) -> None:
        """Autonomous self-healing — recovers from paused/stopped states without user action."""
        from .brokers.base_broker import OrderSide as _OS
        from .risk.risk_manager import BotState
        state = self.risk_manager.metrics.state
        now = datetime.now(timezone.utc)

        env = self.bot_cfg["bot"].get("environment", "paper")

        if state == BotState.PAUSED:
            if env == "paper":
                # Paper mode: no pause for loss streaks — keep learning from every trade
                self.risk_manager.metrics.state = BotState.ACTIVE
                self.risk_manager.metrics.consecutive_losses = 0
                logger.info("Paper mode: loss-streak pause skipped — resuming immediately")
            else:
                pause_until = self.risk_manager.metrics.pause_until
                if pause_until and now >= pause_until:
                    self.risk_manager.metrics.state = BotState.ACTIVE
                    self.risk_manager.metrics.consecutive_losses = 0
                    logger.info("Loss-streak pause expired — bot resumed automatically")

        elif state == BotState.STOPPED:
            pause_until = self.risk_manager.metrics.pause_until
            if pause_until is None or now >= pause_until:
                if env == "paper":
                    logger.warning("Paper mode: 1h drawdown pause expired — resuming automatically")
                    self.risk_manager.metrics.state = BotState.ACTIVE
                    self.risk_manager.metrics.consecutive_losses = 0
                    self.risk_manager.metrics.daily_pnl = 0.0

    def _send_morning_report(self) -> None:
        """05:30 Swiss time — overnight summary sent to Telegram."""
        try:
            positions = self.broker.get_positions()
            account = self.broker.get_account()

            pos_lines = ""
            total_unrealized = 0.0
            for p in positions:
                pnl = (p.current_price - p.entry_price) * abs(p.qty) * (1 if p.side.value == "buy" else -1)
                total_unrealized += pnl
                emoji = "🟢" if pnl >= 0 else "🔴"
                pos_lines += f"{emoji} {p.symbol}: {p.side.value.upper()} ${pnl:+.2f}\n"

            overnight = self.reporter.daily_report()
            trades_today = overnight.get("total_trades", 0)
            pnl_today = overnight.get("total_pnl_usd", 0.0)

            status = self.risk_manager.status_summary()
            state_emoji = {"active": "✅", "safe_mode": "⚠️", "paused": "⏸", "stopped": "🛑"}.get(
                status["state"], "❓"
            )
            pause_info = f"\nPause bis: {status['paused_until']}" if status.get("paused_until") else ""
            self.telegram.send(
                f"☀️ <b>Guten Morgen — Nachtbericht 05:30</b>\n\n"
                f"<b>Konto:</b> ${account.equity:,.2f} (Cash: ${account.cash:,.2f})\n"
                f"<b>Unrealisiert:</b> ${total_unrealized:+.2f}\n"
                f"<b>Trades heute:</b> {trades_today} | P&L: ${pnl_today:+.2f}\n\n"
                f"<b>Offene Positionen ({len(positions)}):</b>\n{pos_lines if pos_lines else '— keine —'}\n"
                f"<b>Aktive Strategien:</b> {len(self.strategies)}\n"
                f"<b>Bot-Status:</b> {state_emoji} {status['state'].upper()}{pause_info}\n"
                f"<b>Verluste in Folge:</b> {status['consecutive_losses']}"
            )
        except Exception as e:
            logger.error(f"Morning report failed: {e}")
            self.telegram.error_alert(f"Morgenbericht fehlgeschlagen: {e}")

    def _load_existing_positions(self) -> None:
        """On restart, sync _open_trades with positions already open at the broker."""
        try:
            positions = self.broker.get_positions()
            for pos in positions:
                if pos.symbol not in self._open_trades:
                    self._open_trades[pos.symbol] = {
                        "order_id": "restored",
                        "entry_price": pos.entry_price,
                        "side": pos.side,
                        "qty": abs(pos.qty),
                        "sl": None,
                        "tp": None,
                        "strategy": "restored",
                        "opened_at": datetime.now(timezone.utc),
                    }
                    logger.info(
                        f"Restored position: {pos.symbol} {pos.side.value} "
                        f"qty={pos.qty:.4f} @ {pos.entry_price:.4f}"
                    )
        except Exception as e:
            logger.warning(f"Could not load existing positions on startup: {e}")

    def _manage_open_positions(self, account) -> None:
        """Check SL/TP/trailing and close positions as needed."""
        closed = []
        positions = {p.symbol: p for p in self.broker.get_positions()}

        for symbol, trade in self._open_trades.items():
            pos = positions.get(symbol)
            if pos is None:
                # Position was already closed (broker-side)
                closed.append(symbol)
                continue

            price = pos.current_price
            side = trade["side"]
            sl = trade.get("sl")
            tp = trade.get("tp")

            # Restored positions have no SL/TP — assign default % levels so they
            # don't block the position cap forever
            if sl is None and tp is None:
                entry = trade["entry_price"]
                if side == OrderSide.BUY:
                    sl = entry * 0.985   # 1.5% stop-loss
                    tp = entry * 1.030   # 3.0% take-profit
                else:
                    sl = entry * 1.015
                    tp = entry * 0.970
                trade["sl"] = sl
                trade["tp"] = tp
                logger.info(f"Assigned fallback SL/TP to {symbol}: SL={sl:.4f} TP={tp:.4f}")

            # Ghost-trade guard: never evaluate an exit on a freshly-opened
            # position. A trade that closes within seconds is a spread/mark
            # artifact (open and immediate re-check in the same tick), not a
            # real signal — this is what produced the "tp with a loss" trades.
            # A minimum hold time makes sub-minute exits impossible by design.
            min_hold = self.bot_cfg.get("bot", {}).get("min_hold_seconds", 120)
            held_s = (datetime.now(timezone.utc) - trade["opened_at"]).total_seconds()
            if held_s < min_hold:
                continue

            should_close = False
            reason = ""

            if side == OrderSide.BUY:
                if sl and price <= sl:
                    should_close, reason = True, "sl"
                elif tp and price >= tp:
                    should_close, reason = True, "tp"
            else:
                if sl and price >= sl:
                    should_close, reason = True, "sl"
                elif tp and price <= tp:
                    should_close, reason = True, "tp"

            # ── Trailing stop ─────────────────────────────────────────────────
            if not should_close:
                trailing_cfg = self.risk_cfg.get("trailing_stop", {})
                if trailing_cfg.get("enabled"):
                    activate_pct = trailing_cfg.get("activate_after_profit_pct", 1.0) / 100
                    trail_pct = trailing_cfg.get("trail_pct", 0.8) / 100
                    entry_price = trade["entry_price"]
                    if side == OrderSide.BUY:
                        profit_pct = (price - entry_price) / entry_price
                        if profit_pct >= activate_pct:
                            peak = max(trade.get("trail_peak", price), price)
                            trade["trail_peak"] = peak
                            if price <= peak * (1 - trail_pct):
                                should_close, reason = True, "trailing_stop"
                    else:
                        profit_pct = (entry_price - price) / entry_price
                        if profit_pct >= activate_pct:
                            trough = min(trade.get("trail_trough", price), price)
                            trade["trail_trough"] = trough
                            if price >= trough * (1 + trail_pct):
                                should_close, reason = True, "trailing_stop"

            # ── Time-based exit ───────────────────────────────────────────────
            if not should_close:
                max_hold_h = self.bot_cfg.get("bot", {}).get("max_hold_hours", 6)
                held_h = (datetime.now(timezone.utc) - trade["opened_at"]).total_seconds() / 3600
                if held_h >= max_hold_h:
                    should_close, reason = True, "time_limit"

            if should_close:
                success = self.broker.close_position(symbol)
                if success:
                    direction = 1 if side == OrderSide.BUY else -1
                    pnl = (price - trade["entry_price"]) * trade["qty"] * direction
                    # Label honesty: a "tp"/"trailing_stop" that closes at a loss
                    # wasn't really a profit-taking exit (spread/late fill). Record
                    # what actually happened so the journal stats stay truthful.
                    if reason in ("tp", "trailing_stop") and pnl < 0:
                        reason = "spread_loss"
                    prev_state = self.risk_manager.metrics.state
                    self.risk_manager.record_trade_result(pnl)
                    new_state = self.risk_manager.metrics.state
                    self.telegram.trade_exited(
                        symbol=symbol, side=side.value, qty=trade["qty"],
                        entry=trade["entry_price"], exit_price=price,
                        pnl=pnl, reason=reason,
                    )
                    # Inform user when bot changes state — bot handles recovery itself
                    if prev_state != new_state:
                        streak = self.risk_manager.metrics.consecutive_losses
                        pause_until = self.risk_manager.metrics.pause_until
                        resume_str = pause_until.strftime('%H:%M UTC') if pause_until else '—'
                        if new_state.value == "paused":
                            env = self.bot_cfg["bot"].get("environment", "paper")
                            if env != "paper":
                                self.telegram.send(
                                    f"⏸ <b>Bot kurz pausiert</b> ({streak} Verluste in Folge)\n"
                                    f"Automatische Wiederaufnahme um {resume_str}."
                                )
                            # Paper mode: no notification — bot resumes within 60s anyway
                        elif new_state.value == "stopped":
                            env = self.bot_cfg["bot"].get("environment", "paper")
                            if env == "paper":
                                self.telegram.send(
                                    "🔄 <b>Drawdown-Limit erreicht</b>\n"
                                    "Bot pausiert 1h, setzt sich automatisch zurück und handelt weiter."
                                )
                            else:
                                self.telegram.error_alert(
                                    "🛑 HARD STOP — maximaler Verlust im Live-Modus.\n"
                                    "Bitte manuell prüfen bevor Neustart."
                                )
                    # Log every close. A logging failure must be loud, never a
                    # silently-dropped trade (that is how the P&L accounting
                    # diverged from reality during the experiment).
                    try:
                        self.reporter.log_trade(
                            symbol=symbol,
                            strategy=trade.get("strategy", ""),
                            direction="long" if side == OrderSide.BUY else "short",
                            entry_price=trade["entry_price"],
                            exit_price=price,
                            qty=trade["qty"],
                            pnl=pnl,
                            entry_time=trade["opened_at"],
                            exit_time=datetime.now(timezone.utc),
                            exit_reason=reason,
                        )
                    except Exception as e:
                        logger.error(f"CRITICAL: failed to journal closed trade {symbol} pnl={pnl:.2f}: {e}")
                    # SL cooldown: block re-entry for 30 min to prevent chasing losses
                    if reason == "sl":
                        cooldown_minutes = self.bot_cfg.get("bot", {}).get("sl_cooldown_minutes", 30)
                        self._sl_cooldown[symbol] = datetime.now(timezone.utc) + timedelta(minutes=cooldown_minutes)
                        self._save_sl_cooldowns()
                        logger.info(f"{symbol}: SL cooldown set — no re-entry for {cooldown_minutes} min")
                    closed.append(symbol)

        for symbol in closed:
            self._open_trades.pop(symbol, None)
            self.risk_manager.metrics.open_positions = max(
                0, self.risk_manager.metrics.open_positions - 1
            )

    # ── Signal fusion ─────────────────────────────────────────────────────────

    def _fuse_signals(self, signals: list[Signal], cfg: dict) -> Optional[Signal]:
        if not signals:
            return None

        enabled = cfg.get("enabled", True)
        if not enabled:
            return max(signals, key=lambda s: s.score) if signals else None

        weights = cfg.get("score_weights", {})
        threshold = cfg.get("score_threshold", 1.5)

        for direction in (SignalType.LONG, SignalType.SHORT):
            dir_signals = [s for s in signals if s.signal == direction]
            if not dir_signals:
                continue

            composite = sum(s.score * weights.get(s.strategy, 1.0) for s in dir_signals)
            if composite >= threshold:
                # Return the highest-scored signal as representative
                best = max(dir_signals, key=lambda s: s.score)
                logger.info(
                    f"Fusion score {direction.value}: {composite:.3f} ≥ {threshold} "
                    f"({len(dir_signals)} strategies)"
                )
                return best

        return None

    def _sentiment_filter(self, signals: list[Signal], sentiment: float) -> list[Signal]:
        """Drop entry signals that oppose strong sentiment (|score| > 0.5)."""
        filtered = []
        for s in signals:
            if not s.is_entry():
                filtered.append(s)
                continue
            if sentiment > 0.5 and s.signal == SignalType.SHORT:
                logger.debug(f"Dropping SHORT on {s.symbol} — strong positive sentiment ({sentiment:.2f})")
                continue
            if sentiment < -0.5 and s.signal == SignalType.LONG:
                logger.debug(f"Dropping LONG on {s.symbol} — strong negative sentiment ({sentiment:.2f})")
                continue
            filtered.append(s)
        return filtered

    # ── Broker factory ────────────────────────────────────────────────────────

    def _init_broker(self) -> BaseBroker:
        broker_name = self.bot_cfg.get("broker", "alpaca").lower()

        if broker_name == "alpaca":
            from .brokers.alpaca_broker import AlpacaBroker
            return AlpacaBroker()
        elif broker_name in ("binance", "kraken", "bybit", "okx", "kucoin"):
            from .brokers.ccxt_broker import CCXTBroker
            return CCXTBroker(broker_name)
        else:
            raise ValueError(f"Unknown broker: {broker_name}")

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def _handle_shutdown(self, signum, frame) -> None:
        logger.info("Shutdown signal received — stopping gracefully")
        self._running = False
        # Print final report
        report = self.reporter.daily_report()
        hints = self.reporter.generate_optimization_hints()
        logger.info(f"Optimization hints: {hints}")

    @staticmethod
    def _merge(base: dict, override: dict) -> None:
        for k, v in override.items():
            if isinstance(v, dict) and k in base:
                TradingBot._merge(base[k], v)
            else:
                base[k] = v
