"""
Tests for experiment #43: Buffett factors (French data + own single-stock test).
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_43 import (
    parse_french_monthly, mt, factor_table, long_only_tilts, sharpe_diff_monthly,
    month_scores, quintile_backtest, run_experiment43_report,
)

FF_TEXT = """This file was created by CMPT_ME_BEME_OP_INV_RETS using the 202407 CRSP database.
The 1-month TBill rate data until 202405 come from Ibbotson Associates.

,Mkt-RF,SMB,HML,RMW,CMA,RF
196307,  -0.39,  -0.41,  -0.97,   0.68,  -1.18,   0.27
196308,   5.07,  -0.80,   1.80,   0.36,  -0.35,   0.25
196309,  -1.57,  -0.52,   0.13,  -0.71,   0.29,   0.27

 Annual Factors: January-December
,Mkt-RF,SMB,HML,RMW,CMA,RF
  1964,  12.52,   0.40,  11.93,   2.37,   6.19,   3.54
"""


def test_parse_french_monthly():
    df = parse_french_monthly(FF_TEXT)
    assert list(df.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert len(df) == 3 and str(df.index[0]) == "1963-07"
    assert abs(df.loc["1963-08", "Mkt-RF"] - 0.0507) < 1e-12
    assert parse_french_monthly("garbage").empty


def test_parse_missing_values():
    txt = ",Lo 20,Hi 20\n196307, -99.99, 1.00\n196308, 2.00, 3.00\n"
    df = parse_french_monthly(txt)
    assert np.isnan(df.iloc[0, 0]) and df.iloc[1, 1] == 0.03


def _french(n=400, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("1980-01", periods=n, freq="M")
    ff5 = pd.DataFrame({"Mkt-RF": rng.normal(0.006, 0.045, n), "SMB": rng.normal(0, 0.03, n),
                        "HML": rng.normal(0.004, 0.03, n), "RMW": rng.normal(0.003, 0.02, n),
                        "CMA": rng.normal(0.002, 0.02, n), "RF": np.full(n, 0.003)}, index=idx)
    q = lambda: pd.DataFrame({"Lo 20": rng.normal(0.009, 0.035, n), "Hi 20": rng.normal(0.008, 0.06, n)}, index=idx)
    return {"ff5": ff5, "mom": pd.DataFrame({"Mom": rng.normal(0.006, 0.04, n)}, index=idx),
            "var": q(), "beta": q(), "op": q(), "bm": q(), "eu5": ff5.iloc[120:], "eumom": None}


def test_factor_and_tilt_tables():
    d = _french()
    f = factor_table(d)
    assert {"HML (value)", "RMW (quality/profitability)", "UMD (momentum)", "Low-var − high-var quintile"} <= set(f)
    t = long_only_tilts(d)
    assert "Buffett mix (low-var + profitable + value, 1/3 each)" in t


def test_mt_and_sharpe_diff():
    idx = pd.period_range("1990-01", periods=300, freq="M")
    rng = np.random.default_rng(2)
    a = pd.Series(rng.normal(0.01, 0.03, 300), index=idx)
    b = pd.Series(rng.normal(0.0, 0.03, 300), index=idx)
    assert mt(a)["t"] > 3
    bt = sharpe_diff_monthly(a, b, n=500)
    assert bt["obs"] > 0 and bt["lo"] > 0 and bt["p"] < 0.05


def _stocks(n_stocks=20, n=1500, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    mkt = rng.normal(0.0003, 0.01, n)
    px = {}
    for i in range(n_stocks):
        b = 0.4 + 1.2 * i / n_stocks
        px[f"S{i}"] = pd.Series(100 * np.exp(np.cumsum(b * mkt + rng.normal(0, 0.01, n))), index=idx)
    return px, pd.Series(100 * np.exp(np.cumsum(mkt)), index=idx)


def test_month_scores_beta_ordering_and_backtest():
    px, ix = _stocks()
    months = month_scores(pd.DataFrame(px), ix, "beta")
    assert months, "no months"
    sc = months[-1]["score"]
    assert sc["S0"] < sc["S19"]
    bt = quintile_backtest(months)
    assert {"low", "high", "all", "bab_raw"} <= set(bt.columns)
    assert (bt["beta_low"] < bt["beta_high"]).all()
    pb = quintile_backtest(months, rng=np.random.default_rng(0))
    assert len(pb) == len(bt)


def test_report_smoke():
    px, ix = _stocks()
    rep = run_experiment43_report(_french(), {"Test": (px, ix)}, n_trials=50, n_placebo=5)
    assert "Part A" in rep and "Part B" in rep and "A3" in rep
    rep2 = run_experiment43_report({}, {}, n_trials=50, n_placebo=5)
    assert "skipped" in rep2
