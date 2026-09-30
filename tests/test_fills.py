"""
Journal books real fills and fees: exit at the broker's fill price, crypto taker
fee on both legs, notes explain signal vs fill. Without fill data it falls back to
the signal price (and says so).
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from src.bot import TradingBot, _valid_fill
from src.brokers.base_broker import Position, OrderSide, AccountInfo
from src.monitoring.trade_state import trade_fee


def _bot(tmp_path, symbol, price, close_fill):
    bot = object.__new__(TradingBot)
    bot.bot_cfg = {"bot": {"min_hold_seconds": 120, "max_hold_hours": 1, "crypto_fee_bps": 25}}
    bot.risk_cfg = {"trailing_stop": {"enabled": False}}
    bot._cooldown_path = tmp_path / "cd.json"
    bot._open_trades_path = tmp_path / "open_trades.json"
    bot._sl_cooldown = {}
    bot._open_trades = {symbol: {
        "order_id": "x", "entry_price": 100.0, "signal_price": 99.9, "fill_known": True,
        "side": OrderSide.BUY, "qty": 2.0, "sl": None, "tp": None, "strategy": "test",
        "opened_at": datetime.now(timezone.utc) - timedelta(hours=2)}}   # → time_limit exit
    bot.broker = Mock()
    bot.broker.get_positions.return_value = [Position(symbol=symbol, qty=2.0, entry_price=100.0,
                                                      current_price=price, unrealized_pnl=0.0,
                                                      side=OrderSide.BUY)]
    bot.broker.close_position.return_value = True
    bot.broker.get_close_fill.return_value = close_fill
    bot.risk_manager = Mock()
    bot.risk_manager.metrics.state = "active"
    bot.risk_manager.metrics.open_positions = 1
    bot.telegram = Mock()
    bot.reporter = Mock()
    return bot


def test_valid_fill():
    assert _valid_fill((101.5, 2.0)) == (101.5, 2.0)
    assert _valid_fill(None) is None
    assert _valid_fill(Mock()) is None
    assert _valid_fill((0.0, 1.0)) is None


def test_trade_fee_crypto_only():
    assert trade_fee("SPY", 500, 510, 10) == 0.0
    assert abs(trade_fee("BTC/USD", 100, 110, 2, 25) - 2 * 210 * 0.0025) < 1e-12


def test_exit_uses_fill_price_and_books_fee(tmp_path):
    bot = _bot(tmp_path, "ETH/USD", price=110.0, close_fill=(109.0, 2.0))
    bot._manage_open_positions(AccountInfo(equity=10000, cash=10000, buying_power=10000))
    kw = bot.reporter.log_trade.call_args.kwargs
    fee = 2 * (100 + 109) * 0.0025
    assert kw["exit_price"] == 109.0
    assert abs(kw["pnl"] - (9.0 * 2 - fee)) < 1e-9
    assert "signal 110" in kw["notes"] and "fee est" in kw["notes"]


def test_exit_without_fill_falls_back_to_signal(tmp_path):
    bot = _bot(tmp_path, "SPY", price=110.0, close_fill=None)
    bot._manage_open_positions(AccountInfo(equity=10000, cash=10000, buying_power=10000))
    kw = bot.reporter.log_trade.call_args.kwargs
    assert kw["exit_price"] == 110.0 and kw["pnl"] == 20.0
    assert "no fill data" in kw["notes"]


def test_alpaca_fee_activity_to_usd():
    import pytest
    ab = pytest.importorskip("src.brokers.alpaca_broker")
    f = ab.AlpacaBroker._fee_usd
    assert f({"qty": "-0.00025", "price": "80000"}) == pytest.approx(20.0)
    assert f({"net_amount": "-3.5", "qty": "-1", "price": "1"}) == 3.5
    assert f({"qty": None}) == 0.0
