import numpy as np
import pandas as pd

from src.backtest.experiments_92 import monthly_features, build_panel, portfolio, run_experiment92_report
from src.scanner.yuh_scanner import GREEN, RED


def _daily(seed, drift, start="2008-01-01", n=3000):
    d = pd.bdate_range(start, periods=n)
    r = np.random.default_rng(seed).normal(drift, 0.02, n)
    return pd.Series(50 * np.exp(np.cumsum(r)), index=d)


def test_features_and_panel():
    feats = {f"T{i}": monthly_features(_daily(i, 0.0008 if i % 2 else -0.0004)) for i in range(40)}
    spy = monthly_features(_daily(99, 0.0004))
    months = pd.period_range("2010-01", "2018-12", freq="M")
    d = build_panel(feats, lambda t, m: (0.06 if t == "T3" else -0.03), spy, months)
    assert set(d["colour"]) <= {"🟢", "🟡", "🔴"} and len(d) > 1000
    assert (d.loc[d["ticker"] == "T3", "colour"] == RED).all()          # dilution → always red
    g, r = d[d["colour"] == GREEN], d[d["colour"] == RED]
    assert len(g) and len(r)
    p = portfolio(d, GREEN, 0.005)
    assert p.index.is_monotonic_increasing
    spy_ret = spy["close"].pct_change()
    rep = run_experiment92_report(d, spy_ret, ["probe"])
    assert "🟢 − 🔴 next month" in rep and "≈ Yuh" in rep


def test_young_ipo_flag():
    feats = {f"T{i}": monthly_features(_daily(i, 0.001, start="2008-01-01")) for i in range(30)}
    feats["NEW"] = monthly_features(_daily(77, 0.002, start="2011-01-03", n=2000))
    spy = monthly_features(_daily(99, 0.0004))
    d = build_panel(feats, lambda t, m: float("nan"), spy, pd.period_range("2012-06", "2012-08", freq="M"))
    assert d.loc[d["ticker"] == "NEW", "young"].all()
    assert not d.loc[d["ticker"] == "T1", "young"].any()
