import numpy as np
import pandas as pd

from src.backtest.experiments_97 import (SYMBOLS, components, fg_index, rolling_pct, zone_entries, fwd, strategy,
                                         parse_cnn, run_experiment97_report, LONG)


def _px(seed=0):
    rng = np.random.default_rng(seed)
    d = pd.bdate_range("2002-01-01", "2026-11-19")
    px = {}
    for s in SYMBOLS:
        if s.startswith("^VIX"):
            px[s] = pd.Series(np.clip(20 + np.cumsum(rng.normal(0, 1, len(d))) * 0.1, 9, 80), index=d)
        else:
            px[s] = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(d)))), index=d)
    return px


def test_rolling_pct_and_index_range():
    x = pd.Series(np.arange(300, dtype=float))
    p = rolling_pct(x)
    assert np.isnan(p.iloc[100]) and p.iloc[-1] > 99
    ix = fg_index(components(_px()), LONG)
    v = ix.dropna()
    assert len(v) > 4000 and v.min() >= 0 and v.max() <= 100


def test_zone_entries_gap():
    ix = pd.Series([50] * 30 + [20, 20, 50, 20] + [50] * 25 + [20], index=pd.bdate_range("2020-01-01", periods=60), dtype=float)
    ev = zone_entries(ix, below=25)
    assert len(ev) == 2 and ev[0] == ix.index[30] and ev[1] == ix.index[59]


def test_fwd_entry_next_day_and_strategy_lag():
    d = pd.bdate_range("2020-01-01", periods=10)
    p = pd.Series(np.arange(1, 11, dtype=float), index=d)
    assert abs(fwd(p, 2).iloc[0] - (p.iloc[3] / p.iloc[1] - 1)) < 1e-12
    ix = pd.Series(80.0, index=d)          # greed from day 0 → S1 out from the 3rd return on
    r = strategy(p, None, ix, "S1", cost_side=0.0)
    assert (r.iloc[1:] == 0).all() and r.iloc[0] > 0  # day-0 signal acts from day 2's return


def test_parse_cnn_and_report():
    js = {"fear_and_greed_historical": {"data": [{"x": 1700000000000, "y": 22.0}, {"x": 1700086400000, "y": 30.0}]}}
    s = parse_cnn(js)
    assert len(s) == 2 and s.iloc[0] == 22.0
    rep = run_experiment97_report(_px(1), cnn=None)
    assert "extreme fear" in rep and "S2 buy fear" in rep and "Latest" in rep
