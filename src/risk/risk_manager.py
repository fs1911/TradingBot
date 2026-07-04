"""
Risk & Money Management Engine
────────────────────────────────────────────────────────────────────────────
Responsibilities:
- Position sizing (fixed fractional risk model)
- Drawdown tracking (daily / weekly / monthly / total)
- Safe-mode logic
- Loss-streak protection
- Session-time validation
- Pre-trade risk gate (approve / reject / adjust signals)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date, timezone, timedelta
from enum import Enum
from typing import Optional
from loguru import logger

from ..strategies.base_strategy import Signal, SignalType
from ..brokers.base_broker import AccountInfo, Position


class BotState(str, Enum):
    ACTIVE = "active"
    SAFE_MODE = "safe_mode"        # Reduced size, no new entries
    PAUSED = "paused"              # Loss streak pause
    STOPPED = "stopped"            # Hard stop — manual restart required


@dataclass
class RiskMetrics:
    state: BotState = BotState.ACTIVE
    equity_high_water: float = 0.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    total_pnl: float = 0.0
    consecutive_losses: int = 0
    trades_today: int = 0
    open_positions: int = 0
    pause_until: Optional[datetime] = None
    safe_mode_reason: str = ""
    last_reset_date: date = field(default_factory=date.today)


class RiskManager:
    """Enforces all risk rules before any trade is executed."""

    def __init__(self, config: dict):
        self.cfg = config
        self.risk = config.get("risk", {})
        self.sl_cfg = config.get("stop_loss", {})
        self.tp_cfg = config.get("take_profit", {})
        self.session_cfg = config.get("session_filter", {})
        self.safe_cfg = self.risk.get("safe_mode", {})
        self.metrics = RiskMetrics()

    # ── Daily reset ───────────────────────────────────────────────────────────

    def daily_reset(self, account: AccountInfo) -> None:
        today = date.today()
        if self.metrics.last_reset_date != today:
            logger.info(f"Daily reset — equity: {account.equity:.2f}")
            self.metrics.daily_pnl = 0.0
            self.metrics.trades_today = 0
            self.metrics.last_reset_date = today
            if self.metrics.state == BotState.PAUSED and self.metrics.pause_until:
                if datetime.now(timezone.utc) > self.metrics.pause_until:
                    logger.info("Loss-streak pause expired — resuming ACTIVE state")
                    self.metrics.state = BotState.ACTIVE
                    self.metrics.consecutive_losses = 0

        if account.equity > self.metrics.equity_high_water:
            self.metrics.equity_high_water = account.equity

    # ── Signal gating ─────────────────────────────────────────────────────────

    def approve_signal(self, signal: Signal, account: AccountInfo) -> bool:
        """Return True only if the signal passes all risk checks."""
        if self.metrics.state == BotState.STOPPED:
            logger.warning(f"STOPPED — rejecting signal for {signal.symbol}")
            return False

        if self.metrics.state == BotState.PAUSED:
            if self.metrics.pause_until and datetime.now(timezone.utc) < self.metrics.pause_until:
                logger.warning(f"PAUSED until {self.metrics.pause_until} — rejecting {signal.symbol}")
                return False
            else:
                self.metrics.state = BotState.ACTIVE

        if not signal.is_entry():
            return True   # Exit signals always pass

        if self.metrics.state == BotState.SAFE_MODE and self.safe_cfg.get("disable_new_entries", False):
            logger.warning(f"SAFE_MODE (no entries) — rejecting {signal.symbol}")
            return False

        # Open position cap
        max_open = self.risk.get("max_open_positions", 8)
        if self.metrics.open_positions >= max_open:
            logger.info(f"Max open positions ({max_open}) reached — skipping {signal.symbol}")
            return False

        # Daily drawdown
        if self.metrics.equity_high_water > 0:
            daily_dd = -self.metrics.daily_pnl / self.metrics.equity_high_water * 100
            max_daily = self.risk.get("max_daily_drawdown_pct", 3.0)
            if daily_dd >= max_daily:
                logger.warning(f"Daily drawdown limit {max_daily}% reached ({daily_dd:.2f}%) — halting")
                self.metrics.state = BotState.PAUSED
                self.metrics.pause_until = datetime.now(timezone.utc) + timedelta(hours=24)
                return False

        return True

    def check_risk_reward(self, entry_price: float, signal: Signal) -> Optional[float]:
        """Compute R:R ratio given a known entry price. Call this after price fetch."""
        if not signal.stop_loss or not signal.take_profit:
            return None
        sl_dist = abs(entry_price - signal.stop_loss)
        tp_dist = abs(entry_price - signal.take_profit)
        if sl_dist == 0:
            return None
        return tp_dist / sl_dist

    # ── Position sizing ───────────────────────────────────────────────────────

    def calculate_position_size(
        self,
        account: AccountInfo,
        signal: Signal,
        current_price: float,
    ) -> float:
        """
        Fixed-fractional position sizing.
        Risk per trade = equity × risk_per_trade_pct / 100
        Position size = risk_amount / (entry - stop_loss)
        """
        risk_pct = self.risk.get("risk_per_trade_pct", 1.0)
        if self.metrics.state == BotState.SAFE_MODE:
            reduction = self.safe_cfg.get("reduce_position_size_pct", 50)
            risk_pct *= (1 - reduction / 100)

        risk_amount = account.equity * (risk_pct / 100)
        max_position_value = account.equity * self.risk.get("max_position_size_pct", 5.0) / 100

        if signal.stop_loss and signal.stop_loss != current_price:
            sl_distance = abs(current_price - signal.stop_loss)
            if sl_distance > 0:
                qty = risk_amount / sl_distance
            else:
                qty = risk_amount / (current_price * 0.015)
        else:
            # Fallback: use default stop pct
            default_sl_pct = self.sl_cfg.get("default_pct", 1.5) / 100
            qty = risk_amount / (current_price * default_sl_pct)

        # Cap by max position value
        max_qty = max_position_value / current_price
        qty = min(qty, max_qty)

        logger.debug(
            f"Position size {signal.symbol}: equity={account.equity:.0f}, "
            f"risk={risk_amount:.0f}, price={current_price:.4f}, qty={qty:.4f}"
        )
        return round(qty, 6)

    # ── Trade outcome recording ───────────────────────────────────────────────

    def record_trade_result(self, pnl: float) -> None:
        self.metrics.daily_pnl += pnl
        self.metrics.weekly_pnl += pnl
        self.metrics.monthly_pnl += pnl
        self.metrics.total_pnl += pnl
        self.metrics.trades_today += 1

        if pnl < 0:
            self.metrics.consecutive_losses += 1
        else:
            self.metrics.consecutive_losses = 0

        max_losses = self.risk.get("max_consecutive_losses", 4)
        if self.metrics.consecutive_losses >= max_losses:
            pause_h = self.risk.get("pause_after_loss_streak_hours", 4)
            logger.warning(
                f"{self.metrics.consecutive_losses} consecutive losses — "
                f"pausing for {pause_h}h"
            )
            self.metrics.state = BotState.PAUSED
            self.metrics.pause_until = datetime.now(timezone.utc) + timedelta(hours=pause_h)

        # Total drawdown hard stop
        total_dd_pct = (-self.metrics.total_pnl / self.metrics.equity_high_water * 100
                        if self.metrics.equity_high_water > 0 else 0)
        max_total = self.risk.get("max_total_drawdown_pct", 15.0)
        if total_dd_pct >= max_total:
            logger.critical(
                f"TOTAL DRAWDOWN {total_dd_pct:.2f}% ≥ {max_total}% — HARD STOP"
            )
            self.metrics.state = BotState.STOPPED
            # Set recovery timer so auto_recover in bot.py knows when 24h are up
            self.metrics.pause_until = datetime.now(timezone.utc) + timedelta(hours=24)

    # ── State report ──────────────────────────────────────────────────────────

    def status_summary(self) -> dict:
        m = self.metrics
        return {
            "state": m.state.value,
            "daily_pnl": round(m.daily_pnl, 2),
            "weekly_pnl": round(m.weekly_pnl, 2),
            "monthly_pnl": round(m.monthly_pnl, 2),
            "total_pnl": round(m.total_pnl, 2),
            "consecutive_losses": m.consecutive_losses,
            "trades_today": m.trades_today,
            "open_positions": m.open_positions,
            "equity_hwm": round(m.equity_high_water, 2),
            "paused_until": str(m.pause_until) if m.pause_until else None,
        }
