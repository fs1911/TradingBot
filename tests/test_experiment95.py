import numpy as np
import pandas as pd

from src.backtest.experiments_95 import (GROUPS, all_symbols, aligned_daily, monthly_frames, panel, pooled,
                                         run_experiment95_report)


def _px(link: bool, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.bdate_range("2009-01-01", "2026-11-13")
    um = d.to_period("M").unique()
    base = {s: rng.normal(0.005, 0.05, len(um)) for s in all_symbols()}
    if link:
        for g in GROUPS.values():
            for _, a, b, _ in g:
                for s in b:
                    base[s] = 0.7 * np.roll(base[a[0]], 1) + rng.normal(0.005, 0.02, len(um))
    px = {}
    for s, r in base.items():
        mc = pd.Series(100 * np.cumprod(1 + r), index=um)
        px[s] = pd.Series(mc.reindex(d.to_period("M")).to_numpy(), index=d)
    return px


def test_alignment_drops_weekend_values():
    d = pd.date_range("2024-01-01", "2024-03-31", freq="D")  # 24/7 asset
    btc = pd.Series(np.arange(len(d), dtype=float) + 1, index=d)
    spy_d = pd.bdate_range("2024-01-01", "2024-03-31")
    spy = pd.Series(np.ones(len(spy_d)) * 100, index=spy_d)
    al = aligned_daily({"SPY": spy, "BTC-USD": btc})
    # March 2024 ended on a Sunday: the aligned month-end value must be Friday 29 March
    assert al["BTC-USD"].loc["2024-03-29"] == btc.loc["2024-03-29"]
    assert al.index[-1] == pd.Timestamp("2024-03-29")


def test_detects_link_and_skip_variant():
    m, s = monthly_frames(aligned_daily(_px(True)))
    from src.backtest.experiments_95 import GROUP_A
    p = pooled(panel(m, s, GROUP_A, "next"))
    assert p["b"] > 0.3 and p["t"] > 3
    m0, s0 = monthly_frames(aligned_daily(_px(False, 1)))
    assert abs(pooled(panel(m0, s0, GROUP_A, "next"))["t"]) < 4


def test_report_runs():
    m, s = monthly_frames(aligned_daily(_px(True, 2)))
    rep = run_experiment95_report(m, s, n_perm=10)
    assert "silver → silver miners" in rep and "Holm" in rep and "follow the lagging producer" in rep
