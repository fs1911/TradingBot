"""
Tests for experiment #19: broad-universe scan.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_19 import run_experiment19_report

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def test_report_covers_all_groups_and_handles_missing():
    rng = np.random.default_rng(0)
    data = {s: _df(100 + np.cumsum(rng.normal(0, 1, 900)))
            for s in ["SPY", "GLD", "FXF", "BTC/USD"]}
    groups = {
        "Indizes": ["SPY", "MISSING1"],
        "Edelmetalle": ["GLD"],
        "Waehrungen": ["FXF"],
        "Krypto": ["BTC/USD"],
    }
    report = run_experiment19_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        groups=groups,
    )
    assert "Experiment #19" in report
    for g in groups:
        assert g in report
    assert "Hurst" in report and "VarRatio" in report
    assert "no data" in report            # MISSING1 handled gracefully
    assert "Summary" in report
    assert "false positives" in report    # honest multiple-testing note
