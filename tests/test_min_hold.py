"""
Regression test for the ghost-trade fix: a freshly-opened position must NOT be
closed within the minimum-hold window, even if its price already sits beyond the
stop — that "immediate close" was the spread/mark artifact producing sub-second
ghost trades (incl. impossible "tp with a loss").
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from src.bot import TradingBot
from src.brokers.base_broker import Position, OrderSide, AccountInfo


def _make_bot(tmp_path, opened_at):
    bot = object.__new__(TradingBot)
    bot.bot_cfg = {"bot": {"min_hold_seconds": 120, "max_hold_hours": 24}}
    bot.risk_cfg = {"trailing_stop": {"enabled": False}}
    bot._cooldown_path = tmp_path / "cd.json"
    bot._sl_cooldown = {}
    bot._open_trades = {
        "ETH/USD": {
            "order_id": "x", "entry_price": 100.0, "side": OrderSide.BUY,
            "qty": 1.0, "sl": 99.0, "tp": 110.0, "strategy": "test",
            "opened_at": opened_at,
        }
    }
    # Price 98 is below the stop (99) → would close immediately without the guard
    pos = Position(symbol="ETH/USD", qty=1.0, entry_price=100.0,
                   current_price=98.0, unrealized_pnl=-2.0, side=OrderSide.BUY)
    bot.broker = Mock()
    bot.broker.get_positions.return_value = [pos]
    bot.broker.close_position.return_value = True
    bot.risk_manager = Mock()
    bot.risk_manager.metrics.state = "active"
    bot.risk_manager.metrics.open_positions = 1
    bot.telegram = Mock()
    bot.reporter = Mock()
    return bot


def test_fresh_position_not_closed(tmp_path):
    """Opened just now, price already past the stop → must be held, not closed."""
    bot = _make_bot(tmp_path, datetime.now(timezone.utc))
    bot._manage_open_positions(AccountInfo(equity=10000, cash=10000, buying_power=10000))
    bot.broker.close_position.assert_not_called()
    assert "ETH/USD" in bot._open_trades


def test_old_position_closes_on_stop(tmp_path):
    """Past the min-hold window, the same stop breach DOES close the trade."""
    bot = _make_bot(tmp_path, datetime.now(timezone.utc) - timedelta(seconds=200))
    bot._manage_open_positions(AccountInfo(equity=10000, cash=10000, buying_power=10000))
    bot.broker.close_position.assert_called_once_with("ETH/USD")
    assert "ETH/USD" not in bot._open_trades
