"""
Tests for experiment #34: Shiller CAPE (parser + pure analysis on synthetic data).
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_34 import (
    parse_shiller_csv, real_stock_returns, real_bond_returns, forward_annualised,
    expanding_pct_rank, corr_t, mstats, trend_position, run_experiment34_report,
)


def _synthetic(n=1500, seed=0):
    """Monthly series where high CAPE is followed by weak returns (mean reversion)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1871-01-01", periods=n, freq="MS")
    cape = np.empty(n); price = np.empty(n)
    cape[0], price[0] = 15.0, 5.0
    for t in range(1, n):
        exp_ret = 0.008 - 0.0006 * (cape[t - 1] - 16.0)      # high CAPE → low return
        r = exp_ret + rng.normal(0, 0.035)
        price[t] = price[t - 1] * (1 + r)
        cape[t] = max(5.0, cape[t - 1] * (1 + r) * 0.997 + 0.05)
    return pd.DataFrame({"price": price, "div": price * 0.04, "cpi": 10 * 1.002 ** np.arange(n),
                         "gs10": 4.0 + rng.normal(0, 0.1, n), "cape": cape}, index=idx)


def test_parse_shiller_csv():
    txt = ("Date,SP500,Dividend,Earnings,Consumer Price Index,Long Interest Rate,"
           "Real Price,Real Dividend,Real Earnings,PE10\n"
           "1871-01-01,4.44,0.26,0.4,12.46,5.32,89,5.2,8,0\n"
           "1881-01-01,6.19,0.27,0.49,9.42,3.7,163,7,13,18.47\n")
    df = parse_shiller_csv(txt)
    assert list(df.columns) == ["price", "div", "cpi", "gs10", "cape"]
    assert np.isnan(df["cape"].iloc[0]) and df["cape"].iloc[1] == 18.47   # 0 → NaN
    assert parse_shiller_csv("garbage,cols\n1,2\n").empty


def test_real_returns_deflate_inflation():
    idx = pd.date_range("2000-01-01", periods=3, freq="MS")
    df = pd.DataFrame({"price": [100.0, 100.0, 100.0], "div": [0.0, 0.0, 0.0],
                       "cpi": [100.0, 101.0, 102.01], "gs10": [5.0, 5.0, 5.0],
                       "cape": [20.0, 20.0, 20.0]}, index=idx)
    s = real_stock_returns(df)
    assert abs(s.iloc[1] - (1 / 1.01 - 1)) < 1e-12              # flat price, 1% inflation
    b = real_bond_returns(df)
    assert abs(b.iloc[1] - ((1 + 0.05 / 12) / 1.01 - 1)) < 1e-12  # carry only


def test_forward_annualised_and_pct_rank():
    r = pd.Series([0.01] * 24)
    f = forward_annualised(r, 12)
    assert abs(f.iloc[0] - (1.01 ** 12 - 1)) < 1e-9
    assert f.iloc[-1] != f.iloc[-1]                                 # NaN at the end
    x = pd.Series(np.arange(200, dtype=float))
    p = expanding_pct_rank(x, min_hist=120)
    assert p.iloc[:120].isna().all() and p.iloc[150] == 1.0          # new high = top rank


def test_corr_t_and_mstats():
    a = pd.Series(np.arange(50.0)); b = -a
    r, t, n = corr_t(a, b)
    assert r < -0.99 and t < 0 and n == 50
    st = mstats(pd.Series([0.01] * 120))
    assert st["maxdd"] == 0.0 and st["cagr"] > 0.12


def test_trend_position_is_lagged():
    stock = pd.Series([0.05] * 30)
    pos = trend_position(stock, 10)
    assert np.isnan(pos.iloc[0]) and pos.iloc[-1] == 1.0


def test_report_on_synthetic_mean_reverting_cape():
    rep = run_experiment34_report(_synthetic(), "synthetic", n_trials=10)
    assert "Experiment #34" in rep
    assert "1 — Does high CAPE predict" in rep and "3 — Allocation rules" in rep
    assert "CAPE-gated trend" in rep and "Summary" in rep
    # the planted effect should show up as a negative 10y correlation
    line = [l for l in rep.splitlines() if l.startswith("| 10y")][0]
    corr = float(line.split("|")[4])
    assert corr < 0


def test_report_without_data():
    assert "No Shiller data" in run_experiment34_report(pd.DataFrame(), "none")
