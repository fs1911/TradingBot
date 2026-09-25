"""
Tests for experiment #41: hardening multi-asset trend following.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_40 import build_returns
from src.backtest.experiments_41 import (
    make_tsmom, run_with_costs, dry_spells, run_experiment41_report,
)


def _prices(n=2200, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2004-01-01", periods=n)
    t = np.arange(n)
    p = {"EQ": 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n))),
         "UP": 100 * np.exp(0.0006 * t + np.cumsum(rng.normal(0, 0.005, n))),
         "DOWN": 100 * np.exp(-0.0006 * t + np.cumsum(rng.normal(0, 0.005, n)))}
    return {k: pd.Series(v, index=idx) for k, v in p.items()}, pd.Series(2.0, index=idx)


def test_blend_signal_and_long_only_and_cap():
    prices, _ = _prices()
    r = build_returns(prices).iloc[1:]
    cash = pd.Series(0.0001, index=r.index)
    hist, ch = r.iloc[:1500], cash.iloc[:1500]
    w = make_tsmom((63, 126, 252), cap=2.0)(hist, ch, "EQ")
    assert w["UP"] > 0 and w["DOWN"] < 0 and w.abs().sum() <= 2.0 + 1e-9
    lo = make_tsmom((252,), long_only=True)(hist, ch, "EQ")
    assert (lo >= 0).all() and lo.sum() <= 1.0 + 1e-9


def test_placebo_signs_are_random_but_bounded():
    prices, _ = _prices()
    r = build_returns(prices).iloc[1:]
    cash = pd.Series(0.0001, index=r.index)
    rng = np.random.default_rng(0)
    fn = make_tsmom((252,), placebo_rng=rng)
    signs = {tuple(np.sign(fn(r.iloc[:1500], cash.iloc[:1500], "EQ")).values) for _ in range(20)}
    assert len(signs) > 1


def test_borrow_fee_reduces_returns():
    prices, _ = _prices()
    r = build_returns(prices).iloc[1:]
    cash = pd.Series(0.0001, index=r.index)
    fn = make_tsmom((252,))
    a = run_with_costs(r, cash, fn, "EQ", 5.0, 0.0)
    b = run_with_costs(r, cash, fn, "EQ", 5.0, 0.05)
    assert b.sum() < a.sum()


def test_dry_spells_fields():
    idx = pd.bdate_range("2000-01-01", periods=1500)
    rr = pd.Series(np.r_[np.full(500, 0.001), np.full(300, -0.002), np.full(700, 0.001)], index=idx)
    d = dry_spells(rr, pd.Series(0.0, index=idx))
    assert d["under_years"] > 1.0 and d["worst3y"] < 1 and 0 <= d["neg3y"] <= 1


def test_report_structure():
    prices, irx = _prices()
    rep = run_experiment41_report({"t": (prices, "EQ")}, irx, n_trials=10, n_placebo=5, n_boot=50)
    for k in ("Signal horizon", "Costs", "Leverage cap", "Realistic version", "Dry spells", "Placebo", "Summary t"):
        assert k in rep
