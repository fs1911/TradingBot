"""
Tests for experiment #33: trend filter with cash yield, robustness, savings plans.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_33 import (
    cash_daily_returns, trend_position, filter_returns_with_cash, savings_plans,
    run_experiment33_report,
)

IDX = lambda n: pd.bdate_range("1990-01-01", periods=n)


def _boom_bust(n_up=1500, n_down=400, n_rec=800):
    up = np.linspace(100, 300, n_up)
    down = np.linspace(300, 120, n_down)
    rec = np.linspace(120, 400, n_rec)
    return pd.Series(np.concatenate([up, down, rec]), index=IDX(n_up + n_down + n_rec))


def test_cash_daily_returns_scaling_and_ffill():
    idx = IDX(5)
    irx = pd.Series([5.0, np.nan, 5.0], index=idx[[0, 2, 4]])
    c = cash_daily_returns(irx, idx)
    assert np.allclose(c.to_numpy(), 0.05 / 252)
    assert (cash_daily_returns(pd.Series(dtype=float), idx) == 0).all()


def test_trend_position_causal_and_monthly_holds():
    px = _boom_bust()
    d = trend_position(px, 200)
    m = trend_position(px, 200, monthly=True)
    assert d.iloc[:200].eq(0).all()            # no position before SMA exists
    # monthly signal changes at most once per month
    changes = m.diff().abs()
    months = pd.Series(px.index.to_period("M"), index=px.index)
    per_month = changes.groupby(months.to_numpy()).sum()
    assert (per_month <= 1).all()


def test_cash_yield_helps_filter_in_crash():
    px = _boom_bust()
    zero = filter_returns_with_cash(px, pd.Series(0.0, index=px.index))
    paid = filter_returns_with_cash(px, pd.Series(0.04 / 252, index=px.index))
    assert paid.sum() > zero.sum()             # earning interest while out helps


def test_savings_plans_shapes_and_full_protects_in_crash():
    px = _boom_bust()
    sp = savings_plans(px, pd.Series(0.03 / 252, index=px.index))
    assert set(sp) == {"plain", "light", "full"}
    for mult, dd in sp.values():
        assert np.isfinite(mult) and dd <= 0
    assert sp["full"][1] > sp["plain"][1]      # smaller drawdown for the full switch


def test_report_structure_and_no_data():
    px = _boom_bust()
    irx = pd.Series(4.0, index=px.index)
    assets = [{"name": "Idx", "stooq": "", "yahoo": "X"},
              {"name": "Nope", "stooq": "", "yahoo": "Y"}]
    fetch = lambda a: (px, "yahoo") if a["name"] == "Idx" else (pd.Series(dtype=float), "none")
    rep = run_experiment33_report(fetch, assets, irx, n_trials=10)
    assert "Experiment #33" in rep
    assert "SMA200 monthly" in rep and "trend-DCA full" in rep
    assert "no data" in rep
    assert "Summary timing" in rep and "Summary savings plans" in rep
