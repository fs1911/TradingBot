import numpy as np
import pandas as pd

from src.backtest.experiments_99 import buffett_monthly, relative, timing, run_experiment99_report


def _shiller(seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1945-01-01", "2023-12-01", freq="MS")
    price = 20 * np.exp(np.cumsum(rng.normal(0.005, 0.04, len(idx))))
    return pd.DataFrame({"price": price, "div": price * 0.03, "cpi": 20 * np.exp(np.arange(len(idx)) * 0.003),
                         "gs10": 4 + rng.normal(0, 0.1, len(idx)), "cape": 10 + rng.random(len(idx)) * 20}, index=idx)


def _q(seed=1):
    rng = np.random.default_rng(seed)
    q = pd.date_range("1945-01-01", "2026-07-01", freq="QS")
    gdp = pd.Series(200 * np.exp(np.arange(len(q)) * 0.015), index=q)
    eq = gdp * 1000 * (0.6 + 0.4 * np.sin(np.arange(len(q)) / 15) + rng.normal(0, 0.02, len(q)))
    return eq, gdp


def test_buffett_monthly_lag_and_value():
    q = pd.to_datetime(["2020-01-01", "2020-04-01"])
    eq, gdp = pd.Series([2_000_000.0, 3_000_000.0], index=q), pd.Series([1000.0, 1000.0], index=q)
    bi = buffett_monthly(eq, gdp)
    # Q1 2020 (ends March) is usable from June 2020; value 200 %
    assert bi.index[0] == pd.Period("2020-06", "M") and abs(bi.iloc[0] - 200) < 1e-9
    assert abs(bi[pd.Period("2020-09", "M")] - 300) < 1e-9


def test_timing_uses_past_only():
    idx = pd.period_range("1950-01", periods=400, freq="M")
    s = pd.Series(0.01, index=idx)
    b = pd.Series(0.0, index=idx)
    sig = pd.Series(np.arange(400, dtype=float), index=idx)   # always a new high → 50 % from month 121
    r, d = timing(s, b, sig)
    assert (d["w"] == 0.5).all() and np.allclose(r, 0.005)


def test_report_runs():
    eq, gdp = _q()
    rep = run_experiment99_report(_shiller(), eq, gdp)
    assert "Latest" in rep and "T1 Buffett indicator" in rep and "CAPE" in rep
    assert relative(pd.Series(np.ones(300))).dropna().eq(1).all()
