import numpy as np
import pandas as pd

from src.backtest.experiments_86 import (first_cross_above, drawdown_events, policy_events,
                                         us_elections, outcomes, boot_p, holm, build_events,
                                         run_experiment86_report)


def _px(n=2000, seed=1):
    d = pd.bdate_range("2000-01-03", periods=n)
    r = np.random.default_rng(seed).normal(0.0003, 0.012, n)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=d)


def test_first_cross_needs_quiet_period():
    d = pd.bdate_range("2020-01-01", periods=400)
    x = pd.Series(20.0, index=d)
    x.iloc[150] = 45; x.iloc[160] = 45; x.iloc[350] = 45
    ev = first_cross_above(x, 40)
    assert ev == [d[150], d[350]]


def test_drawdown_rearms_after_new_high():
    d = pd.bdate_range("2020-01-01", periods=6)
    px = pd.Series([100, 85, 80, 110, 95, 98], index=d)
    assert drawdown_events(px, 0.10) == [d[1], d[4]]


def test_policy_first_cut_after_pause():
    m = pd.period_range("2000-01", periods=14, freq="M")
    r = pd.Series([5, 5, 5, 5, 5, 5, 5, 4.75, 4.5, 4.5, 4.5, 4.5, 4.5, 4.5], index=m)
    ev = policy_events(r, -1)
    assert len(ev) == 1 and ev[0].month == 8


def test_elections_are_tuesdays():
    e = us_elections(2016, 2024)
    assert [x.strftime("%Y-%m-%d") for x in e] == ["2016-11-08", "2020-11-03", "2024-11-05"]


def test_outcomes_and_bootstrap():
    px = _px()
    o = outcomes(px, [px.index[10]])
    assert abs(o["1 M"].iloc[0] - (px.iloc[31] / px.iloc[10] - 1)) < 1e-12
    base = np.random.default_rng(0).normal(0, 1, 5000)
    assert boot_p(base, 20, 0.0) > 0.5
    assert boot_p(base, 20, 2.0) < 0.01
    h = holm({"a": 0.01, "b": 0.04})
    assert abs(h["a"] - 0.02) < 1e-12 and abs(h["b"] - 0.04) < 1e-12


def test_report_runs():
    px = _px(); vix = pd.Series(np.where(np.arange(2000) % 500 == 300, 45.0, 18.0), index=px.index)
    ev = build_events(px, vix=vix)
    txt = run_experiment86_report({"S&P 500": px}, ev, btc=None)
    assert "any day" in txt and "Holm" in txt
