"""
Tests for experiment #30: valuation gauges (drawdown-from-ATH & 200d MA).
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_30 import (
    drawdown_from_ath, dist_from_ma, _bucket_forward, run_experiment30_report,
)

IDX = lambda n: pd.date_range("2016-01-01", periods=n, freq="1D", tz="UTC")


def test_drawdown_is_nonpositive_and_zero_at_ath():
    p = pd.Series([1, 2, 3, 2, 1, 4], index=IDX(6), dtype=float)
    dd = drawdown_from_ath(p)
    assert (dd <= 1e-12).all()
    assert dd.iloc[0] == 0.0 and dd.iloc[2] == 0.0 and dd.iloc[-1] == 0.0   # new highs
    assert abs(dd.iloc[4] - (1/3 - 1)) < 1e-9                                # 1 vs peak 3


def test_dist_from_ma_sign():
    n = 300
    p = pd.Series(100 + np.arange(n) * 0.5, index=IDX(n), dtype=float)   # steady uptrend
    d = dist_from_ma(p, ma=200).dropna()
    assert (d > 0).all()            # price above its trailing average in an uptrend


def test_bucket_forward_orders_and_shapes():
    n = 900
    rng = np.random.default_rng(0)
    p = pd.Series(100 + np.cumsum(rng.normal(0.05, 1, n)), index=IDX(n))
    b = _bucket_forward(drawdown_from_ath(p), p, horizon=90, n_buckets=5)
    assert not b.empty
    assert list(b.columns) == ["sig_lo", "sig_hi", "fwd", "n"]
    assert b["sig_lo"].iloc[0] <= b["sig_lo"].iloc[-1]     # bucket 0 = lowest signal


def test_bucket_forward_detects_contrarian_drawdown():
    # mean-reverting oscillator: deep drawdowns are followed by recovery (higher fwd)
    n = 1200
    t = np.arange(n)
    p = pd.Series(100 + 30 * np.sin(t / 40.0), index=IDX(n))
    b = _bucket_forward(drawdown_from_ath(p), p, horizon=30, n_buckets=5)
    assert not b.empty
    assert b["fwd"].iloc[0] > b["fwd"].iloc[-1]            # deepest DD → highest fwd


def test_report_structure_and_bands():
    def fetch(sym):
        n = 1400
        t = np.arange(n)
        base = 100 + 30 * np.sin(t / 45.0) + t * 0.02
        return pd.Series(base, index=IDX(n))
    report = run_experiment30_report(fetch, ["BTC/USD", "SPY"], horizon=90)
    assert "Experiment #30" in report
    assert "Drawdown from ATH" in report
    assert "Distance from 200d MA" in report
    assert "Finanzradar bands" in report
    assert "Kaufen" in report and "Überhitzt" in report
    assert "Summary" in report


def test_report_handles_no_data():
    report = run_experiment30_report(lambda s: None, ["X"], horizon=90)
    assert "no data" in report
