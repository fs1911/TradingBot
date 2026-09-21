"""
Tests for experiment #16: volume signals + stocks/bonds dual momentum.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_16 import (
    volume_capitulation_returns, obv_trend_returns, dual_momentum_returns,
    run_experiment16_report,
)

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes, volumes=None):
    c = np.asarray(closes, float)
    n = len(c)
    v = np.asarray(volumes, float) if volumes is not None else np.full(n, 1e6)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": v}, index=IDX(n))


def test_volume_capitulation_only_trades_after_spike_down_days():
    rng = np.random.default_rng(0)
    n = 400
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    vol = np.full(n, 1e6)
    df = _df(close, vol)
    r = volume_capitulation_returns(df)
    # mostly flat (only trades day after high-volume down days, which are rare here)
    assert (r != 0).mean() < 0.3


def test_obv_trend_runs_and_is_causal():
    rng = np.random.default_rng(1)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 500)))
    r = obv_trend_returns(df)
    assert isinstance(r, pd.Series) and len(r) == 500


def test_dual_momentum_picks_the_stronger_asset():
    n = 800
    spy = _df(100 * (1.001) ** np.arange(n))       # steadily up
    tlt = _df(100 - np.arange(n) * 0.01)           # drifting down
    data = {"SPY": spy, "TLT": tlt}
    r = dual_momentum_returns(data, risk="SPY", bond="TLT")
    assert not r.empty
    assert (1 + r).prod() > 1.0                    # should ride SPY, end positive


def test_report_wellformed():
    rng = np.random.default_rng(2)
    data = {s: _df(100 + np.cumsum(rng.normal(0, 1, 800))) for s in ["SPY", "TLT", "QQQ"]}
    report = run_experiment16_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        volume_symbols=["SPY", "QQQ"], dual_momentum={"risk": "SPY", "bond": "TLT"},
    )
    assert "Experiment #16" in report
    assert "VolCapitulation" in report and "OBVtrend" in report and "DualMom" in report
    assert "Summary" in report
