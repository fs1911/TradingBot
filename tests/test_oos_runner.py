"""
Tests for the out-of-sample backtest runner. Real market data can't be fetched
in CI, so these use a synthetic random-walk OHLC series to verify the runner
splits IS/OOS, runs each strategy, and produces a well-formed Markdown verdict
report without crashing.
"""
import numpy as np
import pandas as pd
import yaml
from pathlib import Path

from src.backtest.oos_runner import run_and_report, split_is_oos, _pool
from src.strategies.supertrend import SupertrendStrategy
from src.strategies.breakout_momentum import BreakoutMomentumStrategy

CONFIG_DIR = Path(__file__).parent.parent / "config"


def _synthetic(n=2000):
    idx = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    rng = np.random.default_rng(42)
    close = 100 + rng.normal(0, 0.5, n).cumsum()
    open_ = close + rng.normal(0, 0.1, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.3, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.3, n))
    vol = rng.uniform(100, 1000, n)
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": vol}, index=idx)


def test_split_is_oos_halves():
    df = _synthetic(1000)
    is_df, oos_df = split_is_oos(df, 0.5)
    assert len(is_df) == 500 and len(oos_df) == 500
    assert is_df.index[-1] < oos_df.index[0]   # chronological, no overlap


def test_pool_metrics():
    class T:
        def __init__(self, pnl): self.pnl = pnl
    pooled = _pool([T(10), T(-5), T(20), T(-5)])
    assert pooled["trades"] == 4
    assert pooled["net"] == 20
    assert pooled["pf"] == 3.0        # gross win 30 / gross loss 10
    assert pooled["wr"] == 50


def test_run_and_report_wellformed():
    df = _synthetic(2000)
    reg = {"supertrend": SupertrendStrategy, "breakout_momentum": BreakoutMomentumStrategy}
    with open(CONFIG_DIR / "strategy_config.yaml") as f:
        strat_cfg = yaml.safe_load(f)

    report = run_and_report(
        get_ohlcv=lambda sym, tf, limit: df,
        active_strategies=["supertrend", "breakout_momentum"],
        registry=reg,
        strategy_cfg=strat_cfg,
        symbols=["BTC/USD"],
        timeframe="15Min",
        limit=2000,
    )
    assert "Out-of-Sample Backtest" in report
    assert "OOS PF" in report                 # table header present
    assert "supertrend" in report
    assert "breakout_momentum" in report
    # one data + header row minimum; verdict words present
    assert "Verdict" in report
