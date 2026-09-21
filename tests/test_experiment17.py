"""
Tests for experiment #17: regime-conditional RSI(2) mean reversion.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_17 import regime_rsi2_returns, run_experiment17_report

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def test_regime_gate_changes_exposure():
    rng = np.random.default_rng(0)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 1200)))
    hi = regime_rsi2_returns(df, regime="high")
    lo = regime_rsi2_returns(df, regime="low")
    allr = regime_rsi2_returns(df, regime="all")
    # gating reduces the number of active days vs no gate
    assert (hi != 0).sum() <= (allr != 0).sum()
    assert (lo != 0).sum() <= (allr != 0).sum()
    assert not hi.equals(lo)


def test_causal_length():
    rng = np.random.default_rng(1)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 800)))
    r = regime_rsi2_returns(df, regime="high")
    assert len(r) == 800


def test_report_wellformed():
    rng = np.random.default_rng(2)
    data = {s: _df(100 + np.cumsum(rng.normal(0, 1, 900))) for s in ["SPY", "QQQ"]}
    report = run_experiment17_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        symbols=["SPY", "QQQ"],
    )
    assert "Experiment #17" in report
    assert "highvol" in report and "lowvol" in report
    assert "Summary" in report
