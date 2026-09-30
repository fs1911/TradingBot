"""
Tests for experiment #44: backtest of the exact live trend-portfolio rule.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_44 import backtest_rule, stats, run_experiment44_report
from src.strategies.trend_portfolio import build_panel


def _px(n=1600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    t = np.arange(n)
    mk = lambda d, v: pd.Series(100 * np.exp(d * t + np.cumsum(rng.normal(0, v, n))), index=idx)
    didx = pd.date_range("2010-01-01", periods=int(n * 1.45), freq="D")
    return {"SPY": mk(0.0004, 0.01), "IEF": mk(0.0001, 0.004), "GLD": mk(0.0002, 0.009),
            "TLT": mk(-0.0003, 0.008), "BIL": mk(0.00008, 0.0001),
            "BTC-USD": pd.Series(100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, len(didx)))), index=didx)}


def test_backtest_rule_runs_and_is_long_only_bounded():
    prices = _px()
    closes = {("BTC/USD" if k == "BTC-USD" else k): v for k, v in prices.items()}
    panel = build_panel(closes, "SPY")
    r, g, t = backtest_rule(panel, ["SPY", "IEF", "GLD", "TLT", "BTC/USD"], "BIL",
                            caps={"BTC/USD": 0.1})
    assert len(r) > 800 and 0 < g <= 1.0 + 1e-9 and t > 0
    assert stats(r, panel["BIL"].pct_change().fillna(0))["maxdd"] > -0.5


def test_report_smoke():
    rep = run_experiment44_report(_px(), ["SPY", "IEF", "GLD", "TLT", "BTC/USD"],
                                  {"BTC/USD": "BTC-USD"})
    assert "Experiment #44" in rep and "Live rule (ETFs + BTC/ETH)" in rep and "Summary" in rep
