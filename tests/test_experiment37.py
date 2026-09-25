"""
Tests for experiment #37: volatility risk premium.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_37 import (
    realized_forward_vol, vrp_table, monthly_returns, alpha_beta, mstats,
    run_experiment37_report,
)


def _spx(n=8000, vol=0.01, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("1990-01-02", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, vol, n))), index=idx)


def test_realized_forward_vol_matches_constant_vol():
    rv = realized_forward_vol(_spx(vol=0.01), 21).dropna()
    assert abs(rv.mean() - 0.01 * np.sqrt(252)) < 0.02
    assert np.isnan(realized_forward_vol(_spx(), 21).iloc[-1])      # forward-looking


def test_vrp_positive_when_vix_exceeds_realized():
    spx = _spx(vol=0.01)
    vix = pd.Series(0.01 * np.sqrt(252) * 100 + 4.0, index=spx.index)  # ~4 pts rich
    tab = vrp_table(vix, spx)
    assert tab["full"]["mean_pts"] > 3 and tab["full"]["t"] > 5
    assert tab["full"]["pct_pos"] > 90
    assert tab["since 2018"] is not None


def test_alpha_beta_recovers_planted_alpha():
    idx = pd.period_range("1990-01", periods=300, freq="M")
    rng = np.random.default_rng(1)
    x = pd.Series(rng.normal(0.007, 0.04, 300), index=idx)
    y = 0.002 + 0.5 * x + pd.Series(rng.normal(0, 0.005, 300), index=idx)
    ab = alpha_beta(y, x)
    assert abs(ab["beta"] - 0.5) < 0.05 and abs(ab["alpha"] - 0.024) < 0.01 and ab["t"] > 3


def test_monthly_returns_and_mstats():
    m = monthly_returns(_spx(n=600))
    assert len(m) > 20
    st = mstats(m)
    assert {"cagr", "vol", "sharpe", "maxdd", "worst", "skew"} <= set(st)


def test_report_structure_and_missing():
    spx = _spx()
    vix = pd.Series(20.0, index=spx.index)
    put = spx * 0.9 + 10
    rep = run_experiment37_report({"VIX": vix, "GSPC": spx, "SP500TR": spx, "PUT": put,
                                   "BXM": pd.Series(dtype=float), "SVXY": pd.Series(dtype=float)},
                                  n_trials=10)
    assert "Experiment #37" in rep and "Does implied volatility exceed" in rep
    assert "PutWrite" in rep and "no data" in rep and "Summary" in rep
    rep2 = run_experiment37_report({"VIX": pd.Series(dtype=float), "GSPC": pd.Series(dtype=float),
                                    "SP500TR": pd.Series(dtype=float)})
    assert "skipped" in rep2
