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
                    direction = 1 if p.side.value == "buy" else -1
                    u = (p.current_price - p.entry_price) * abs(p.qty) * direction
                    unrealized += u
                    pos_detail.append({
                        "symbol": p.symbol,
                        "side": p.side.value,
                        "qty": round(abs(p.qty), 4),
                        "unrealized_usd": round(u, 2),
                    })
            except Exception as e:
                logger.warning(f"Heartbeat: could not read positions: {e}")

            status = self.heartbeat.build_status(
                state=m.state.value,
                open_positions=len(pos_detail) or len(self._open_trades),
                trades_today=m.trades_today,
                equity=account.equity,
                market_trend=self._market_trend,
                daily_pnl=m.daily_pnl,
                realized_pnl=m.total_pnl,
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
