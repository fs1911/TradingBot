"""
Tests for experiment #49: quality score from SEC fundamentals.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_49 import (
    parse_frame, components, quality_score, monthly_returns, form_portfolios, run_experiment49_report,
)


def test_parse_frame():
    js = {"data": [{"cik": 320193, "val": 100.0}, {"cik": 789019, "val": 50}, {"cik": 1, "x": 2}]}
    s = parse_frame(js)
    assert s[320193] == 100.0 and len(s) == 2
    assert parse_frame({}).empty


def test_components_and_score():
    df = pd.DataFrame({"Assets": [100, 100, 100, 100], "GrossProfit": [40, np.nan, 10, 5],
                       "Revenues": [np.nan, 50, np.nan, np.nan], "CostOfRevenue": [np.nan, 20, np.nan, np.nan],
                       "NetIncomeLoss": [10, 8, 1, -5], "StockholdersEquity": [50, 40, 20, 10],
                       "NetCashProvidedByUsedInOperatingActivities": [12, 9, -2, -6],
                       "Liabilities": [50, 60, 80, 90]}, index=[1, 2, 3, 4])
    c = components(df)
    assert abs(c.loc[2, "gross_profitability"] - 0.30) < 1e-9     # GP from revenue − cost
    s = quality_score(c)
    assert s.idxmax() == 1 and s.idxmin() == 4


def _world(n=150, years=range(2010, 2020), seed=0, effect=0.004):
    rng = np.random.default_rng(seed)
    tick = [f"T{i}" for i in range(n)]
    qual = pd.Series(rng.random(n), index=tick)
    idx = pd.bdate_range("2010-01-01", "2021-12-31")
    mkt = rng.normal(0.0003, 0.01, len(idx))
    prices = {}
    for t in tick:
        drift = effect / 21 * (qual[t] - 0.5) * 2
        prices[t] = pd.Series(50 * np.exp(np.cumsum(mkt + drift + rng.normal(0, 0.015, len(idx)))), index=idx)
    scores = {y: qual + rng.normal(0, 0.05, n) for y in years}
    return scores, prices, pd.Series(100 * np.exp(np.cumsum(mkt)), index=idx)


def test_form_portfolios_detects_planted_quality():
    scores, prices, _ = _world()
    px, rets = monthly_returns(prices)
    p = form_portfolios(scores, px, rets)
    assert {"Q1", "Q5", "universe"} <= set(p.columns)
    assert (p["Q5"] - p["Q1"]).mean() > 0.003
    pr = form_portfolios(scores, px, rets, rng=np.random.default_rng(1))
    assert abs((pr["Q5"] - pr["Q1"]).mean()) < abs((p["Q5"] - p["Q1"]).mean())


def test_report_smoke():
    scores, prices, spy = _world(n=80)
    ciks = {i: f"T{i}" for i in range(80)}
    frames = {}
    rng = np.random.default_rng(3)
    for y in range(2010, 2020):
        frames[y] = pd.DataFrame({"Assets": 2e9, "GrossProfit": rng.random(80) * 1e9,
                                  "NetIncomeLoss": rng.normal(1e8, 5e7, 80), "StockholdersEquity": 1e9,
                                  "NetCashProvidedByUsedInOperatingActivities": rng.normal(1e8, 5e7, 80),
                                  "Liabilities": 1e9}, index=list(range(80)))
    rep = run_experiment49_report(frames, [], ciks, prices, spy, n_placebo=5)
    assert "Experiment #49" in rep and "Q5 − universe" in rep and "Summary" in rep
    assert "No fundamentals" in run_experiment49_report({}, ["x"], {}, {}, spy)
