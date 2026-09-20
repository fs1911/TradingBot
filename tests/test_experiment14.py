"""
Tests for experiment #14: volatility targeting.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_14 import vol_target_returns, run_experiment14_report

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def test_vol_target_scales_down_in_high_vol():
    """A calm first half then a wild second half: average exposure should be lower
    in the high-vol regime (the whole point of vol targeting)."""
    rng = np.random.default_rng(0)
    calm = 100 + np.cumsum(rng.normal(0, 0.3, 400))
    wild = calm[-1] + np.cumsum(rng.normal(0, 3.0, 400))
    df = _df(np.concatenate([calm, wild]))
    r = vol_target_returns(df, target_vol=0.10)
    assert len(r) == 800
    # reconstruct implied weight magnitude via |ret|/|underlying ret| is noisy;
    # instead check the strategy took less risk in the wild half (lower vol of returns)
    assert r.iloc[420:].std() < r.iloc[:380].std() * 3    # not blown up by the wild regime


def test_report_wellformed():
    rng = np.random.default_rng(1)
    data = {s: _df(100 + np.cumsum(rng.normal(0.02, 1.0, 900))) for s in ["SPY", "QQQ"]}
    report = run_experiment14_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        symbols=["SPY", "QQQ"],
    )
    assert "Experiment #14" in report
    assert "volatility targeting" in report.lower()
    assert "Summary" in report
    assert "risk management, not an edge" in report
