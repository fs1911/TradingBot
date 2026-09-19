"""
Tests for the research pipeline: the rigor harness (evaluate_hypothesis,
walk_forward) and the commodity-ratio mean-reversion strategy.
"""
import numpy as np
import pandas as pd

from src.backtest.research import (
    evaluate_hypothesis, walk_forward, ratio_strategy_returns,
    run_ratio_research, COST_SCENARIOS,
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


def test_walk_forward_counts_windows():
    ret = pd.Series(np.full(1000, 0.001),
                    index=pd.date_range("2016-01-01", periods=1000, freq="1D", tz="UTC"))
    hits, total = walk_forward(ret, window=252, step=126)
    assert total >= 5 and hits == total          # steadily positive → all windows pass


def test_evaluate_flags_no_edge_on_noise():
    rng = np.random.default_rng(0)
    ret = pd.Series(rng.normal(0, 0.01, 1200),
                    index=pd.date_range("2016-01-01", periods=1200, freq="1D", tz="UTC"))
    res = evaluate_hypothesis("noise", ret)
    assert res["verdict"].startswith("❌")        # pure noise → no robust edge


def test_ratio_strategy_profits_on_mean_reverting_ratio():
    """A stationary (mean-reverting) log-ratio → the market-neutral z-score strategy
    should extract a positive return."""
    n = 1500
    common = 100 + np.cumsum(np.random.default_rng(1).normal(0, 1, n))
    ratio = np.exp(_ou(n, theta=0.08, sigma=0.05, seed=2))   # mean-reverting ratio ~1
    a = common * ratio
    b = common
    r = ratio_strategy_returns(_df(a)["close"], _df(b)["close"])
    assert not r.empty and (1 + r).prod() > 1.0


def test_ratio_research_report_wellformed():
    n = 900
    common = 100 + np.cumsum(np.random.default_rng(3).normal(0, 1, n))
    a = common * np.exp(_ou(n, theta=0.08, seed=4))
    data = {"GLD": _df(a), "SLV": _df(common)}
    report = run_ratio_research(
        get_ohlcv=lambda sym, tf, limit: data[sym],
        experiments=[("GLD", "SLV")], limit=n, window=252, step=126,
    )
    assert "Commodity-Ratio Research" in report
    assert "GLD / SLV" in report
    for label, *_ in COST_SCENARIOS:
        assert label in report
    assert "Summary" in report
