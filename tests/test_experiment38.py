"""
Tests for experiment #38: PutWrite + trend filter combinations.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_38 import (
    build_strategies, monthly_shape, crisis_return, run_experiment38_report,
)


def _series(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("1996-06-01", periods=n)
    sp = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n)))
    # put-write: lower beta, small premium, occasional big loss
    put_r = 0.5 * np.diff(np.log(sp), prepend=np.log(sp[0])) + 0.0001
    put_r[rng.random(n) < 0.002] -= 0.05
    put = 100 * np.exp(np.cumsum(put_r))
    return (pd.Series(put, index=idx), pd.Series(sp, index=idx),
            pd.Series(3.0, index=idx))


def test_build_strategies_columns_and_mixes():
    put, sp, irx = _series()
    df = build_strategies(put, sp, irx)
    assert "50/50 PutWrite + trend-S&P" in df.columns and len(df) == len(put) - 200
    mix = 0.5 * df["PutWrite"] + 0.5 * df["S&P 500 TR"]
    assert np.allclose(mix, df["50/50 PutWrite + S&P"])
    # filtered PutWrite earns cash (not PutWrite) on out-of-market days
    diff = (df["PutWrite + trend (daily)"] - df["PutWrite"]).abs()
    assert (diff > 1e-12).any()


def test_monthly_shape_and_crisis_return():
    idx = pd.bdate_range("2008-01-01", periods=300)
    r = pd.Series(0.001, index=idx)
    r.iloc[100] = -0.2
    sk, worst, when = monthly_shape(r)
    assert worst < -0.15 and sk < 0
    assert abs(crisis_return(r, "2008-01-01", "2008-01-31") - ((1.001 ** len(r.loc['2008-01'])) - 1)) < 1e-9


def test_report_structure_and_missing():
    put, sp, irx = _series()
    rep = run_experiment38_report({"PUT": put, "SP500TR": sp, "IRX": irx}, n_trials=10)
    assert "Experiment #38" in rep and "## Overall" in rep and "## Crises" in rep
    assert "Rigor on the key differentials" in rep and "Summary" in rep
    assert "Missing data" in run_experiment38_report({"PUT": pd.Series(dtype=float)})
