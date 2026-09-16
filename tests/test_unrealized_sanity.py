"""
Regression test for the unrealized-P&L glitch: the heartbeat must use the broker's
own unrealized P&L and ignore a single position whose |unrealized| exceeds account
equity (physically impossible → corrupt data), instead of the old recompute that
reported +$83k on 0.04 BTC and poisoned the whole realized/unrealized split.
"""
from unittest.mock import Mock
from src.bot import TradingBot
from src.brokers.base_broker import Position, OrderSide, AccountInfo


def _pos(symbol, qty, entry, current, unreal, side):
    return Position(symbol=symbol, qty=qty, entry_price=entry,
                    current_price=current, unrealized_pnl=unreal, side=side)


def _bot(tmp_path, positions, equity):
    bot = object.__new__(TradingBot)
    bot._last_heartbeat = None
    bot._pnl_baseline = 68485.0
    bot._equity_history_path = tmp_path / "eq.csv"
    bot._open_trades = {}
    bot._market_trend = "flat"
    bot.broker = Mock()
    bot.broker.get_positions.return_value = positions
    bot.risk_manager = Mock()
    bot.risk_manager.metrics.state.value = "active"
    bot.risk_manager.metrics.trades_today = 2
    bot.risk_manager.metrics.daily_pnl = -88.0
    bot.heartbeat = Mock()
    bot.heartbeat.build_status.return_value = {}
    bot.journal_syncer = Mock()
    return bot


def test_corrupt_unrealized_is_ignored(tmp_path):
    import datetime as dt
    positions = [
        _pos("AVAX/USD", 431.0, 20.0, 19.9, -19.63, OrderSide.BUY),   # sane
        _pos("BTC/USD", 0.0415, 0.0, 110000.0, 83233.21, OrderSide.BUY),  # corrupt: > equity
        _pos("CRM", 12.0, 300.0, 296.0, 43.08, OrderSide.SELL),       # sane
    ]
    bot = _bot(tmp_path, positions, equity=63240.0)
    account = AccountInfo(equity=63240.0, cash=1000.0, buying_power=1000.0)
    bot._maybe_heartbeat(dt.datetime.now(dt.timezone.utc), account)

    kwargs = bot.heartbeat.build_status.call_args.kwargs
    # only the two sane positions counted; the +83k BTC glitch dropped
    assert round(kwargs["unrealized_pnl"], 2) == round(-19.63 + 43.08, 2)
    # realized stays consistent with equity: total = equity - baseline
    assert round(kwargs["realized_pnl"] + kwargs["unrealized_pnl"], 2) == round(63240.0 - 68485.0, 2)
    # the corrupt position is not in the per-position detail
    assert all(p["symbol"] != "BTC/USD" for p in kwargs["positions"])
