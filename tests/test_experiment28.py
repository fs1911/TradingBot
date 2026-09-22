"""
Tests for experiment #28: dated-futures calendar basis carry & signal.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_28 import (
    annualized_basis, basis_carry_returns, basis_signal_forward_returns,
    run_experiment28_report,
)

IDX = lambda n: pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC")


def test_annualized_basis_math():
    # 2% premium with 90 days to expiry → ~8.11%/yr
    assert abs(annualized_basis(100.0, 102.0, 90) - 0.02 * (365 / 90)) < 1e-9
    assert np.isnan(annualized_basis(100.0, 102.0, 0))     # guard
    assert np.isnan(annualized_basis(0.0, 102.0, 90))


def test_basis_carry_captures_convergence_positive_in_contango():
    n = 400
    rng = np.random.default_rng(0)
    spot = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=IDX(n))
    # future starts 3% above spot and converges linearly to spot by the end
    premium = np.linspace(0.03, 0.0, n)
    future = spot * (1 + premium)
    carry = basis_carry_returns(spot, future, rolls_per_year=4, roll_cost_bps=0.0)
    assert len(carry) == len(spot.align(future, join="inner")[0])
    assert carry.sum() > 0                       # converging contango pays the carry

def test_roll_cost_reduces_carry():
    n = 400
    spot = pd.Series(100.0 + np.arange(n) * 0.01, index=IDX(n))
    future = spot * 1.01
    cheap = basis_carry_returns(spot, future, roll_cost_bps=0.0).sum()
    dear = basis_carry_returns(spot, future, roll_cost_bps=100.0).sum()
    assert dear < cheap


def test_signal_forward_returns_detects_contrarian_basis():
    n = 500
    rng = np.random.default_rng(1)
    # construct: high basis is followed by lower forward returns
    spot = pd.Series(100 + np.cumsum(rng.normal(0.05, 1, n)), index=IDX(n))
    fwd = spot.shift(-30) / spot - 1.0
    basis = (-fwd).fillna(0.0) + rng.normal(0, 0.01, n)   # basis ~ -forward return
    tbl = basis_signal_forward_returns(spot, pd.Series(basis, index=IDX(n)), horizon=30)
    assert not tbl.empty
    # highest-basis bucket should show lower forward return than lowest-basis bucket
    assert tbl["fwd_ret"].iloc[-1] < tbl["fwd_ret"].iloc[0]


def test_report_no_data_path_mentions_funding_fallback():
    report = run_experiment28_report(lambda s: None, ["BTC/USDT:USDT"])
    assert "Experiment #28" in report
    assert "no dated-futures data" in report
    assert "#29" in report                        # honest fallback proposal


def test_report_with_injected_data():
    def fetch_basis(sym):
        n = 420
        rng = np.random.default_rng(abs(hash(sym)) % 1000)
        spot = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=IDX(n))
        future = spot * (1 + np.linspace(0.03, 0.0, n))
        ann_basis = pd.Series(np.linspace(0.12, 0.0, n), index=IDX(n))
        return spot, future, ann_basis
    report = run_experiment28_report(fetch_basis, ["BTC/USDT:USDT", "ETH/USDT:USDT"])
    assert "Carry (the delta-neutral trade)" in report
    assert "Finanzradar signal" in report
    assert "Summary" in report
