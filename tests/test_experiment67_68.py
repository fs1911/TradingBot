import json
import numpy as np
import pandas as pd

from src.backtest.experiments_67_68 import (fetch_dbnomics, monthly, unhedged, hedged, stats, rolling_win,
                                            run_experiments67_68_report)


def test_hedge_math():
    idx = pd.period_range("2000-01", periods=4, freq="M")
    r = pd.Series([0.0, 0.01, 0.01, 0.01], index=idx)
    fx = pd.Series([1.0, 1.0, 0.9, 0.9], index=idx)
    u = unhedged(r, fx)
    assert abs(u.iloc[1] - (1.01 * 0.9 - 1)) < 1e-12
    h = hedged(r, pd.Series(1.0, index=idx), pd.Series(4.0, index=idx))
    assert abs(h.iloc[-1] - (0.01 - 0.03 / 12)) < 1e-12


def test_dbnomics_fetch_parses():
    doc = {"series": {"docs": [{"period": [f"{y}-{m:02d}" for y in range(1990, 2001) for m in range(1, 13)],
                                "value": [1.5] * 132}]}}
    out, src = fetch_dbnomics(lambda url: json.dumps(doc))
    assert set(out) >= {"CHF per USD", "CH policy rate"} and "DBnomics" in src["CHF per USD"]


def test_report_end_to_end():
    d = pd.bdate_range("1990-01-01", "2025-12-31")
    rng = np.random.default_rng(0)
    px = lambda: pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(d)))), index=d)
    m = pd.period_range("1990-01", "2025-12", freq="M")
    macro = {"CHF per USD": pd.Series(np.linspace(1.5, 0.9, len(m)), index=m),
             "EUR per USD": pd.Series(0.9, index=m), "CH policy rate": pd.Series(1.0, index=m),
             "US policy rate": pd.Series(4.0, index=m), "EA policy rate": pd.Series(2.5, index=m)}
    rep = run_experiments67_68_report(macro, {"x": "test"}, px(), px(), px(), {})
    assert "Hedge the currency" in rep and "Home bias" in rep and "Best mix in the first half" in rep
