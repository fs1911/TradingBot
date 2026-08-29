"""
Tests for the volatility risk-premium edge test.
"""
import numpy as np
import pandas as pd

from src.backtest.vol_premium import short_vol_returns, run_vol_report, _stats_plus


def _df(closes):
    n = len(closes)
    idx = pd.date_range("2016-01-01", periods=n, freq="1D", tz="UTC")
    c = np.asarray(closes, float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=idx)


def test_trend_filter_reduces_prolonged_drawdown():
    """A steady rise then a MULTI-day decline: the trend filter exits once price
    falls below its average and so ends better than naive holding. (It cannot dodge
    a one-day gap — only a sustained decline — which is the honest limitation.)"""
    up = 100 + np.arange(200) * 0.5
    decline = up[-1] * (0.96 ** np.arange(60))       # ~-4%/day for 60 days
    df = _df(np.concatenate([up, decline]))
    naive = short_vol_returns(df, sign=1.0, mode="naive", sma=50)
    trend = short_vol_returns(df, sign=1.0, mode="trend", sma=50)
    assert (1 + trend).prod() > (1 + naive).prod()             # filter survives the decline better
    assert _stats_plus(trend)["dd"] > _stats_plus(naive)["dd"]  # smaller (less negative) drawdown


def test_stats_plus_reports_worst_day():
    r = pd.Series([0.01, -0.5, 0.02, 0.01])
    st = _stats_plus(r)
    assert st["worst_day"] == -50.0
    assert "mar" in st and "dd" in st


def test_report_wellformed_and_handles_missing_instrument():
    # SVXY present, SPY present
    svxy = _df(100 + np.arange(700) * 0.1 + np.sin(np.arange(700) / 10))
    spy = _df(100 + np.arange(700) * 0.2)
    data = {"SVXY": svxy, "SPY": spy}
    report = run_vol_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        short_vol_candidates=["SVXY"], benchmark="SPY", limit=700, window=252, step=126,
    )
    assert "Volatility Risk-Premium Edge Test" in report
    assert "worst 1-day%" in report
    assert "Short-vol naive" in report and "trend" in report

    # No instrument available → graceful message, no crash
    empty = run_vol_report(
        get_ohlcv=lambda sym, tf, limit: pd.DataFrame(),
        short_vol_candidates=["SVXY"], benchmark="SPY", limit=700,
    )
    assert "cannot test" in empty
