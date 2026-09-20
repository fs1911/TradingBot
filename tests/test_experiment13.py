"""
Tests for experiment #13: RSI(2) parameter-robustness grid.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_13 import rsi2_grid, _summary, run_experiment13_report, GRID
from src.backtest.experiments_12 import rsi2_returns

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def test_rsi2_params_change_behavior():
    rng = np.random.default_rng(0)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 1200)))
    a = rsi2_returns(df, oversold=5, exit_sma=2, use_trend=True)
    b = rsi2_returns(df, oversold=20, exit_sma=10, use_trend=False)
    assert not a.equals(b)                      # parameters actually matter


def test_grid_size_and_summary():
    rng = np.random.default_rng(1)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 1400)))
    rows = rsi2_grid(df, 0.05, 0.08)
    expected = len(GRID["oversold"]) * len(GRID["exit_sma"]) * len(GRID["use_trend"])
    assert len(rows) == expected
    surv, sig, poswf, total = _summary(rows)
    assert 0 <= surv <= total == expected


def test_report_wellformed():
    rng = np.random.default_rng(2)
    data = {s: _df(100 + np.cumsum(rng.normal(0, 1, 1000))) for s in ["SPY", "QQQ"]}
    report = run_experiment13_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        symbols=["SPY", "QQQ"],
    )
    assert "Experiment #13" in report
    assert "parameter robustness" in report.lower()
    assert "Verdict" in report
