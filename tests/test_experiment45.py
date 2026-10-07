"""
Tests for experiment #45: Finanzradar trend signal per asset.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_45 import (
    monthly_closes, monthly_cash, trend_score, events, false_rates, follow,
    placebo_p, analyse_asset, run_experiment45_report,
)


def _daily(drifts, seed=0, start="2000-01-03"):
    rng = np.random.default_rng(seed)
    parts, n = [], 0
    for d, days in drifts:
        parts.append(d + rng.normal(0, 0.008, days))
        n += days
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(100 * np.exp(np.cumsum(np.concatenate(parts))), index=idx)


def test_score_and_events_follow_regimes():
    px = monthly_closes(_daily([(0.001, 800), (-0.0015, 500), (0.001, 800)]))
    cash = pd.Series(0.0, index=px.index)
    sc = trend_score(px, cash)
    assert sc.dropna().between(0, 3).all()
    ev = events(sc)
    kinds = list(ev["kind"])
    assert "exit" in kinds and "entry" in kinds
    assert kinds.index("exit") < len(kinds) - 1   # re-entry after the bear phase


def test_monthly_cash():
    idx = pd.period_range("2020-01", periods=4, freq="M")
    irx = pd.Series([1.2] * 90, index=pd.bdate_range("2019-12-01", periods=90))
    c = monthly_cash(irx, idx)
    assert np.allclose(c, 0.012 / 12)


def test_false_rates():
    idx = pd.period_range("2020-01", periods=8, freq="M")
    sc = pd.Series([0, 2, 1, 1, 0, 2, 3, 3], index=idx, dtype=float)
    px = pd.Series([100, 100, 95, 94, 90, 92, 99, 101], index=idx, dtype=float)
    fe, fx = false_rates(px, sc, events(sc))
    assert fe == 0.5      # entry at 100 reversed at 95 (false); entry at 92 holds
    assert fx == 1.0      # exit at 90 reversed at 92


def test_follow_and_placebo_detect_planted_timing():
    idx = pd.period_range("1990-01", periods=360, freq="M")
    rng = np.random.default_rng(3)
    w = pd.Series((rng.random(360) > 0.5).astype(float), index=idx)
    r = rng.normal(0, 0.03, 360) + w.shift(1).fillna(0).to_numpy() * 0.03
    px = pd.Series(100 * np.cumprod(1 + r), index=idx)
    cash = pd.Series(0.0, index=idx)
    edge, p, plc = placebo_p(w, px, cash)
    assert edge > 0.05 and p < 0.01   # planted ≈ 0.03·12·¼ ≈ 9% p.a.
    assert len(follow(px, cash, w, 10.0)) == 359


def test_analyse_and_report_smoke():
    d = _daily([(0.0006, 1500), (-0.001, 400), (0.0006, 1500)])
    irx = pd.Series(2.0, index=d.index)
    r = analyse_asset("X", "Indizes", d, irx)
    assert r and r["graded"] and 0 <= r["invested"] <= 1
    rep = run_experiment45_report([{"name": "X", "yahoo": "X", "class": "Indizes"},
                                   {"name": "Y", "yahoo": "Y", "class": "Krypto"}],
                                  {"X": d, "Y": _daily([(0.002, 2000)], seed=4)}, irx)
    assert "Experiment #45" in rep and "Pooled placebo" in rep and "Summary" in rep
