"""
Regression test for the realized-P&L fix: realized P&L must be derived from the
account (equity − baseline − unrealized), consistent with the account value, not
an in-memory counter that resets on restart. The baseline is the first equity in
equity_history.csv, so it survives restarts.
"""
from src.bot import TradingBot
from src.monitoring.heartbeat import Heartbeat


def _bot(tmp_path):
    bot = object.__new__(TradingBot)
    bot._equity_history_path = tmp_path / "equity_history.csv"
    bot._pnl_baseline = None
    return bot


def test_baseline_read_from_history_first_row(tmp_path):
    p = tmp_path / "equity_history.csv"
    p.write_text(
        "utc,equity_usd,realized_pnl_usd,unrealized_pnl_usd,open_positions,daily_pnl_usd\n"
        "2026-07-27 07:59:06,68484.99,0.0,-170.59,9,0.0\n"
        "2026-07-27 08:59:06,68500.00,10.0,5.0,9,10.0\n"
    )
    bot = _bot(tmp_path)
    assert bot._get_pnl_baseline(66000.0) == 68484.99
    # cached on second call even if a different equity is passed
    assert bot._get_pnl_baseline(1.0) == 68484.99


def test_baseline_falls_back_to_current_on_first_run(tmp_path):
    bot = _bot(tmp_path)                     # no history file yet
    assert bot._get_pnl_baseline(70000.0) == 70000.0


def test_realized_consistent_with_equity(tmp_path):
    """realized = (equity − baseline) − unrealized, so realized+unrealized == total
    P&L == equity − baseline. This is the property the old counter violated."""
    p = tmp_path / "equity_history.csv"
    p.write_text(
        "utc,equity_usd,realized_pnl_usd,unrealized_pnl_usd,open_positions,daily_pnl_usd\n"
        "2026-07-27 07:59:06,68485.00,0.0,0.0,0,0.0\n"
    )
    bot = _bot(tmp_path)
    equity, unrealized = 66297.0, -41.0
    baseline = bot._get_pnl_baseline(equity)
    realized = (equity - baseline) - unrealized
    assert round(realized + unrealized, 2) == round(equity - baseline, 2)
    assert round(equity - baseline, 2) == -2188.0     # the real bottom line

    status = Heartbeat().build_status(
        state="active", open_positions=0, trades_today=0, equity=equity,
        market_trend="flat", daily_pnl=0.0, realized_pnl=realized,
        unrealized_pnl=unrealized, positions=[])
    assert status["total_pnl_usd"] == -2188.0
