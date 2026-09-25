"""
Tests for experiment #40: multi-asset trend following.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_40 import (
    build_returns, month_end_positions, w_equal, w_faber, w_tsmom_ls, w_tsmom_lo,
    run_strategy, run_experiment40_report,
)


def _prices(n=2600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2004-01-01", periods=n)
    t = np.arange(n)
    out = {
        "EQ": 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n))),
        "UP": 100 * np.exp(0.0006 * t + np.cumsum(rng.normal(0, 0.005, n))),     # steady uptrend
        "DOWN": 100 * np.exp(-0.0006 * t + np.cumsum(rng.normal(0, 0.005, n))),  # steady downtrend
        "LATE": 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n))),
    }
    prices = {k: pd.Series(v, index=idx) for k, v in out.items()}
    prices["LATE"] = prices["LATE"].iloc[800:]                                      # starts later
    return prices, pd.Series(2.0, index=idx)


def test_build_returns_and_month_ends():
    prices, _ = _prices()
    r = build_returns(prices)
    assert set(r.columns) == {"EQ", "UP", "DOWN", "LATE"}
    assert r["LATE"].iloc[:790].isna().all()
    mes = month_end_positions(r.index)
    assert len(mes) > 100 and r.index[mes[0]].month != r.index[mes[0] + 1].month


def test_weight_rules_directions():
    prices, irx = _prices()
    r = build_returns(prices).iloc[1:]
    cash = pd.Series(0.0001, index=r.index)
    hist = r.iloc[:1500]
    ew = w_equal(hist, cash.iloc[:1500], "EQ")
    assert abs(ew.sum() - 1.0) < 1e-9 and "LATE" in ew.index
    fb = w_faber(hist, cash.iloc[:1500], "EQ")
    assert fb["UP"] > 0 and fb["DOWN"] == 0
    ls = w_tsmom_ls(hist, cash.iloc[:1500], "EQ")
    assert ls["UP"] > 0 and ls["DOWN"] < 0 and ls.abs().sum() <= 3.0 + 1e-9
    lo = w_tsmom_lo(hist, cash.iloc[:1500], "EQ")
    assert (lo >= 0).all() and lo.sum() <= 1.0 + 1e-9 and lo["DOWN"] == 0


def test_run_strategy_is_causal_and_finite():
    prices, _ = _prices()
    r = build_returns(prices).iloc[1:]
    cash = pd.Series(0.0001, index=r.index)
    out, gross = run_strategy(r, cash, w_tsmom_ls, "EQ")
    assert np.isfinite(out.to_numpy()).all() and gross > 0
    # before any weights exist the strategy earns cash only
    assert np.allclose(out.iloc[:20], 0.0001)


def test_report_structure():
    prices, irx = _prices()
    rep = run_experiment40_report({"test": (prices, "EQ"),
                                   "empty": ({"X": pd.Series(dtype=float)}, "X")},
                                  irx, n_trials=10, n_boot=100)
    assert "Experiment #40" in rep and "Universe: test" in rep
    assert "TSMOM long/short" in rep and "Faber GTAA" in rep and "60/40" in rep
    assert "before 2013" in rep and "No usable data" in rep
