"""
Tests for experiment #20: cross-sectional long/short over individual stocks.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_20 import (
    build_price_panel, _decile_weights, _rebalance_dates,
    long_short_returns, score_reversal, score_momentum,
    run_experiment20_report,
)

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def _make_universe(n_syms=30, n_days=800, seed=0):
    rng = np.random.default_rng(seed)
    data = {}
    for i in range(n_syms):
        px = 100 + np.cumsum(rng.normal(0.02, 1.0, n_days))
        data[f"S{i:02d}"] = _df(np.maximum(px, 1.0))
    return data


def test_decile_weights_are_dollar_neutral():
    score = pd.Series({f"S{i}": float(i) for i in range(20)})
    w = _decile_weights(score, top=0.1, bottom=0.1)
    assert abs(w[w > 0].sum() - 1.0) < 1e-9      # long leg sums to +1
    assert abs(w[w < 0].sum() + 1.0) < 1e-9      # short leg sums to -1
    assert abs(w.sum()) < 1e-9                    # dollar neutral
    # highest score is long, lowest is short
    assert w["S19"] > 0 and w["S0"] < 0


def test_decile_weights_handles_tiny_input():
    w = _decile_weights(pd.Series({"A": 1.0, "B": 2.0}), 0.1, 0.1)
    assert (w == 0).all()                         # <10 names → flat


def test_rebalance_dates_frequency():
    dates = pd.date_range("2020-01-01", periods=200, freq="1D")
    assert _rebalance_dates(dates, "D") == set(dates)
    monthly = _rebalance_dates(dates, "M")
    assert 6 <= len(monthly) <= 8                 # ~7 month-ends in 200 days
    weekly = _rebalance_dates(dates, "W")
    assert len(weekly) > len(monthly)


def test_score_functions_are_causal_and_shaped():
    panel = pd.DataFrame({"A": np.arange(1, 301.0), "B": np.arange(300, 0.0, -1)})
    rev = score_reversal(panel, lookback=5)
    # A rose → reversal dislikes it (lower score) than falling B
    assert rev["A"] < rev["B"]
    mom = score_momentum(panel, lookback=252, skip=21)
    assert mom["A"] > mom["B"]                     # A trended up → higher momentum


def test_long_short_returns_flat_before_first_rebalance_and_finite():
    data = _make_universe()
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100)
    r = long_short_returns(panel, lambda ps: score_reversal(ps, 5),
                           rebalance="D", cost_bps=5.0)
    assert len(r) == len(panel)
    assert r.iloc[0] == 0.0                        # no position day 0
    assert np.isfinite(r.to_numpy()).all()


def test_costs_reduce_returns():
    data = _make_universe()
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100)
    cheap = long_short_returns(panel, lambda ps: score_reversal(ps, 5), "D", cost_bps=0.0)
    dear = long_short_returns(panel, lambda ps: score_reversal(ps, 5), "D", cost_bps=20.0)
    assert dear.sum() < cheap.sum()                # higher costs → lower cumulative


def test_report_structure_and_missing_symbols():
    data = _make_universe(n_syms=30, n_days=800)
    universe = list(data) + ["MISSING1", "MISSING2"]
    report = run_experiment20_report(
        get_ohlcv=lambda s, tf, lim: data.get(s, pd.DataFrame()),
        universe=universe, limit=800,
    )
    assert "Experiment #20" in report
    assert "Short-term reversal" in report
    assert "momentum" in report.lower()
    assert "Survivorship bias" in report          # honesty note present
    assert "Summary" in report


def test_report_handles_insufficient_universe():
    data = _make_universe(n_syms=5)                # <20 names
    report = run_experiment20_report(
        get_ohlcv=lambda s, tf, lim: data.get(s, pd.DataFrame()),
        universe=list(data), limit=800,
    )
    assert "Insufficient data" in report
