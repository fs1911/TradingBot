import numpy as np
import pandas as pd

from src.backtest.experiments_95 import aligned_daily
from src.backtest.experiments_98 import (SYMBOLS, GROUP_A, weekly_frames, panel, pooled, rule_returns,
                                         run_experiment98_report)


def _px(link: bool, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.bdate_range("2017-01-02", "2026-11-20")
    wk = d.to_period("W-FRI")
    uw = wk.unique()
    base = {s: rng.normal(0.002, 0.06, len(uw)) for s in SYMBOLS}
    if link:
        for s in GROUP_A:
            base[s] = 0.7 * np.roll(base["BTC-USD"], 1) + rng.normal(0.0, 0.02, len(uw))
    px = {}
    for s, r in base.items():
        wc = pd.Series(100 * np.cumprod(1 + r), index=uw)
        px[s] = pd.Series(wc.reindex(wk).to_numpy(), index=d)
    return px


def test_detects_weekly_lag_and_not_noise():
    w, k = weekly_frames(aligned_daily(_px(True)))
    p = pooled(panel(w, k, "BTC-USD", GROUP_A))
    assert p["b"] > 0.3 and p["t"] > 3
    w0, k0 = weekly_frames(aligned_daily(_px(False, 1)))
    assert abs(pooled(panel(w0, k0, "BTC-USD", GROUP_A))["t"]) < 4


def test_no_lookahead_next_week():
    w, k = weekly_frames(aligned_daily(_px(False, 2)))
    p = panel(w, k, "BTC-USD", {"IREN": None})
    row = p.iloc[10]
    i = w.index.get_loc(row["week"])
    assert abs(row["Y"] - (w["IREN"].iloc[i + 1] - w["SPY"].iloc[i + 1])) < 1e-9


def test_rule_costs_and_report():
    w, k = weekly_frames(aligned_daily(_px(True, 3)))
    g, n = rule_returns(w, "BTC-USD", GROUP_A, 0.0), rule_returns(w, "BTC-USD", GROUP_A, 0.0145)
    assert (n <= g + 1e-12).all() and (g - n).max() > 0
    rep = run_experiment98_report(w, k, n_perm=10)
    assert "A bitcoin → new stocks" in rep and "Holm" in rep and "net Yuh" in rep
