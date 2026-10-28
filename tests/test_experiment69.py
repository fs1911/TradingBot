import numpy as np
import pandas as pd

from src.backtest.experiments_69 import daily_inputs, leveraged, monthly_rebalanced, stats, kelly, run_experiment69_report


def _data(years=60, mu=0.0004, sd=0.011, seed=0):
    d = pd.bdate_range("1950-01-02", periods=years * 252)
    rng = np.random.default_rng(seed)
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(mu, sd, len(d)))), index=d)
    irx = pd.Series(3.0, index=d)
    return px, irx


def test_leverage_math():
    px, irx = _data()
    d = daily_inputs(px, irx, None)
    assert abs(d["cash"].iloc[-1] - 0.03 / 252) < 1e-12
    r2 = leveraged(d, 2)
    assert np.allclose(r2, 2 * d["r"] - (d["cash"] + 0.005 / 252) - 0.009 / 252)
    m2 = monthly_rebalanced(d, 2.0)
    first = d.index.to_period("M") != d.index.to_period("M").shift(1) if False else None
    assert abs(m2.iloc[0] - (2 * d["r"].iloc[0] - (d["cash"].iloc[0] + 0.005 / 252))) < 1e-12
    assert np.allclose(monthly_rebalanced(d, 1.0), d["r"])


def test_volatility_drag_and_report():
    px, irx = _data(mu=0.0002, sd=0.02)          # high vol, low drift → 3× loses to 1×
    d = daily_inputs(px, irx, None)
    assert stats(leveraged(d, 3))["cagr"] < stats(leveraged(d, 1))["cagr"]
    m = (1 + d["r"]).groupby(d.index.to_period("M")).prod() - 1
    k = kelly(m, pd.Series(0.0025, index=m.index))
    assert len(k) > 100
    rep = run_experiment69_report(px, irx, None)
    assert "Daily leverage" in rep and "Kelly" in rep and "2× monthly reset" in rep
