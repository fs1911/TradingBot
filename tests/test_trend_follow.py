"""
Tests for the daily-bar trend-following edge test. Real Alpaca data can't be
fetched in CI, so these use synthetic series: a strong uptrend the system should
profit from, a downtrend it should stay flat on (long-only), and a well-formed
grouped report.
"""
import numpy as np
import pandas as pd

from src.backtest.trend_follow import run_trend_backtest, run_trend_report, SYSTEMS


def _series(closes):
    n = len(closes)
    idx = pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")
    close = np.asarray(closes, dtype=float)
    high = close * 1.005
    low = close * 0.995
    return pd.DataFrame({"open": close, "high": high, "low": low,
                         "close": close, "volume": np.full(n, 1e6)}, index=idx)


def test_uptrend_is_profitable():
    """A clean persistent uptrend → the long/flat trend system makes money."""
    df = _series(100 + np.arange(400) * 0.5)          # steady rise
    trades = run_trend_backtest(df, fast=20, slow=100, atr_mult=3.0, atr_period=14)
    assert trades, "should take at least one trade in a clear uptrend"
    assert sum(t.pnl for t in trades) > 0


def test_downtrend_stays_flat():
    """A persistent downtrend → long-only system never enters (close < SMA)."""
    df = _series(300 - np.arange(400) * 0.5)          # steady fall
    trades = run_trend_backtest(df, fast=20, slow=100, atr_mult=3.0, atr_period=14)
    assert trades == []


def test_report_wellformed():
    up = _series(100 + np.arange(500) * 0.4)
    report = run_trend_report(
        get_ohlcv=lambda sym, tf, limit: up,
        universes={"metals": ["GLD", "SLV"]},
        limit=500,
    )
    assert "Daily Trend-Following Edge Test" in report
    assert "METALS" in report
    for s in SYSTEMS:
        assert s["name"] in report
    assert "OOS PF" in report and "Verdict" in report
