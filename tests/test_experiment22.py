"""
Tests for experiment #22: alpha-vs-beta decomposition of long-only momentum.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_20 import build_price_panel
from src.backtest.experiments_21 import score_momentum
from src.backtest.experiments_22 import (
    equal_weight_benchmark, long_only_excess, run_experiment22_report,
)

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def _make_universe(n_syms=30, n_days=900, seed=0):
    rng = np.random.default_rng(seed)
    return {f"S{i:02d}": _df(np.maximum(100 + np.cumsum(rng.normal(0.02, 1.0, n_days)), 1.0))
            for i in range(n_syms)}


def test_benchmark_is_mean_of_daily_returns():
    data = _make_universe()
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100)
    bench = equal_weight_benchmark(panel)
    expected = panel.pct_change().mean(axis=1).fillna(0.0)
    assert np.allclose(bench.to_numpy(), expected.to_numpy())


def test_excess_is_portfolio_minus_benchmark_and_neutralizes_beta():
    data = _make_universe()
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100)
    port, bench, excess = long_only_excess(panel, lambda ps: score_momentum(ps), top=0.1)
    assert np.allclose(excess.to_numpy(), (port - bench).to_numpy())
    # excess is market-neutral: far lower correlation to the benchmark than the
    # raw long-only portfolio (which is ~fully long the market)
    corr_port = np.corrcoef(port.iloc[260:], bench.iloc[260:])[0, 1]
    corr_excess = np.corrcoef(excess.iloc[260:], bench.iloc[260:])[0, 1]
    assert corr_excess < corr_port


def test_report_structure_and_columns():
    data = _make_universe(n_syms=30, n_days=900)
    report = run_experiment22_report(
        get_ohlcv=lambda s, tf, lim: data.get(s, pd.DataFrame()),
        universe=list(data), limit=900,
    )
    assert "Experiment #22" in report
    assert "alpha or beta" in report.lower()
    assert "Bench Sharpe" in report and "Alpha Sharpe" in report
    assert "Raw 12-1" in report and "Residual" in report and "Vol-scaled" in report
    assert "Summary" in report


def test_report_handles_insufficient_universe():
    data = _make_universe(n_syms=5)
    report = run_experiment22_report(
        get_ohlcv=lambda s, tf, lim: data.get(s, pd.DataFrame()),
        universe=list(data), limit=900,
    )
    assert "Insufficient data" in report
