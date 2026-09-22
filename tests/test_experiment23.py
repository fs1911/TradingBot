"""
Tests for experiment #23: the rebalancing premium.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_20 import build_price_panel, _rebalance_dates
from src.backtest.experiments_23 import (
    buy_and_hold_returns, rebalanced_returns, rebalancing_premium,
    run_experiment23_report,
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


def test_quarter_rebalance_dates_added():
    dates = pd.date_range("2020-01-01", periods=400, freq="1D")
    q = _rebalance_dates(dates, "Q")
    assert 4 <= len(q) <= 6                      # ~5 quarter-ends in 400 days
    assert len(q) < len(_rebalance_dates(dates, "M"))


def test_buy_and_hold_flat_first_day_and_finite():
    data = _make_universe()
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100).dropna()
    bh = buy_and_hold_returns(panel)
    assert len(bh) == len(panel)
    assert bh.iloc[0] == 0.0
    assert np.isfinite(bh.to_numpy()).all()


def test_rebalancing_premium_isolates_harvest_on_mean_reverting_universe():
    # Two anti-correlated assets that oscillate: rebalancing should harvest a
    # POSITIVE premium over buy&hold (classic volatility-harvesting example),
    # padded to a full 20+ name universe of the same oscillators so the panel builds.
    n = 800
    t = np.arange(n)
    a = 100 + 20 * np.sin(t / 15.0)
    b = 100 - 20 * np.sin(t / 15.0) + 40      # anti-phase, kept positive
    data = {}
    for i in range(12):
        data[f"A{i:02d}"] = _df(a)
        data[f"B{i:02d}"] = _df(b)
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100).dropna()
    reb, bh, excess = rebalancing_premium(panel, rebalance="M", cost_bps=0.0)
    assert len(excess) == len(panel)
    assert excess.sum() > 0                      # harvest is positive on oscillators


def test_costs_reduce_the_premium():
    data = _make_universe()
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100).dropna()
    _, _, cheap = rebalancing_premium(panel, "W", cost_bps=0.0)
    _, _, dear = rebalancing_premium(panel, "W", cost_bps=25.0)
    assert dear.sum() < cheap.sum()              # turnover costs eat the premium


def test_report_structure():
    data = _make_universe(n_syms=30, n_days=900)
    report = run_experiment23_report(
        get_ohlcv=lambda s, tf, lim: data.get(s, pd.DataFrame()),
        universe=list(data), limit=900,
    )
    assert "Experiment #23" in report
    assert "rebalancing premium" in report.lower()
    assert "B&H Sharpe" in report and "Premium Sharpe" in report
    assert "weekly" in report and "monthly" in report and "quarterly" in report
    assert "Summary" in report
