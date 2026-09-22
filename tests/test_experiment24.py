"""
Tests for experiment #24: crypto funding-rate carry.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_24 import (
    funding_to_daily_carry, carry_stats, run_experiment24_report,
)


def _funding_series(n_intervals=900, per_day=3, mean=0.0001, neg_patch=0.0, seed=0):
    """Synthetic 8h funding: mostly positive drip, optional negative patch."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2022-01-01", tz="UTC")
    idx = pd.date_range(start, periods=n_intervals, freq="8h")
    vals = rng.normal(mean, 0.00005, n_intervals)
    if neg_patch:
        k = int(n_intervals * neg_patch)
        vals[100:100 + k] = -abs(rng.normal(0.0003, 0.0001, k))  # bear flip
    return pd.Series(vals, index=idx)


def test_daily_carry_sums_intervals_per_day():
    f = _funding_series(n_intervals=9, per_day=3)   # 3 days x 3 intervals
    daily = funding_to_daily_carry(f)
    assert len(daily) == 3
    assert np.isclose(daily.iloc[0], f.iloc[0:3].sum())


def test_daily_carry_handles_empty():
    assert len(funding_to_daily_carry(pd.Series(dtype=float))) == 0
    assert len(funding_to_daily_carry(None)) == 0


def test_carry_stats_reports_negative_fraction_and_drawdown():
    f = _funding_series(n_intervals=900, neg_patch=0.1, seed=1)
    daily = funding_to_daily_carry(f)
    st = carry_stats(f, daily)
    assert st["pct_negative"] > 0          # the bear patch shows up
    assert st["max_drawdown_pct"] <= 0     # drawdown is non-positive
    assert st["days"] == len(daily)


def test_report_structure_and_disclaimers():
    data = {
        "BTC/USDT:USDT": _funding_series(seed=1),
        "ETH/USDT:USDT": _funding_series(seed=2),
        "SOL/USDT:USDT": _funding_series(seed=3, neg_patch=0.15),
    }
    report = run_experiment24_report(
        fetch_funding=lambda s: data.get(s),
        symbols=list(data) + ["MISSING/USDT:USDT"],
    )
    assert "Experiment #24" in report
    assert "funding-rate carry" in report.lower()
    assert "NOT risk-free" in report                # honesty disclaimer present
    assert "not executable on Alpaca" in report or "not executable" in report.lower() \
        or "NOT tradeable on Alpaca" in report
    assert "Diversified basket" in report
    assert "no/short data" in report                # missing symbol handled
    assert "Summary" in report


def test_report_handles_all_missing():
    report = run_experiment24_report(fetch_funding=lambda s: None,
                                     symbols=["X/USDT:USDT"])
    assert "Experiment #24" in report
    assert "no/short data" in report
