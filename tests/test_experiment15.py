"""
Tests for experiment #15: walk-forward machine-learning prediction.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_15 import (
    build_features, _fit_logreg, ml_returns, run_experiment15_report, FEATURES,
)

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def test_features_built_without_lookahead():
    rng = np.random.default_rng(0)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 400)))
    feat = build_features(df)
    for f in FEATURES:
        assert f in feat.columns
    assert "fwd" in feat.columns
    # fwd is the NEXT day's return: fwd[t] == r1[t+1]
    r1 = feat["r1"].to_numpy()
    fwd = feat["fwd"].to_numpy()
    assert np.allclose(fwd[10], r1[11], equal_nan=True)


def test_logreg_learns_separable_data():
    rng = np.random.default_rng(1)
    X = rng.normal(0, 1, (400, 2))
    y = (X[:, 0] + X[:, 1] > 0).astype(float)      # linearly separable
    Xb = np.column_stack([np.ones(400), X])
    w = _fit_logreg(Xb, y)
    p = 1 / (1 + np.exp(-(Xb @ w)))
    acc = ((p > 0.5) == y).mean()
    assert acc > 0.9                                # should fit separable data well


def test_ml_returns_causal_runs():
    rng = np.random.default_rng(2)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 1200)))
    ret, weights = ml_returns(df)
    assert isinstance(ret, pd.Series) and len(ret) > 0
    assert set(weights.keys()) <= set(FEATURES)


def test_report_wellformed():
    rng = np.random.default_rng(3)
    data = {s: _df(100 + np.cumsum(rng.normal(0, 1, 1000))) for s in ["SPY", "QQQ"]}
    report = run_experiment15_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        symbols=["SPY", "QQQ"],
    )
    assert "Experiment #15" in report
    assert "logistic regression" in report.lower()
    assert "feature weights" in report.lower()
    assert "Summary" in report
