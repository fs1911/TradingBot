"""
Tests for experiment #46: macro filters against false trend signals.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_46 import (
    parse_fred_csv, to_monthly, stress_series, filtered_weight, exits_and_false,
    placebo_filter, run_experiment46_report,
)
from src.backtest.experiments_45 import monthly_closes, monthly_cash, trend_score


def test_parse_fred_csv():
    s = parse_fred_csv("observation_date,UNRATE\n1948-01-01,3.4\n1948-02-01,3.8\n1948-03-01,.\n")
    assert len(s) == 2 and s.iloc[1] == 3.8


def _macro(n=480, start="1980-01-01"):
    idx = pd.date_range(start, periods=n, freq="MS")
    t = np.arange(n)
    un = 5 + 2 * np.sin(t / 30)
    return {"UNRATE": pd.Series(un, index=idx),
            "BAA": pd.Series(7 + np.sin(t / 20), index=idx), "AAA": pd.Series(np.full(n, 6.0), index=idx),
            "GS10": pd.Series(5 + np.sin(t / 40), index=idx), "TB3MS": pd.Series(np.full(n, 5.2), index=idx),
            "VIXCLS": pd.Series(20 + 10 * np.sin(t / 15), index=idx),
            "CAPE": pd.Series(20 + 5 * np.sin(t / 50), index=idx)}


def test_stress_series_lags_and_vote():
    idx = pd.period_range("1980-01", periods=480, freq="M")
    st = stress_series(_macro(), idx)
    assert {"F1 unemployment", "F2 credit spread", "F3 yield curve", "F4 VIX>25",
            "F5 CAPE>median", "F6 macro vote (≥2 of F1–F3)"} <= set(st)
    un = to_monthly(_macro()["UNRATE"])
    raw = (un > un.rolling(12).mean())
    # F1 uses last month's reading (publication lag)
    assert st["F1 unemployment"].iloc[100] == raw.iloc[99]


def test_ended_series_does_not_freeze():
    idx = pd.period_range("1980-01", periods=480, freq="M")
    m = _macro()
    m["CAPE"] = m["CAPE"].iloc[:300]
    st = stress_series(m, idx)["F5 CAPE>median"]
    assert st.iloc[-1] != st.iloc[-1] or pd.isna(st.iloc[-1])   # NaN after the data ends


def test_filtered_weight():
    idx = pd.period_range("2000-01", periods=4, freq="M")
    sc = pd.Series([0, 1, 3, 0], index=idx, dtype=float)
    st = pd.Series([True, False, True, np.nan], index=idx)
    w = filtered_weight(sc, st)
    assert list(w) == [0.0, 1.0, 1.0, 0.0]


def test_exits_and_false():
    idx = pd.period_range("2000-01", periods=6, freq="M")
    w = pd.Series([1, 0, 1, 1, 0, 0], index=idx, dtype=float)
    px = pd.Series([100, 90, 95, 96, 90, 80], index=idx, dtype=float)
    per_dec, fx = exits_and_false(px, w)
    assert fx == 0.5 and per_dec > 0


def test_report_smoke():
    rng = np.random.default_rng(0)
    d = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 7000))),
                  index=pd.bdate_range("1985-01-01", periods=7000))
    irx = pd.Series(3.0, index=d.index)
    rep = run_experiment46_report([{"name": "X", "yahoo": "X"}], {"X": d}, irx, _macro(520, "1984-01-01"))
    assert "Experiment #46" in rep and "F6 macro vote" in rep and "Crisis" in rep
    px = monthly_closes(d)
    cash = monthly_cash(irx, px.index)
    sc = trend_score(px, cash).dropna()
    st = stress_series(_macro(520, "1984-01-01"), sc.index)["F1 unemployment"]
    real, p = placebo_filter(px.loc[sc.index], cash.loc[sc.index], sc, st)
    assert np.isfinite(real) and 0 <= p <= 1


def test_parse_dbnomics_and_bls():
    from src.backtest.experiments_46 import parse_dbnomics_json, parse_bls_json
    db = '{"series": {"docs": [{"period": ["1948-01", "1948-02", "1948-03"], "value": [3.4, "NA", 4.0]}]}}'
    s = parse_dbnomics_json(db)
    assert len(s) == 2 and s.iloc[-1] == 4.0
    bls = ('{"Results": {"series": [{"data": [{"year": "2024", "period": "M02", "value": "3.9"},'
           '{"year": "2024", "period": "M01", "value": "3.7"}, {"year": "2024", "period": "M13", "value": "3.8"}]}]}}')
    b = parse_bls_json(bls)
    assert list(b) == [3.7, 3.9]
    assert parse_dbnomics_json("garbage").empty and parse_bls_json("{}").empty


def test_fetch_macro_falls_back_to_yahoo(monkeypatch):
    import src.backtest.experiments_46 as m
    def boom(*a, **k):
        raise OSError("blocked")
    monkeypatch.setattr(m, "_get", boom)
    idx = pd.bdate_range("1985-01-01", periods=9000)
    rng = np.random.default_rng(1)
    yahoo = {s: pd.Series(np.abs(rng.normal(3, 0.5, len(idx))) + 1, index=idx)
             for s in ("VWEHX", "VFITX", "^TNX", "^IRX", "^VIX")}
    macro, src, err = m.fetch_macro(lambda sym, start: yahoo.get(sym, pd.Series(dtype=float)))
    assert src["UNRATE"] == "none" and "FRED UNRATE" in err
    assert "VWEHX" in src["credit"] and src["curve"] == "Yahoo ^TNX/^IRX" and src["VIX"] == "Yahoo ^VIX"
    st = m.stress_series(macro, pd.period_range("1990-01", periods=300, freq="M"))
    assert {"F2 credit spread", "F3 yield curve", "F4 VIX>25"} <= set(st)
    assert "F1 unemployment" not in st
