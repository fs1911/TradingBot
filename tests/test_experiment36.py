"""
Tests for experiment #36: calendar anomalies before/after publication.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_36 import (
    tom_mask, monday_mask, january_mask, halloween_mask, preholiday_mask,
    welch, p_two_sided, compare, window_strategy, run_experiment36_report,
)


def test_tom_mask_marks_last_and_first_three():
    idx = pd.bdate_range("2020-01-01", "2020-02-29")
    m = tom_mask(idx)
    jan = m[idx.month == 1]
    assert jan.iloc[:3].all() and not jan.iloc[3] and jan.iloc[-1]
    assert m.sum() == 8                      # 4 per month (3 first + last) × 2


def test_simple_masks():
    idx = pd.bdate_range("2021-01-01", "2021-12-31")
    assert monday_mask(idx).sum() == (idx.weekday == 0).sum()
    assert january_mask(idx).sum() == (idx.month == 1).sum()
    assert halloween_mask(idx)[idx.month == 6].sum() == 0


def test_preholiday_detects_midweek_closure_not_weekends():
    idx = pd.bdate_range("2021-06-28", "2021-07-09").drop(pd.Timestamp("2021-07-05"))
    m = preholiday_mask(idx)
    assert m.loc["2021-07-02"]               # Friday before Monday holiday (gap 4)
    assert not m.loc["2021-07-09"]           # last day: unknown
    assert not m.loc["2021-06-30"]           # normal day
    assert m.sum() == 1


def test_welch_and_p():
    rng = np.random.default_rng(0)
    a, b = rng.normal(1, 1, 500), rng.normal(0, 1, 500)
    assert welch(a, b) > 5
    assert p_two_sided(0.0) == 1.0 and p_two_sided(4.0) < 1e-4


def test_compare_and_strategy_detect_planted_tom_effect():
    idx = pd.bdate_range("1950-01-01", periods=8000)
    rng = np.random.default_rng(1)
    m = tom_mask(idx)
    r = pd.Series(rng.normal(0, 0.01, len(idx)), index=idx) + m.astype(float) * 0.002
    c = compare(r, m)
    assert c["t"] > 5 and c["in_bp"] > c["out_bp"]
    s = window_strategy(r, m, cost_bps=0.0)
    assert (s[~m] == 0).all()


def test_report_structure_and_missing():
    idx = pd.bdate_range("1928-01-02", periods=24000)
    rng = np.random.default_rng(2)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, len(idx)))), index=idx)
    rep = run_experiment36_report(close, n_trials=10)
    assert "Experiment #36" in rep and "BEFORE" in rep and "AFTER" in rep
    for k in ("turn-of-month", "monday", "january", "pre-holiday", "halloween"):
        assert k in rep
    assert "Summary" in rep
    assert "Missing data" in run_experiment36_report(pd.Series(dtype=float))
