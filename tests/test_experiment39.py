"""
Tests for experiment #39: Sharpe-difference bootstrap, leverage, robustness.
"""
import math
import numpy as np
import pandas as pd

from src.backtest.experiments_39 import (
    prepare, gated, sharpe_excess, sharpe_diff_bootstrap, levered, run_experiment39_report,
)


def _series(n=5000, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("1996-06-01", periods=n)
    sp = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n)))
    pr = 0.5 * np.diff(np.log(sp), prepend=np.log(sp[0])) + 0.0001
    pr[rng.random(n) < 0.002] -= 0.05
    return (pd.Series(100 * np.exp(np.cumsum(pr)), index=idx), pd.Series(sp, index=idx),
            pd.Series(3.0, index=idx))


def test_sharpe_excess_zero_for_cash():
    idx = pd.bdate_range("2000-01-01", periods=500)
    cash = pd.Series(0.0001, index=idx)
    r = cash + pd.Series(np.random.default_rng(0).normal(0, 0.01, 500), index=idx)
    assert abs(sharpe_excess(r, cash)) < 1.5


def test_bootstrap_detects_clear_sharpe_gap_and_not_noise():
    idx = pd.bdate_range("2000-01-01", periods=3000)
    rng = np.random.default_rng(1)
    cash = pd.Series(0.0, index=idx)
    good = pd.Series(rng.normal(0.0008, 0.005, 3000), index=idx)     # Sharpe ~2.5
    bad = pd.Series(rng.normal(0.0001, 0.01, 3000), index=idx)       # Sharpe ~0.16
    bt = sharpe_diff_bootstrap(good, bad, cash, n=400)
    assert bt["obs"] > 1.5 and bt["p"] < 0.01 and bt["lo"] > 0
    same = sharpe_diff_bootstrap(bad, bad, cash, n=200)
    assert same["p"] == 1.0                                          # no difference


def test_levered_cost_and_scaling():
    idx = pd.bdate_range("2000-01-01", periods=10)
    r = pd.Series(0.001, index=idx); cash = pd.Series(0.0, index=idx)
    lv = levered(r, cash, 2.0, spread=0.0252)
    assert np.allclose(lv, 0.002 - 0.0001)


def test_gated_uses_cash_when_below_trend():
    put, sp, irx = _series()
    d = prepare(put, sp, irx)
    g = gated(d["r_put"], d["sp_level"], d["cash"])
    assert len(g) == len(d["r_put"])
    assert np.isclose(g.iloc[10], d["cash"].iloc[10])                 # before SMA exists → cash


def test_report_structure_and_missing():
    put, sp, irx = _series()
    rep = run_experiment39_report({"PUT": put, "SP500TR": sp, "IRX": irx}, n_trials=10, n_boot=100)
    assert "Experiment #39" in rep and "Sharpe-difference test" in rep
    assert "Equal risk" in rep and "Robustness" in rep and "Summary" in rep
    assert "Missing data" in run_experiment39_report({"PUT": pd.Series(dtype=float)})
