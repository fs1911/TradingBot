"""
Tests for durable open-trade state, entry plausibility and journal sanitising
(restart artefact: broker avg entry of BTC at −2.2M USD booked +85k fake profit).
"""
from datetime import datetime, timezone

import pandas as pd

from src.brokers.base_broker import OrderSide
from src.monitoring.trade_state import (
    plausible_entry, save_open_trades, load_open_trades, sanitize_journal,
)


def test_plausible_entry():
    assert plausible_entry(100.0, 101.0)
    assert not plausible_entry(-1927407.0, 75940.0)
    assert not plausible_entry(0.0, 10.0)
    assert not plausible_entry(None, 10.0)
    assert not plausible_entry(10.0, 30.0)
    assert not plausible_entry(float("nan"), 10.0)


def test_open_trades_roundtrip(tmp_path):
    p = tmp_path / "open_trades.json"
    t0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    trades = {"BTC/USD": {"order_id": "x1", "entry_price": 80000.0, "side": OrderSide.BUY,
                          "qty": 0.05, "sl": 78000.0, "tp": None, "strategy": "supertrend",
                          "opened_at": t0}}
    save_open_trades(p, trades)
    back = load_open_trades(p)
    assert back["BTC/USD"]["side"] == "buy" and back["BTC/USD"]["opened_at"] == t0
    assert back["BTC/USD"]["strategy"] == "supertrend" and back["BTC/USD"]["tp"] is None
    assert load_open_trades(tmp_path / "missing.json") == {}


def test_sanitize_journal_voids_only_implausible_rows(tmp_path):
    p = tmp_path / "j.csv"
    pd.DataFrame([
        {"symbol": "BTC/USD", "strategy": "restored", "entry_price": -2227542.0, "exit_price": 84104.2,
         "qty": 0.037, "pnl_usd": 85394.44, "pnl_pct": 1.0, "exit_reason": "tp", "notes": None},
        {"symbol": "SPY", "strategy": "supertrend", "entry_price": 500.0, "exit_price": 498.0,
         "qty": 10, "pnl_usd": -20.0, "pnl_pct": -0.4, "exit_reason": "sl", "notes": None},
    ]).to_csv(p, index=False)
    assert sanitize_journal(p) == 1
    df = pd.read_csv(p)
    assert df.loc[0, "pnl_usd"] == 0.0 and df.loc[0, "exit_reason"] == "invalid_entry"
    assert df.loc[1, "pnl_usd"] == -20.0
    assert sanitize_journal(p) == 0  # idempotent


def _bot(tmp_path, positions):
    from unittest.mock import Mock
    from src.bot import TradingBot
    bot = object.__new__(TradingBot)
    bot._open_trades = {}
    bot._open_trades_path = tmp_path / "open_trades.json"
    bot.broker = Mock()
    bot.broker.get_positions.return_value = positions
    return bot


def _pos(sym, side, entry, price, qty=1.0):
    from unittest.mock import Mock
    p = Mock()
    p.symbol, p.side, p.entry_price, p.current_price, p.qty = sym, side, entry, price, qty
    return p


def test_restore_rejects_implausible_broker_entry(tmp_path):
    bot = _bot(tmp_path, [_pos("BTC/USD", OrderSide.BUY, -2227542.0, 84000.0, 0.037)])
    bot._load_existing_positions()
    t = bot._open_trades["BTC/USD"]
    assert t["entry_price"] == 84000.0 and t["strategy"] == "restored"


def test_restore_resumes_persisted_trade(tmp_path):
    t0 = datetime(2026, 9, 29, 13, 45, tzinfo=timezone.utc)
    save_open_trades(tmp_path / "open_trades.json", {
        "MSFT": {"order_id": "o1", "entry_price": 400.0, "side": OrderSide.SELL, "qty": 6,
                 "sl": 404.0, "tp": 390.0, "strategy": "breakout_momentum", "opened_at": t0}})
    bot = _bot(tmp_path, [_pos("MSFT", OrderSide.SELL, 399.5, 402.0, -6)])
    bot._load_existing_positions()
    t = bot._open_trades["MSFT"]
    assert t["strategy"] == "breakout_momentum" and t["sl"] == 404.0 and t["opened_at"] == t0
    assert t["side"] == OrderSide.SELL and t["qty"] == 6
