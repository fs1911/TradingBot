"""
Tests for experiment #42: chart-technical rules under a circular-shift placebo.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_42 import (
    rule_fib, rule_support, rule_breakout, rule_rsi, rule_macd, rule_bollinger, rule_cross,
    shift_distribution, trades, evaluate_market, pooled_p, run_experiment42_report, RULES,
)


def _walk(n=3000, seed=0, drift=0.0003):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("1990-01-01", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, 0.01, n))), index=idx)


def test_shift_distribution_matches_np_roll():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 800)
    pos = (rng.random(800) > 0.5).astype(float)
    real, plc = shift_distribution(pos, x, min_shift=100)
    assert np.isclose(real, np.dot(pos, x) * 252 / 800)
    k = 150
    assert np.isclose(plc[k - 100], np.dot(np.roll(pos, k), x) * 252 / 800)


def test_fib_enters_on_retracement_and_exits_at_target():
    # up-swing 100 → 200, pullback to ~138 (61.8%), then recovery above 200
    up = np.linspace(100, 200, 120)
    down = np.linspace(200, 135, 30)
    rec = np.linspace(135, 210, 40)
    flat = np.full(250, 100.0)
    c = pd.Series(np.concatenate([flat, up, down, rec]), index=pd.bdate_range("2000-01-01", periods=440))
    pos = rule_fib(c, n=120, level=0.618, stop=0.786, max_hold=200)
    first = pos[pos == 1].index[0]
    assert c[first] <= 200 - 0.618 * 100 + 1e-9 and c[first] > 200 - 0.786 * 100
    assert pos.iloc[-1] == 0  # exited at the old high


def test_rules_are_binary_and_lookahead_free():
    c = _walk(1500)
    for name, fn in RULES.items():
        p = fn(c)
        assert set(np.unique(p.to_numpy())) <= {0.0, 1.0}, name
        # changing the future must not change past signals
        c2 = c.copy()
        c2.iloc[1200:] *= 1.5
        assert (fn(c2).iloc[:1200] == p.iloc[:1200]).all(), name


def test_breakout_and_cross_trend_up():
    idx = pd.bdate_range("2000-01-01", periods=600)
    c = pd.Series(np.linspace(100, 300, 600), index=idx)
    assert rule_breakout(c, 20, 10).iloc[-1] == 1
    assert rule_cross(c).iloc[-1] == 1
    assert rule_macd(c).iloc[-1] in (0.0, 1.0)
    assert rule_rsi(c).sum() == 0  # never oversold in a straight uptrend
    assert rule_bollinger(c).sum() == 0
    assert rule_support(c).sum() == 0


def test_trades_roundtrip():
    pos = np.array([0, 1, 1, 0, 0, 1, 0])
    c = np.array([10, 10, 11, 12, 12, 12, 9.0])
    assert np.allclose(trades(pos, c), [0.2, -0.25])


def test_random_walk_has_no_significant_edge():
    cash = pd.Series(0.0, index=_walk(3000).index)
    res = []
    for s in range(6):
        m = evaluate_market(_walk(3000, seed=s), cash, RULES["Breakout 20/10 (Donchian)"])
        assert m is not None
        res.append(m)
    edge, p = pooled_p(res, 2000)
    assert p > 0.001 and abs(edge) < 0.1


def test_planted_timing_edge_is_detected():
    c = _walk(3000, seed=3, drift=0.0)
    rng = np.random.default_rng(5)
    known = pd.Series(np.repeat(rng.random(150) > 0.5, 20).astype(float), index=c.index)
    r = c.pct_change().fillna(0.0) + known.shift(1).fillna(0.0) * 0.002
    c2 = 100 * (1 + r).cumprod()
    cash = pd.Series(0.0, index=c.index)
    m = evaluate_market(c2, cash, lambda s: known.reindex(s.index))
    edge, p = pooled_p([m, m, m], 2000)
    assert edge > 0.1 and p < 0.01


def test_report_smoke():
    idx = pd.bdate_range("1995-01-01", periods=2000)
    mk = {f"M{i}": ("cls" + str(i % 2), _walk(2000, seed=i)) for i in range(4)}
    mk["short"] = ("cls0", _walk(300))
    rules = {k: RULES[k] for k in list(RULES)[:3]}
    rep = run_experiment42_report(mk, pd.Series(2.0, index=idx), rules=rules)
    assert "Experiment #42" in rep and "Markets usable: 4/5" in rep and "Summary" in rep
