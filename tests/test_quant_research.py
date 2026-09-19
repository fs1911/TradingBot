"""
Tests for the quant-research module: structure diagnostics and pairs stat-arb.
"""
import numpy as np
import pandas as pd

from src.backtest.quant_research import (
    hurst_exponent, variance_ratio, _half_life, backtest_pair,
    find_pairs, run_quant_report,
)


def _df(closes):
    n = len(closes)
    idx = pd.date_range("2016-01-01", periods=n, freq="1D", tz="UTC")
    c = np.asarray(closes, float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=idx)


def _ou(n, theta=0.1, sigma=1.0, seed=0):
    """Mean-reverting Ornstein-Uhlenbeck series (stationary)."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = x[t - 1] - theta * x[t - 1] + sigma * rng.normal()
    return x


def test_hurst_detects_mean_reversion_and_trend():
    mr = pd.Series(100 + _ou(1500, theta=0.2))          # stationary → H < 0.5
    trend = pd.Series(100 + np.arange(1500) * 0.3)       # deterministic up → H > 0.5
    assert hurst_exponent(mr) < 0.5
    assert hurst_exponent(trend) > 0.5


def test_half_life_finite_for_mean_reverting_spread():
    s = pd.Series(_ou(1000, theta=0.15))
    hl = _half_life(s)
    assert np.isfinite(hl) and hl > 0


def test_pair_strategy_profits_on_cointegrated_pair():
    """A shared random-walk factor + a stationary spread → the pair is cointegrated
    and the market-neutral z-score strategy should be profitable."""
    n = 1500
    rng = np.random.default_rng(1)
    common = 100 + np.cumsum(rng.normal(0, 1, n))        # common stochastic trend
    spread = _ou(n, theta=0.1, sigma=0.5, seed=2)        # stationary spread
    a = common + spread
    b = common
    r = backtest_pair(_df(a)["close"], _df(b)["close"], beta_window=120, z_window=60)
    assert not r.empty
    assert (1 + r).prod() > 1.0                          # profitable on a true cointegrated pair


def test_report_wellformed():
    n = 900
    rng = np.random.default_rng(7)
    common = 100 + np.cumsum(rng.normal(0, 1, n))
    data = {
        "AAA": _df(common + _ou(n, theta=0.1, seed=1)),
        "BBB": _df(common + _ou(n, theta=0.1, seed=2)),
        "CCC": _df(100 + np.cumsum(rng.normal(0, 1, n))),   # independent
    }
    report = run_quant_report(
        get_ohlcv=lambda sym, tf, limit: data[sym],
        symbols=list(data), limit=n, window=252, step=126,
    )
    assert "Quant Research" in report
    assert "Market structure" in report
    assert "Hurst" in report
    assert "pairs" in report.lower()
