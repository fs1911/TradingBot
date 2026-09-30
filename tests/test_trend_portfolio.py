"""
Tests for the live multi-asset trend portfolio (long-only, monthly).
"""
from datetime import datetime, timezone
from unittest.mock import Mock

import numpy as np
import pandas as pd

from src.strategies.trend_portfolio import (
    build_panel, signals, target_weights, rebalance_orders, rebalance_due,
)


def _series(start, n, drift, vol, seed, freq="B"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq=freq)
    return pd.Series(100 * np.exp(np.cumsum(drift + rng.normal(0, vol, n))), index=idx)


def _closes():
    return {
        "SPY": _series("2024-01-01", 450, 0.0008, 0.010, 1),    # up
        "TLT": _series("2024-01-01", 450, -0.0008, 0.008, 2),   # down
        "GLD": _series("2024-01-01", 450, 0.0006, 0.009, 3),    # up
        "BIL": _series("2024-01-01", 450, 0.00015, 0.0002, 4),  # cash
        "BTC/USD": _series("2024-01-01", 630, 0.002, 0.03, 5, freq="D"),   # 24/7, up
    }


def test_build_panel_aligns_crypto_to_calendar():
    p = build_panel(_closes(), "SPY")
    assert p.index.equals(_closes()["SPY"].index)
    assert p["BTC/USD"].notna().sum() > 400


def test_signals_long_only():
    s = signals(build_panel(_closes(), "SPY"), "BIL")
    assert s["SPY"] > 0 and s["GLD"] > 0 and s["BTC/USD"] > 0
    assert s["TLT"] == 0.0
    assert ((s >= 0) & (s <= 1)).all()


def test_signals_skip_short_history_and_stale():
    c = _closes()
    c["NEW"] = _series("2025-03-01", 60, 0.001, 0.01, 9)       # < 1 year of data
    c["OLD"] = _series("2024-01-01", 300, 0.001, 0.01, 10)     # stale: ends months ago
    s = signals(build_panel(c, "SPY"), "BIL")
    assert "NEW" not in s.index and "OLD" not in s.index


def test_target_weights_caps_and_no_leverage():
    w = target_weights(build_panel(_closes(), "SPY"), "BIL", target_vol=0.5,
                       max_gross=1.0, max_weight=0.25, caps={"BTC/USD": 0.10})
    assert "TLT" not in w.index
    assert (w >= 0).all() and w.sum() <= 1.0 + 1e-9
    assert w.max() <= 0.25 + 1e-9 and w["BTC/USD"] <= 0.10 + 1e-9


def test_target_weights_all_down_is_all_cash():
    c = {k: _series("2024-01-01", 450, -0.001, 0.01, i) for i, k in enumerate(["SPY", "EFA", "GLD"])}
    c["BIL"] = _series("2024-01-01", 450, 0.00015, 0.0002, 7)
    assert target_weights(build_panel(c, "SPY"), "BIL").empty


def test_rebalance_orders():
    w = pd.Series({"SPY": 0.20, "GLD": 0.10})
    prices = {"SPY": 500.0, "GLD": 200.0, "TLT": 90.0, "XLV": 140.0}
    holdings = {"SPY": 30.0, "TLT": 50.0, "GLD": 49.5}
    orders = {o[0]: o for o in rebalance_orders(w, 100_000, prices, holdings, 200, 0.01)}
    assert orders["TLT"][1] == -50.0 and orders["TLT"][2] == "exit"
    assert orders["SPY"][2] == "rebalance" and abs(orders["SPY"][1] - 10.0) < 1e-9
    assert "GLD" not in orders            # 9,900 vs 10,000 target: below threshold
    seq = rebalance_orders(w, 100_000, prices, holdings, 200, 0.01)
    assert seq[0][1] < 0                  # sells first


def test_rebalance_due():
    t = datetime(2026, 10, 1, 15, 30, tzinfo=timezone.utc)
    assert rebalance_due(t, "2026-09", True)
    assert not rebalance_due(t, "2026-10", True)
    assert not rebalance_due(t, "2026-09", False)
    assert not rebalance_due(datetime(2026, 10, 1, 14, 0, tzinfo=timezone.utc), "2026-09", True)
    assert rebalance_due(t, None, True)


def test_portfolio_tick_end_to_end(tmp_path):
    from src.bot import TradingBot
    from src.brokers.base_broker import Position, OrderSide, AccountInfo
    closes = _closes()
    bot = object.__new__(TradingBot)
    bot.bot_cfg = {"portfolio": {"enabled": True, "calendar": "SPY", "cash_symbol": "BIL",
                                 "universe": ["SPY", "TLT", "GLD", "BTC/USD"],
                                 "caps": {"BTC/USD": 0.10}, "target_vol": 0.10}}
    bot._portfolio_state_path = tmp_path / "ps.json"
    bot._portfolio_log_path = tmp_path / "pr.csv"
    bot._open_trades_path = tmp_path / "ot.json"
    bot._open_trades = {"AAPL": {}}
    legacy = Position(symbol="AAPL", qty=-9, entry_price=200, current_price=201,
                      unrealized_pnl=-9, side=OrderSide.SELL)
    bot.broker = Mock()
    bot.broker.get_ohlcv.side_effect = lambda s, tf, limit=400: pd.DataFrame({"close": closes[s]})
    bot.broker.get_positions.side_effect = [[legacy], []]
    bot.broker.get_account.return_value = AccountInfo(equity=60_000, cash=60_000, buying_power=60_000)
    bot.broker.close_position.return_value = True
    bot.broker.place_order.side_effect = lambda o: (setattr(o, "order_id", "id1"), o)[1]
    bot.telegram = Mock()
    now = datetime(2025, 5, 2, 16, 0, tzinfo=timezone.utc)
    bot._portfolio_tick(now, bot.broker.get_account(), market_open=True)
    bot.broker.close_position.assert_any_call("AAPL")            # legacy short closed
    bought = {c.args[0].symbol for c in bot.broker.place_order.call_args_list}
    assert "SPY" in bought and "TLT" not in bought
    assert bot._load_portfolio_state()["last_month"] == "2025-05"
    assert bot._open_trades == {}
    # same month again → nothing happens
    bot.broker.place_order.reset_mock()
    bot._portfolio_tick(now, bot.broker.get_account(), market_open=True)
    bot.broker.place_order.assert_not_called()
