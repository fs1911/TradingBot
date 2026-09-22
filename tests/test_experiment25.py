"""
Tests for experiment #25: funding carry net of realistic costs.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_25 import (
    net_carry_model, run_experiment25_report, FEE_TIERS,
)


def _funding(n_intervals=1200, mean=0.0001, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n_intervals, freq="8h", tz="UTC")
    return pd.Series(rng.normal(mean, 0.00005, n_intervals), index=idx)


def _daily(mean_daily=0.0003, n=800, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC")
    return pd.Series(rng.normal(mean_daily, 0.0005, n), index=idx)


def test_net_model_subtracts_costs_from_gross():
    d = _daily()
    m = net_carry_model(d, spot_vol_annual=0.6, rotation_days=30, fee=FEE_TIERS["taker"])
    assert m["net_ann"] < m["gross_ann"]              # costs reduce gross
    assert m["exec_drag"] > 0 and m["rehedge_drag"] > 0


def test_more_frequent_rotation_costs_more():
    d = _daily()
    fast = net_carry_model(d, 0.6, rotation_days=7, fee=FEE_TIERS["taker"])
    slow = net_carry_model(d, 0.6, rotation_days=90, fee=FEE_TIERS["taker"])
    assert fast["exec_drag"] > slow["exec_drag"]
    assert fast["net_ann"] < slow["net_ann"]


def test_maker_cheaper_than_taker():
    d = _daily()
    taker = net_carry_model(d, 0.6, 30, FEE_TIERS["taker"])
    maker = net_carry_model(d, 0.6, 30, FEE_TIERS["maker"])
    assert maker["net_ann"] > taker["net_ann"]


def test_insufficient_data_flag():
    assert net_carry_model(pd.Series([0.001, 0.002]), 0.6, 30, 0.0005).get("insufficient")


def test_report_structure_and_capital_column():
    data = {"BTC/USDT:USDT": _funding(seed=1), "ETH/USDT:USDT": _funding(seed=2)}
    report = run_experiment25_report(
        fetch_funding=lambda s: data.get(s),
        symbols=list(data), target_annual=3650.0,
    )
    assert "Experiment #25" in report
    assert "net of realistic costs" in report.lower()
    assert "Capital for target" in report
    assert "taker" in report and "maker" in report
    assert "Summary" in report


def test_report_handles_no_data():
    report = run_experiment25_report(fetch_funding=lambda s: None, symbols=["X"])
    assert "Insufficient funding data" in report
