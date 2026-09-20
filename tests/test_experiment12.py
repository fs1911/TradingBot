"""
Tests for experiment #12 anomaly strategies.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_12 import (
    _rsi, turn_of_month_returns, overnight_returns, rsi2_returns,
    low_vol_returns, run_experiment12_report,
)

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes, opens=None):
    c = np.asarray(closes, float)
    n = len(c)
    o = np.asarray(opens, float) if opens is not None else c
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.01,
                         "low": np.minimum(o, c) * 0.99, "close": c,
                         "volume": np.full(n, 1e6)}, index=IDX(n))


def test_rsi_bounds():
    up = np.cumsum(np.full(100, 1.0)) + 100
    down = 300 - np.cumsum(np.full(100, 1.0))
    assert _rsi(up, 2)[-1] > 90       # steady up -> high RSI
    assert _rsi(down, 2)[-1] < 10     # steady down -> low RSI


def test_turn_of_month_only_invests_some_days():
    df = _df(100 + np.cumsum(np.random.default_rng(0).normal(0, 1, 800)))
    r = turn_of_month_returns(df)
    # not invested every day (some zero-return days from being flat)
    active = (r != 0).mean()
    assert 0 < active < 1


def test_overnight_uses_open_close_gap():
    n = 300
    close = 100 + np.arange(n) * 0.0
    opn = close + 1.0                 # every open 1 above prior close -> positive overnight
    df = _df(close, opn)
    r = overnight_returns(df, commission_pct=0, slippage_pct=0)
    assert r.iloc[5] > 0              # positive overnight drift captured


def test_rsi2_and_lowvol_run():
    rng = np.random.default_rng(1)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 1000)))
    assert len(rsi2_returns(df)) == 1000
    data = {s: _df(100 + np.cumsum(rng.normal(0, 1, 1000))) for s in ["A", "B", "C", "D", "E"]}
    lv = low_vol_returns(data)
    assert not lv.empty


def test_experiment12_report_wellformed():
    rng = np.random.default_rng(2)
    syms = ["SPY", "QQQ", "XLF", "XLK", "XLE", "XLV"]
    data = {s: _df(100 + np.cumsum(rng.normal(0, 1, 900))) for s in syms}
    report = run_experiment12_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        index_symbols=["SPY", "QQQ"], lowvol_universe=syms,
    )
    assert "Experiment #12" in report
    assert "TurnOfMonth" in report and "Overnight" in report and "RSI2" in report
    assert "Summary" in report
