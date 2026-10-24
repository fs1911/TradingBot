"""
Tests for experiment #50: share buybacks vs issuance.
"""
import math

import numpy as np
import pandas as pd

from src.backtest.experiments_50 import issuance_from_concept, issuance_scores, selected_portfolio, run_experiment50_report
from src.backtest.experiments_49 import monthly_returns


def test_issuance_from_concept_same_filing_split_safe():
    js = {"units": {"shares": [
        # FY2015 10-K: current 90, prior (restated) 100  → buyback
        {"start": "2015-01-01", "end": "2015-12-31", "val": 90, "accn": "a1", "fy": 2015, "fp": "FY",
         "form": "10-K", "filed": "2016-02-20"},
        {"start": "2014-01-01", "end": "2014-12-31", "val": 100, "accn": "a1", "fy": 2015, "fp": "FY",
         "form": "10-K", "filed": "2016-02-20"},
        # FY2016 10-K after a 2:1 split: both years doubled → issuance only +10%
        {"start": "2016-01-01", "end": "2016-12-31", "val": 198, "accn": "a2", "fy": 2016, "fp": "FY",
         "form": "10-K", "filed": "2017-02-20"},
        {"start": "2015-01-01", "end": "2015-12-31", "val": 180, "accn": "a2", "fy": 2016, "fp": "FY",
         "form": "10-K", "filed": "2017-02-20"},
        # quarterly fact ignored
        {"start": "2016-10-01", "end": "2016-12-31", "val": 1, "accn": "a2", "fy": 2016, "fp": "FY",
         "form": "10-K", "filed": "2017-02-20"},
    ]}}
    d = issuance_from_concept(js)
    assert abs(d[2015][0] - math.log(0.9)) < 1e-12
    assert abs(d[2016][0] - math.log(1.1)) < 1e-12           # split does not look like issuance
    assert d[2016][1] == pd.Timestamp("2017-02-20")
    assert issuance_from_concept({}) == {}


def test_issuance_scores_point_in_time():
    iss = {1: {2015: (-0.1, pd.Timestamp("2016-02-20"))}, 2: {2015: (0.2, pd.Timestamp("2016-09-01"))},
           3: {2015: (3.0, pd.Timestamp("2016-02-01"))}}
    sc = issuance_scores(iss, {1: "AAA", 2: "BBB", 3: "CCC"}, [2015])
    assert list(sc[2015].index) == ["AAA"]          # BBB filed too late, CCC implausible
    assert sc[2015]["AAA"] == 0.1


def _world(n=120, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", "2020-12-31")
    mkt = rng.normal(0.0003, 0.01, len(idx))
    ni = pd.Series(rng.normal(0, 0.05, n), index=[f"T{i}" for i in range(n)])
    prices = {t: pd.Series(50 * np.exp(np.cumsum(mkt - ni[t] * 0.02 / 21 * 10 + rng.normal(0, 0.015, len(idx)))),
                           index=idx) for t in ni.index}
    return ni, prices, pd.Series(100 * np.exp(np.cumsum(mkt)), index=idx)


def test_selected_portfolio():
    _, prices, _ = _world()
    px, rets = monthly_returns(prices)
    r = selected_portfolio({2012: [f"T{i}" for i in range(10)]}, px, rets)
    assert len(r) == 12 and r.index[0] == pd.Period("2013-07", "M")


def test_report_smoke():
    ni, prices, spy = _world()
    tmap = {i: f"T{i}" for i in range(len(ni))}
    iss = {i: {y: (float(ni[f"T{i}"]), pd.Timestamp(f"{y + 1}-02-15")) for y in range(2010, 2019)} for i in range(len(ni))}
    rng = np.random.default_rng(1)
    frames = {y: pd.DataFrame({"Assets": 2e9, "GrossProfit": rng.random(len(ni)) * 1e9,
                               "NetIncomeLoss": rng.normal(1e8, 5e7, len(ni)), "StockholdersEquity": 1e9,
                               "NetCashProvidedByUsedInOperatingActivities": rng.normal(1e8, 5e7, len(ni)),
                               "Liabilities": 1e9}, index=list(range(len(ni)))) for y in range(2010, 2019)}
    rep = run_experiment50_report(frames, iss, 0, tmap, prices, spy, n_placebo=5)
    assert "Experiment #50" in rep and "Buybacks (Q5) − universe" in rep and "Summary" in rep
