"""
Tests for experiment #35: trend filter on monthly averages vs true month-end closes.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_35 import (
    month_end_closes, build_panel, real_returns, lag1_autocorr, run_experiment35_report,
)


def _daily(n_years=40, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("1928-01-02", periods=252 * n_years)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, len(idx)))), index=idx)


def _shiller_from_daily(daily):
    avg = daily.groupby(daily.index.to_period("M")).mean()
    idx = avg.index.to_timestamp()
    n = len(avg)
    return pd.DataFrame({"price": avg.to_numpy(), "div": avg.to_numpy() * 0.04,
                         "cpi": 10 * 1.002 ** np.arange(n), "gs10": np.full(n, 4.0),
                         "cape": np.full(n, 15.0)}, index=idx)


def test_month_end_closes_takes_last_day():
    idx = pd.to_datetime(["2020-01-02", "2020-01-31", "2020-02-03", "2020-02-28"])
    s = month_end_closes(pd.Series([1.0, 2.0, 3.0, 4.0], index=idx))
    assert list(s.values) == [2.0, 4.0]
    assert str(s.index[0]) == "2020-01"


def test_averaging_creates_autocorrelation():
    d = _daily()
    rr = real_returns(build_panel(_shiller_from_daily(d), d))
    # random-walk daily data: month-end returns ~uncorrelated, averages clearly positive
    assert lag1_autocorr(rr["stock_avg"]) > lag1_autocorr(rr["stock_me"]) + 0.1


def test_real_returns_columns_and_cash_is_minus_inflation():
    d = _daily(5)
    rr = real_returns(build_panel(_shiller_from_daily(d), d))
    assert {"stock_avg", "stock_me", "bond", "cash0"} <= set(rr.columns)
    assert abs(rr["cash0"].dropna().iloc[0] - (1 / 1.002 - 1)) < 1e-9


def test_report_structure_and_missing_data():
    d = _daily()
    rep = run_experiment35_report(_shiller_from_daily(d), d, n_trials=10)
    assert "Experiment #35" in rep and "The artefact, measured" in rep
    assert "B · trend filter (month-end, bonds)" in rep and "by era" in rep
    assert "Summary" in rep
    assert "Missing data" in run_experiment35_report(pd.DataFrame(), pd.Series(dtype=float))
