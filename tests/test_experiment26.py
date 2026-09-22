"""
Tests for experiment #26: broader / cross-sectional structural carry.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_26 import (
    build_carry_panel, equal_weight_carry, carry_weighted,
    cross_sectional_spread, run_experiment26_report,
)


def _funding(n_intervals=1200, mean=0.0001, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n_intervals, freq="8h", tz="UTC")
    return pd.Series(rng.normal(mean, 0.00005, n_intervals), index=idx)


def _universe(means, seed0=0):
    """One funding series per coin, each with its own mean funding level."""
    return {f"C{i}/USDT:USDT": _funding(mean=m, seed=seed0 + i)
            for i, m in enumerate(means)}


def test_build_panel_filters_short_history():
    data = {"A/USDT:USDT": _funding(1200, seed=1),
            "B/USDT:USDT": _funding(1200, seed=2),
            "C/USDT:USDT": _funding(1200, seed=3),
            "SHORT/USDT:USDT": _funding(60, seed=4)}          # too short
    panel = build_carry_panel(lambda s: data.get(s), list(data))
    assert "SHORT/USDT:USDT" not in panel.columns
    assert panel.shape[1] == 3


def test_equal_weight_is_row_mean():
    data = _universe([0.0001, 0.0002, 0.00005], seed0=10)
    panel = build_carry_panel(lambda s: data.get(s), list(data))
    eq = equal_weight_carry(panel)
    assert np.allclose(eq.to_numpy(), panel.mean(axis=1).dropna().to_numpy())


def test_carry_weighted_tilts_toward_high_funding_coin():
    # coin 1 has much higher funding → carry-weighted mean should exceed equal-weight
    data = _universe([0.00002, 0.0004, 0.00002], seed0=20)
    panel = build_carry_panel(lambda s: data.get(s), list(data))
    eq = equal_weight_carry(panel).mean()
    cw = carry_weighted(panel).mean()
    assert cw > eq


def test_cross_sectional_spread_is_causal_and_finite():
    data = _universe([0.00002, 0.0004, 0.00002, 0.0003, 0.00001], seed0=30)
    panel = build_carry_panel(lambda s: data.get(s), list(data))
    spread = cross_sectional_spread(panel)
    assert len(spread) > 100
    assert np.isfinite(spread.to_numpy()).all()
    # high-funding half minus low-funding half is positive on average when the
    # ranking (trailing funding) genuinely separates coins
    assert spread.mean() > 0


def test_report_structure():
    data = _universe([0.0001, 0.0002, 0.00005, 0.0003], seed0=40)
    report = run_experiment26_report(lambda s: data.get(s), list(data))
    assert "Experiment #26" in report
    assert "Broad basket" in report
    assert "Carry-weighted" in report
    assert "Cross-sectional spread" in report
    assert "Summary" in report


def test_report_handles_no_data():
    report = run_experiment26_report(lambda s: None, ["X/USDT:USDT"])
    assert "Insufficient funding data" in report
