"""
Tests for experiment #10: parameter-robustness grid and the combined report.
"""
import numpy as np
import pandas as pd

from src.backtest.research import (
    param_grid_robustness, _grid_summary, run_experiment10_report, PARAM_GRID,
)


def _df(closes):
    n = len(closes)
    idx = pd.date_range("2016-01-01", periods=n, freq="1D", tz="UTC")
    c = np.asarray(closes, float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=idx)


def _ou(n, theta=0.1, sigma=0.5, seed=0):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = x[t - 1] - theta * x[t - 1] + sigma * rng.normal()
    return x


def _mean_reverting_pair(n, seed):
    common = 100 + np.cumsum(np.random.default_rng(seed).normal(0, 1, n))
    a = common * np.exp(_ou(n, theta=0.08, sigma=0.05, seed=seed + 50))
    return a, common


def test_grid_covers_all_valid_combos():
    a, b = _mean_reverting_pair(1400, 1)
    rows = param_grid_robustness(_df(a)["close"], _df(b)["close"],
                                 commission_pct=0.05, slippage_pct=0.03, borrow_pct_annual=1.0)
    # all combos have exit < entry (3 z-windows × 3 entries × 3 exits, all valid here)
    expected = len(PARAM_GRID["z_windows"]) * len(PARAM_GRID["entries"]) * len(PARAM_GRID["exits"])
    assert len(rows) == expected
    assert all("oos_mar" in r and "z" in r for r in rows)


def test_grid_summary_on_strong_mean_reversion():
    a, b = _mean_reverting_pair(1600, 2)
    rows = param_grid_robustness(_df(a)["close"], _df(b)["close"],
                                 commission_pct=0.02, slippage_pct=0.02, borrow_pct_annual=0.0)
    good, total, med = _grid_summary(rows)
    assert total > 0 and 0 <= good <= total
    assert isinstance(med, float)


def test_experiment10_report_wellformed():
    n = 1000
    a, b = _mean_reverting_pair(n, 3)
    gld, gdx = _df(a), _df(b)
    uup = _df(100 + np.cumsum(np.random.default_rng(9).normal(0, 0.2, n)))
    data = {"GLD": gld, "GDX": gdx, "UUP": uup, "SLV": gld}
    report = run_experiment10_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        robust_pair=("GLD", "GDX"), usd_pairs=[("GLD", "UUP"), ("SLV", "UUP")],
        limit=n, window=252, step=126,
    )
    assert "Experiment #10" in report
    assert "Part A" in report and "Part B" in report
    assert "parameter robustness" in report.lower()
    assert "UUP" in report
