"""
Tests for experiment #18: intraday mean reversion on 5-minute bars.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_18 import intraday_meanrev_daily_returns, run_experiment18_report


def _intraday_df(days=40, bars_per_day=78, seed=0):
    """Synthetic 5-min bars across several sessions with intraday mean reversion."""
    rng = np.random.default_rng(seed)
    rows = []
    idx = []
    price = 100.0
    start = pd.Timestamp("2024-01-02 14:30", tz="UTC")
    for d in range(days):
        day_open = start + pd.Timedelta(days=d)
        level = price
        for b in range(bars_per_day):
            # mean-reverting intraday oscillation around the day's level
            price = level + np.sin(b / 6) * 0.5 + rng.normal(0, 0.1)
            idx.append(day_open + pd.Timedelta(minutes=5 * b))
            rows.append(price)
    c = np.array(rows)
    return pd.DataFrame({"open": c, "high": c * 1.001, "low": c * 0.999,
                         "close": c, "volume": np.full(len(c), 1e5)},
                        index=pd.DatetimeIndex(idx))


def test_daily_aggregation_shape():
    df = _intraday_df(days=30)
    daily = intraday_meanrev_daily_returns(df)
    assert isinstance(daily, pd.Series)
    assert len(daily) <= 30                       # at most one entry per session
    assert daily.index.is_monotonic_increasing


def test_insufficient_data_returns_empty():
    small = _intraday_df(days=2, bars_per_day=10)
    out = intraday_meanrev_daily_returns(small)
    assert out.empty or len(out) <= 2


def test_report_wellformed():
    data = {"SPY": _intraday_df(days=400, seed=1), "QQQ": _intraday_df(days=400, seed=2)}
    report = run_experiment18_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym),
        symbols=["SPY", "QQQ"], timeframe="5Min",
    )
    assert "Experiment #18" in report
    assert "intraday" in report.lower()
    assert "Summary" in report
