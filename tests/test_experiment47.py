"""
Tests for experiment #47: market signal applied to single stocks.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_47 import market_weights, stock_runs, region_placebo, run_experiment47_report


def _daily(seed, beta=1.0, n=6000, mkt=None):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("1995-01-02", periods=n)
    if mkt is None:
        t = np.arange(n)
        mkt = 0.0004 + np.where((t > 2500) & (t < 3000), -0.003, 0.0) + rng.normal(0, 0.01, n)
    r = beta * mkt + rng.normal(0, 0.012, n)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=idx), mkt


def test_market_weights_and_stock_runs():
    idx_px, mkt = _daily(0, 1.0)
    irx = pd.Series(2.0, index=idx_px.index)
    wm, wmm = market_weights(idx_px, irx, {})
    assert wm.between(0, 1).all() and wmm.equals(wm)   # no macro → same
    st, _ = _daily(1, 1.2, mkt=mkt)
    r = stock_runs(st, irx, wm, wmm)
    assert r and set(r["rets"]) == {"B&H", "Own trend", "Market trend", "Market + macro"}
    # the planted crash: market trend must cut the drawdown of a high-beta stock
    assert r["stats"]["Market trend"]["maxdd"] > r["stats"]["B&H"]["maxdd"]


def test_region_placebo_and_report():
    idx_px, mkt = _daily(0)
    irx = pd.Series(2.0, index=idx_px.index)
    wm, wmm = market_weights(idx_px, irx, {})
    prices = {f"S{i}": _daily(10 + i, 1.0, mkt=mkt)[0] for i in range(6)}
    stocks = {t: stock_runs(d, irx, wm, wmm) for t, d in prices.items()}
    real, p = region_placebo(stocks, irx, wm, n_shifts=20)
    assert np.isfinite(real) and 0 < p <= 1
    rep = run_experiment47_report({"Test": (prices, idx_px)}, irx, {}, n_shifts=10)
    assert "Experiment #47" in rep and "Placebo" in rep and "Summary" in rep
