import numpy as np
import pandas as pd

from src.backtest.experiments_93 import event_row, run_experiment93_report, EVENTS


def test_event_row_and_report():
    d = pd.bdate_range("2019-01-01", "2026-11-13")
    spy = pd.Series(np.linspace(100, 200, len(d)), index=d)
    px = {s: pd.Series(np.linspace(50, 80, len(d)), index=d) for _, _, syms in EVENTS for s in syms}
    r = event_row(px, spy, "2022-08-09", ["SOXX"])
    assert r["n_sym"] == 1 and np.isfinite(r["+1 Y"]) and r["dd"] <= 0
    late = event_row(px, spy, "2026-05-28", ["RCAT"])
    assert np.isnan(late["+1 Y"])
    rep = run_experiment93_report(px, spy)
    assert "CHIPS" in rep and "beat SPY in" in rep
