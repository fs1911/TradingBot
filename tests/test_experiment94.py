import numpy as np
import pandas as pd

from src.backtest.experiments_94 import (CHAINS, all_symbols, monthly_returns, chain_panel, pooled,
                                         strategy, holm, run_experiment94_report)


def _px(lag_link: bool, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.bdate_range("2009-01-01", "2026-11-13")
    months = d.to_period("M")
    um = months.unique()
    base = {s: rng.normal(0.005, 0.05, len(um)) for s in all_symbols()}
    leaders = {s for _, a, _ in CHAINS for s in a}
    if lag_link:  # followers copy their leader's return one month later
        for _, a, b in CHAINS:
            for s in b:
                base[s] = 0.7 * np.roll(base[a[0]], 1) + rng.normal(0.005, 0.02, len(um))
    px = {}
    for s, r in base.items():
        mclose = pd.Series(100 * np.cumprod(1 + r), index=um)
        px[s] = pd.Series(mclose.reindex(months).to_numpy(), index=d)
    return px, leaders


def test_detects_lagged_link_and_not_noise():
    px, _ = _px(True)
    m = monthly_returns(px)
    p = pooled(chain_panel(m, CHAINS, 1))
    assert p["b"] > 0.3 and p["t"] > 3
    px0, _ = _px(False, seed=1)
    m0 = monthly_returns(px0)
    p0 = pooled(chain_panel(m0, CHAINS, 1))
    assert abs(p0["t"]) < 4


def test_no_lookahead_in_panel():
    px, _ = _px(False, seed=2)
    m = monthly_returns(px)
    pan = chain_panel(m, CHAINS[:1], 1)
    row = pan.iloc[5]
    k = m.index.get_loc(row["month"])
    nxt = m.index[k + 1]
    fb = m.loc[nxt, ["VST", "NRG", "CEG", "XLU"]].mean() - m.loc[nxt, "SPY"]
    assert abs(row["Y"] - fb) < 1e-9


def test_strategy_holm_report():
    px, _ = _px(True, seed=3)
    m = monthly_returns(px)
    s = strategy(m, cost_side=0.005)
    assert len(s) > 150 and s.notna().all()
    assert holm([0.01, 0.04, 0.5]) == [0.03, 0.08, 0.5]
    rep = run_experiment94_report(m, n_perm=20)
    assert "Primary" in rep and "Tesla → lithium" in rep and "2023-06" in rep
