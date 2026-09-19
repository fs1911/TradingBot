"""
Tests for the pairs stat-arb stress test: borrow cost drag, within-group pair
selection, and a well-formed stress report.
"""
import numpy as np
import pandas as pd

from src.backtest.quant_research import (
    backtest_pair, find_pairs_grouped, run_pairs_stress_report, COST_SCENARIOS,
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


def _coint_pair(n, seed):
    rng = np.random.default_rng(seed)
    common = 100 + np.cumsum(rng.normal(0, 1, n))
    return common + _ou(n, seed=seed + 100), common


def test_borrow_cost_reduces_return():
    a, b = _coint_pair(1500, 1)
    no_borrow = backtest_pair(_df(a)["close"], _df(b)["close"], borrow_pct_annual=0.0)
    with_borrow = backtest_pair(_df(a)["close"], _df(b)["close"], borrow_pct_annual=10.0)
    assert (1 + with_borrow).prod() < (1 + no_borrow).prod()   # borrow drag lowers return


def test_grouped_pairs_only_within_group():
    n = 900
    a1, b1 = _coint_pair(n, 2)
    data = {
        "SPY": _df(a1), "QQQ": _df(b1),          # both in 'index'
        "BTC/USD": _df(100 + np.cumsum(np.random.default_rng(9).normal(0, 2, n))),  # 'crypto' alone
    }
    groups = {"index": ["SPY", "QQQ"], "crypto": ["BTC/USD"]}
    pairs = find_pairs_grouped(data, groups)
    # only SPY/QQQ possible (BTC is alone in its group → no cross-domain pair)
    for a, b, _ in pairs:
        assert {a, b} == {"SPY", "QQQ"}


def test_stress_report_wellformed():
    n = 1000
    data = {}
    # two cointegrated index pairs + a couple of extras
    a1, b1 = _coint_pair(n, 3)
    a2, b2 = _coint_pair(n, 4)
    data["SPY"], data["XLY"] = _df(a1), _df(b1)
    data["QQQ"], data["XLK"] = _df(a2), _df(b2)
    groups = {"index": ["SPY", "XLY", "QQQ", "XLK"]}
    report = run_pairs_stress_report(
        get_ohlcv=lambda sym, tf, limit: data[sym], groups=groups,
        limit=n, window=252, step=126,
    )
    assert "Pairs Stat-Arb Stress Test" in report
    assert "Cost sensitivity" in report
    for label, *_ in COST_SCENARIOS:
        assert label in report
    assert "Robustness" in report
