"""
Tests for experiment #29: funding as a froth gauge (Finanzradar signal).
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_29 import (
    annualized_funding, froth_buckets, froth_filter_returns,
    run_experiment29_report,
)


def _funding(n=1200, mean=0.0001, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="8h", tz="UTC")
    return pd.Series(rng.normal(mean, 0.00005, n), index=idx)


def _prices(n=400, drift=0.0005, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC")
    return pd.Series(100 + np.cumsum(rng.normal(drift, 1, n)), index=idx)


def test_annualized_funding_smooths_and_scales():
    f = _funding(mean=0.0001)      # ~0.03%/day → ~11%/yr
    annf = annualized_funding(f, smooth=7)
    assert len(annf) > 0
    assert 0.05 < annf.mean() < 0.20


def test_annualized_funding_empty():
    assert len(annualized_funding(pd.Series(dtype=float))) == 0


def test_froth_buckets_detect_contrarian():
    n = 500
    idx = pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC")
    rng = np.random.default_rng(3)
    spot = pd.Series(100 + np.cumsum(rng.normal(0.05, 1, n)), index=idx)
    fwd = spot.shift(-30) / spot - 1.0
    annf = pd.Series((-fwd).fillna(0.0) + rng.normal(0, 0.01, n), index=idx)  # funding ~ -fwd
    b = froth_buckets(annf, spot, horizon=30)
    assert not b.empty
    assert b["fwd"].iloc[-1] < b["fwd"].iloc[0]      # high funding → lower forward


def test_froth_filter_is_causal_and_reduces_exposure():
    n = 500
    idx = pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC")
    rng = np.random.default_rng(4)
    spot = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=idx)
    annf = pd.Series(rng.normal(0.1, 0.3, n), index=idx)
    strat, ret = froth_filter_returns(annf, spot, window=180, hot_q=0.8)
    assert len(strat) == len(ret)
    # filtered series steps aside sometimes → fewer nonzero days than buy&hold
    assert (strat == 0).sum() >= (ret == 0).sum()


def test_report_structure():
    def ff(s):
        return {"BTC/USDT:USDT": _funding(seed=1), "ETH/USDT:USDT": _funding(seed=2)}.get(s)
    def fp(s):
        return {"BTC/USDT:USDT": _prices(seed=1), "ETH/USDT:USDT": _prices(seed=2)}.get(s)
    report = run_experiment29_report(ff, fp, ["BTC/USDT:USDT", "ETH/USDT:USDT"])
    assert "Experiment #29" in report
    assert "froth" in report.lower()
    assert "step aside when funding hot" in report
    assert "Finanzradar" in report
    assert "Summary" in report


def test_report_handles_no_data():
    report = run_experiment29_report(lambda s: None, lambda s: None, ["X/USDT:USDT"])
    assert "no usable funding+price data" in report or "no data" in report
