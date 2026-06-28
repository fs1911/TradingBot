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
import os
import time
import signal
import sys
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from .utils.helpers import load_config
from .utils.logger import setup_logger
from .indicators.technical import add_all_indicators
from .strategies.base_strategy import Signal, SignalType
from .strategies.ema_crossover import EMACrossoverStrategy
from .strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from .strategies.macd_momentum import MACDMomentumStrategy
from .strategies.congress_trades import CongressTradesStrategy
from .risk.risk_manager import RiskManager
from .data.news_sentiment import SentimentAnalyzer
from .monitoring.reporter import PerformanceReporter
from .brokers.base_broker import BaseBroker, Order, OrderSide, OrderType


STRATEGY_REGISTRY = {
    "ema_crossover": EMACrossoverStrategy,
    "rsi_mean_reversion": RSIMeanReversionStrategy,
    "macd_momentum": MACDMomentumStrategy,
    "congress_mirror": CongressTradesStrategy,
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

        # Config shortcuts
        broker_key = self.bot_cfg.get("broker", "alpaca")
        self.market_cfg = self.bot_cfg.get("markets", {}).get(broker_key, {})
        self.symbols: list[str] = self.market_cfg.get("symbols", [])
        self.timeframe: str = self.market_cfg.get("timeframe", "1Hour")
        self.loop_interval = self.bot_cfg["bot"].get("loop_interval_seconds", 60)

        # State
        self._running = False
        self._open_trades: dict[str, dict] = {}   # symbol → trade info

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        logger.info(f"TradingBot ready — symbols={self.symbols}, timeframe={self.timeframe}")

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the main trading loop (blocking)."""
        logger.info("Bot started — entering main loop")
        self._running = True

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

        status = self.risk_manager.status_summary()
        if status["state"] in ("stopped", "paused"):
            logger.warning(f"Bot state={status['state']} — skipping entries")
            self._manage_open_positions(account)
            return

        # Market open check (for stock brokers)
        if not self.broker.is_market_open():
            logger.debug("Market closed — skipping")
            return

        # Process each symbol
        for symbol in self.symbols:
            try:
                self._process_symbol(symbol, account)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}", exc_info=True)

        # Manage exits on existing positions
        self._manage_open_positions(account)

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

        # Already in a position for this symbol — skip new entries
        if symbol in self._open_trades:
            return

        # Collect signals from all strategies
        raw_signals: list[Signal] = []
        for strategy in self.strategies:
            try:
                raw_signals.extend(strategy.generate_signals(df, symbol))
            except Exception as e:
                logger.error(f"Strategy {strategy.name} failed for {symbol}: {e}")

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

        # Execute order
        side = OrderSide.BUY if entry.signal == SignalType.LONG else OrderSide.SELL
        order = Order(symbol=symbol, side=side, qty=qty, order_type=OrderType.MARKET)
        order = self.broker.place_order(order)

        if order.order_id:
            self._open_trades[symbol] = {
                "order_id": order.order_id,
                "entry_price": current_price,
                "side": side,
                "qty": qty,
                "sl": entry.stop_loss,
                "tp": entry.take_profit,
                "strategy": entry.strategy,
                "opened_at": datetime.now(timezone.utc),
            }
            self.risk_manager.metrics.open_positions += 1
            logger.info(
                f"ENTERED {side.value.upper()} {symbol} @ {current_price:.4f} "
                f"qty={qty:.4f} sl={entry.stop_loss} tp={entry.take_profit} "
                f"via {entry.strategy}"
            )

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

            if should_close:
                success = self.broker.close_position(symbol)
                if success:
                    pnl = pos.unrealized_pnl
                    self.risk_manager.record_trade_result(pnl)
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
