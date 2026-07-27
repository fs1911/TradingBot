"""Unit tests for the risk manager."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.risk.risk_manager import RiskManager, BotState
from src.strategies.base_strategy import Signal, SignalType
from src.brokers.base_broker import AccountInfo


RISK_CONFIG = {
    "risk": {
        "risk_per_trade_pct": 1.0,
        "max_position_size_pct": 5.0,
        "max_open_positions": 5,
        "max_daily_drawdown_pct": 3.0,
        "max_weekly_drawdown_pct": 6.0,
        "max_monthly_drawdown_pct": 10.0,
        "max_total_drawdown_pct": 15.0,
        "max_consecutive_losses": 3,
        "pause_after_loss_streak_hours": 2,
        "safe_mode": {
            "enabled": True,
            "reduce_position_size_pct": 50,
            "disable_new_entries": False,
        },
    },
    "stop_loss": {"default_pct": 1.5, "use_atr": True, "hard_stop_pct": 3.0},
    "take_profit": {"default_pct": 3.0, "use_atr": True, "min_risk_reward_ratio": 1.5},
    "session_filter": {"enabled": True},
}


@pytest.fixture
def rm():
    return RiskManager(RISK_CONFIG)


@pytest.fixture
def account():
    return AccountInfo(equity=10_000, cash=10_000, buying_power=10_000)


@pytest.fixture
def long_signal():
    return Signal(
        symbol="SPY",
        signal=SignalType.LONG,
        strategy="ema_crossover",
        score=0.75,
        stop_loss=490.0,
        take_profit=510.0,
    )


def test_initial_state(rm):
    assert rm.metrics.state == BotState.ACTIVE
    assert rm.metrics.consecutive_losses == 0


def test_daily_reset_sets_hwm(rm, account):
    rm.daily_reset(account)
    assert rm.metrics.equity_high_water == 10_000


def test_approve_signal_active(rm, account, long_signal):
    rm.daily_reset(account)
    assert rm.approve_signal(long_signal, account) is True


def test_approve_signal_rejected_when_stopped(rm, account, long_signal):
    rm.daily_reset(account)
    rm.metrics.state = BotState.STOPPED
    assert rm.approve_signal(long_signal, account) is False


def test_approve_signal_max_positions(rm, account, long_signal):
    rm.daily_reset(account)
    rm.metrics.open_positions = 5  # At cap
    assert rm.approve_signal(long_signal, account) is False


def test_consecutive_loss_pause(rm, account):
    rm.daily_reset(account)
    for _ in range(3):
        rm.record_trade_result(-100)
    assert rm.metrics.state == BotState.PAUSED
    assert rm.metrics.pause_until is not None


def test_position_size_calculation(rm, account, long_signal):
    rm.daily_reset(account)
    qty = rm.calculate_position_size(account, long_signal, current_price=500.0)
    # Risk = 10000 * 1% = 100; SL dist = 500 - 490 = 10; qty_natural = 10
    # But max_position_size_pct = 5% → max_position_value = $500 → max_qty = 500/500 = 1
    # Position cap kicks in → expected qty = 1.0
    assert abs(qty - 1.0) < 0.01


def test_position_size_uncapped(rm):
    """Verify uncapped sizing: use a low-price instrument so cap doesn't bind."""
    # price=$5, SL=$4 → SL_dist=$1
    # risk = 10000 * 1% = $100 → qty_natural = 100
    # max_position_value = 10000 * 5% = $500 → max_qty = 500/5 = 100
    # Both converge at 100
    account = AccountInfo(equity=10_000, cash=10_000, buying_power=10_000)
    signal = Signal(symbol="LOW", signal=SignalType.LONG, strategy="test",
                    score=0.8, stop_loss=4.0, take_profit=8.0)
    rm.daily_reset(account)
    qty = rm.calculate_position_size(account, signal, current_price=5.0)
    assert abs(qty - 100.0) < 0.1


def test_position_size_capped_for_cheap_asset(rm, account):
    """A very low-priced, low-stop-distance asset (memecoin) must still not
    produce a position worth more than max_position_size_pct of equity — the
    invariant the experiment appeared to violate (SHIB oversized)."""
    rm.daily_reset(account)  # equity = 10_000
    sig = Signal(symbol="SHIB/USD", signal=SignalType.LONG, strategy="test",
                 score=0.9, stop_loss=0.0000199, take_profit=0.000025)
    qty = rm.calculate_position_size(account, sig, current_price=0.00002)
    position_value = qty * 0.00002
    cap = account.equity * 0.05  # max_position_size_pct = 5%
    assert position_value <= cap + 1e-6, f"position ${position_value:.2f} exceeds ${cap:.2f} cap"


def test_position_size_safe_mode(rm, account, long_signal):
    rm.daily_reset(account)
    rm.metrics.state = BotState.SAFE_MODE
    qty_normal = rm.calculate_position_size(account, long_signal, current_price=500.0)
    # Safe mode halves risk_pct → half the size
    assert qty_normal < 10.0


def test_daily_drawdown_triggers_pause(rm, account, long_signal):
    rm.daily_reset(account)
    # Simulate -3% daily loss
    rm.metrics.daily_pnl = -300.0
    approved = rm.approve_signal(long_signal, account)
    assert not approved
    assert rm.metrics.state == BotState.PAUSED


def test_total_drawdown_hard_stop(rm, account):
    rm.daily_reset(account)
    # Simulate 15% total loss
    rm.metrics.total_pnl = -1_500.0
    rm.record_trade_result(-1.0)  # Any additional loss
    assert rm.metrics.state == BotState.STOPPED


def test_status_summary_keys(rm, account):
    rm.daily_reset(account)
    s = rm.status_summary()
    for key in ("state", "daily_pnl", "consecutive_losses", "trades_today"):
        assert key in s
