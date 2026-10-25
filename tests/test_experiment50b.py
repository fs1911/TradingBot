"""
Tests for experiment #50b: hardening buybacks vs issuance.
"""
import math

import numpy as np
import pandas as pd

from src.backtest.experiments_50b import parse_concept_full, hold, run_experiment50b_report


def _f(start, end, val, accn, form, filed):
    return {"start": start, "end": end, "val": val, "accn": accn, "form": form, "filed": filed, "fp": "FY"}


def test_parse_concept_full_annual_and_quarterly():
    js = {"units": {"shares": [
        _f("2015-01-01", "2015-12-31", 95, "k1", "10-K", "2016-02-20"),
        _f("2014-01-01", "2014-12-31", 100, "k1", "10-K", "2016-02-20"),
        _f("2016-04-01", "2016-06-30", 90, "q1", "10-Q", "2016-08-05"),
        _f("2015-04-01", "2015-06-30", 100, "q1", "10-Q", "2016-08-05"),
    ]}}
    a, q = parse_concept_full(js)
    assert abs(a[2015][0] - math.log(0.95)) < 1e-12 and a[2015][2] == 95
    assert len(q) == 1 and abs(q[0][1] - math.log(0.9)) < 1e-12
    assert q[0][2] == pd.Timestamp("2016-08-05")
    assert parse_concept_full({}) == ({}, [])


def test_hold_renormalises_missing():
    idx = pd.period_range("2015-01", periods=6, freq="M")
    rets = pd.DataFrame({"A": [0.01] * 6, "B": [0.03, np.nan, 0.03, 0.03, 0.03, 0.03]}, index=idx)
    r = hold({pd.Period("2015-01", "M"): pd.Series({"A": 0.5, "B": 0.5})}, rets, 3)
    assert list(r.index) == list(pd.period_range("2015-02", periods=3, freq="M"))
    assert abs(r[pd.Period("2015-02", "M")] - 0.01) < 1e-12        # B missing → only A
    assert abs(r[pd.Period("2015-03", "M")] - 0.02) < 1e-12


def test_report_smoke():
    rng = np.random.default_rng(0)
    n = 150
    idx = pd.bdate_range("2009-01-01", "2021-12-31")
    mkt = rng.normal(0.0003, 0.01, len(idx))
    tick = [f"T{i}" for i in range(n)]
    ni = pd.Series(rng.normal(0, 0.05, n), index=tick)
    prices = {t: pd.Series(50 * np.exp(np.cumsum(mkt - ni[t] * 0.01 + rng.normal(0, 0.015, len(idx)))), index=idx)
              for t in tick}
    tmap = {i: t for i, t in enumerate(tick)}
    concepts = {}
    for i, t in enumerate(tick):
        ann = {y: (float(ni[t]), pd.Timestamp(f"{y + 1}-02-15"), 1e8) for y in range(2009, 2020)}
        qs = [(pd.Timestamp(f"{y}-{m:02d}-28"), float(ni[t]), pd.Timestamp(f"{y}-{m:02d}-28") + pd.Timedelta(days=40), 1e8)
              for y in range(2010, 2021) for m in (3, 6, 9)]
        concepts[i] = (ann, qs)
    frames = {y: pd.DataFrame({"Assets": np.where(np.arange(n) < 75, 5e9, 5e10), "GrossProfit": rng.random(n) * 1e9,
                               "NetIncomeLoss": rng.normal(1e8, 5e7, n), "StockholdersEquity": 1e9,
                               "NetCashProvidedByUsedInOperatingActivities": rng.normal(1e8, 5e7, n),
                               "Liabilities": 1e9}, index=list(range(n))) for y in range(2009, 2020)}
    rep = run_experiment50b_report(frames, concepts, 0, tmap, prices)
    assert "Experiment #50b" in rep and "6a Fresh quarterly" in rep and "App rule" in rep
    base = [l for l in rep.splitlines() if l.startswith("| Baseline")][0]
    assert "—" not in base.split("|")[2]          # baseline produced a number
