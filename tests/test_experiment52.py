import numpy as np
import pandas as pd

from src.backtest.experiments_52 import size_spreads, ms, run_experiment52_report


def _df(n=600, small_prem=0.01):
    idx = pd.period_range("1970-01", periods=n, freq="M")
    rng = np.random.default_rng(1)
    cols = [f"S{s}C{c}" for s in range(1, 6) for c in range(1, 6)]
    df = pd.DataFrame(rng.normal(0.008, 0.04, (n, 25)), index=idx, columns=cols)
    df["S1C5"] += small_prem          # planted premium only in the smallest quintile
    return df


def test_size_spreads_positions():
    sp = size_spreads(_df())
    assert set(sp) == {1, 2, 3, 4, 5, "small_high", "big_high"}
    assert sp[1].mean() > 0.008 and abs(sp[5].mean()) < 0.006


def test_ms_short_series_nan():
    assert np.isnan(ms(pd.Series([0.01] * 10))["t"])


def test_report_contains_sections():
    df = _df()
    ff5 = pd.DataFrame({"Mkt-RF": 0.005, "RF": 0.003}, index=df.index)
    rep = run_experiment52_report({"Value (B/M)": df, "Momentum (12-2)": pd.DataFrame(),
                                   "Profitability (OP)": df.iloc[:, :10]}, ff5)
    assert "Value (B/M)" in rep and "1 (smallest)" in rep and "Long-only small & high" in rep
    assert "Momentum (12-2): no data" in rep and "unexpected format" in rep
