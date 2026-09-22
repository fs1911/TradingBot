"""
Tests for experiment #27: cross-exchange funding differential.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_27 import (
    cross_exchange_spread, run_experiment27_report,
)


def _funding(n=1200, mean=0.0001, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="8h", tz="UTC")
    return pd.Series(rng.normal(mean, 0.00005, n), index=idx)


def _daily(mean=0.0002, n=600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC")
    return pd.Series(rng.normal(mean, 0.0003, n), index=idx)


def test_spread_needs_two_venues():
    assert len(cross_exchange_spread({"a": _daily()})) == 0


def test_spread_positive_when_one_venue_persistently_higher():
    hi = _daily(mean=0.0006, seed=1)     # venue A consistently higher funding
    lo = _daily(mean=0.0001, seed=2)
    spread = cross_exchange_spread({"A": hi, "B": lo})
    assert len(spread) > 100
    assert spread.mean() > 0             # short-hi/long-lo captures the gap
    assert np.isfinite(spread.to_numpy()).all()


def test_report_structure_with_multi_exchange():
    def fetch_multi(sym):
        base = {"BTC/USDT:USDT": 0.0003, "ETH/USDT:USDT": 0.00025}.get(sym)
        if base is None:
            return None
        return {"bybit": _funding(mean=base + 0.0002, seed=1),
                "binance": _funding(mean=base, seed=2),
                "okx": _funding(mean=base - 0.0001, seed=3)}
    report = run_experiment27_report(fetch_multi, ["BTC/USDT:USDT", "ETH/USDT:USDT"])
    assert "Experiment #27" in report
    assert "funding differential" in report.lower()
    assert "avg differential" in report
    assert "Summary" in report
    assert "Combined" in report


def test_report_handles_single_or_no_venue():
    report = run_experiment27_report(lambda s: {"bybit": _funding()}, ["BTC/USDT:USDT"])
    assert "not measurable" in report.lower()

    report2 = run_experiment27_report(lambda s: None, ["BTC/USDT:USDT"])
    assert "not measurable" in report2.lower()
