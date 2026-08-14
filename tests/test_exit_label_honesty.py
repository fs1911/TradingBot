"""
Regression test for the "tp with a loss" mislabel. When a take-profit / trailing
exit actually closes at a loss (spread / late fill), the journal must record what
really happened ("spread_loss"), not a dishonest "tp". Verifies the relabel in
_manage_open_positions.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from src.bot import TradingBot
from src.brokers.base_broker import Position, OrderSide, AccountInfo


def _make_bot(tmp_path, *, tp, price):
    bot = object.__new__(TradingBot)
    bot.bot_cfg = {"bot": {"min_hold_seconds": 120, "max_hold_hours": 24}}
    bot.risk_cfg = {"trailing_stop": {"enabled": False}}
    bot._cooldown_path = tmp_path / "cd.json"
    bot._sl_cooldown = {}
    # Opened 200s ago so the min-hold gate is already released.
    bot._open_trades = {
        "ETH/USD": {
            "order_id": "x", "entry_price": 100.0, "side": OrderSide.BUY,
            "qty": 1.0, "sl": None, "tp": tp, "strategy": "test",
            "opened_at": datetime.now(timezone.utc) - timedelta(seconds=200),
        }
    }
    pos = Position(symbol="ETH/USD", qty=1.0, entry_price=100.0,
                   current_price=price, unrealized_pnl=price - 100.0, side=OrderSide.BUY)
    bot.broker = Mock()
    bot.broker.get_positions.return_value = [pos]
    bot.broker.close_position.return_value = True
    bot.risk_manager = Mock()
    bot.risk_manager.metrics.state = "active"
    bot.risk_manager.metrics.open_positions = 1
    bot.telegram = Mock()
    bot.reporter = Mock()
    return bot


def test_tp_closing_at_loss_is_relabelled(tmp_path):
    """tp below entry → price crosses it at a loss → recorded as 'spread_loss'."""
    bot = _make_bot(tmp_path, tp=97.0, price=98.0)   # price>=tp fires, but 98<100 entry = loss
    bot._manage_open_positions(AccountInfo(equity=10000, cash=10000, buying_power=10000))
    bot.reporter.log_trade.assert_called_once()
    assert bot.reporter.log_trade.call_args.kwargs["exit_reason"] == "spread_loss"


def test_genuine_tp_win_keeps_tp_label(tmp_path):
    """A real profitable take-profit keeps the honest 'tp' label."""
    bot = _make_bot(tmp_path, tp=105.0, price=106.0)  # 106>=105 and 106>100 entry = win
    bot._manage_open_positions(AccountInfo(equity=10000, cash=10000, buying_power=10000))
    bot.reporter.log_trade.assert_called_once()
    assert bot.reporter.log_trade.call_args.kwargs["exit_reason"] == "tp"
