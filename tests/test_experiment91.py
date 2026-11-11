import numpy as np
import pandas as pd

from src.backtest.experiments_91 import rule_signals, drawdown_episodes, run_experiment91_report


def _px():
    d = pd.bdate_range("2015-01-02", "2026-11-10")
    n = len(d)
    r = np.random.default_rng(9).normal(0.0012, 0.03, n)
    k = d.get_loc(pd.Timestamp("2026-10-06"))
    r[k + 1:] = -0.012  # steady fall after the peak
    r[k] = 0.05
    return pd.Series(100 * np.exp(np.cumsum(r)), index=d)


def test_rules_use_past_only_and_turn_red():
    px = _px()
    s = rule_signals(px)
    assert set(s) and all(len(v) == len(px) for v in s.values())
    a = s["A close < 200-day avg"]
    px2 = px.copy(); px2.iloc[-1] *= 0.1   # changing the last price must not change earlier signals
    a2 = rule_signals(px2)["A close < 200-day avg"]
    assert (a.iloc[:-1].fillna(-1) == a2.iloc[:-1].fillna(-1)).all()


def test_episodes():
    d = pd.bdate_range("2020-01-01", periods=8)
    px = pd.Series([100, 120, 80, 85, 125, 90, 60, 70], index=d)
    eps = drawdown_episodes(px, 0.25)
    assert eps[0] == (d[1], d[2]) and eps[1] == (d[4], d[6])


def test_report():
    px = _px()
    spy = pd.Series(np.linspace(100, 200, len(px)), index=px.index)
    ts = pd.to_datetime(["2026-11-08T15:00:00Z", "2026-11-09T14:00:00Z"], utc=True)
    arts = pd.DataFrame({"ts": ts, "headline": ["Board launches probe into CEO", "Stock plunges amid investigation"]})
    rep = run_experiment91_report(px, spy, arts, diag=["probe"])
    assert "turned red on" in rep and "Position size" in rep and "probe" in rep
