import json
import numpy as np
import pandas as pd

from src.backtest.experiments_85 import (fetch_year, fundamentals, fair_value, health_score, two_strike_portfolio,
                                         run_experiment85_report, DURATION, INSTANT)


def _raw(n=200, seed=0):
    rng = np.random.default_rng(seed)
    idx = range(1, n + 1)
    rev = rng.uniform(2e9, 2e10, n)
    d = {"Revenues": rev, "GrossProfit": rev * rng.uniform(0.2, 0.6, n), "NetIncomeLoss": rev * rng.uniform(-0.05, 0.2, n),
         "OperatingIncomeLoss": rev * rng.uniform(0, 0.25, n), "DepreciationDepletionAndAmortization": rev * 0.05,
         "NetCashProvidedByUsedInOperatingActivities": rev * 0.15, "PaymentsToAcquirePropertyPlantAndEquipment": rev * 0.05,
         "Assets": rev * 2, "StockholdersEquity": rev * 0.8, "Liabilities": rev * 1.2, "LongTermDebt": rev * 0.5,
         "CashAndCashEquivalentsAtCarryingValue": rev * 0.1, "AssetsCurrent": rev * 0.6, "LiabilitiesCurrent": rev * 0.4,
         "shares": rng.uniform(1e8, 1e9, n)}
    return pd.DataFrame(d, index=list(idx))


def test_fetch_year_uses_all_tags():
    calls = []
    def get(url):
        calls.append(url)
        return json.dumps({"data": [{"cik": 1, "val": 5.0}]})
    df = fetch_year(get, 2020)
    assert len(calls) == len(DURATION) + len(INSTANT) + 1 and "CY2020Q4I" in calls[-1] and df.loc[1, "shares"] == 5.0


def test_fair_value_logic():
    f = fundamentals(_raw(), _raw(seed=1))
    sector = pd.Series({i: "A" if i % 2 else "B" for i in f.index})
    mcap = f["ni"].clip(lower=1) * 15
    fv = fair_value(f, mcap, sector)
    cheap = fv["upside"].idxmax()
    assert fv.loc[cheap, "upside"] > 0 and (fv["n_methods"] <= 3).all()
    hs = health_score(f, sector, f["ni"] / mcap)
    assert hs.dropna().between(0, 100).all() and hs.notna().sum() > 50


def test_two_strike_rule():
    u = {2010: pd.Series({"A": 0.3, "B": 0.2}), 2011: pd.Series({"A": -0.1, "B": 0.1}),
         2012: pd.Series({"A": -0.2, "B": 0.1})}
    p = two_strike_portfolio(u)
    assert p[2011] == ["A", "B"] and p[2012] == ["B"]


def test_report_runs():
    years = {y: _raw(seed=y) for y in range(2010, 2022)}
    tmap = {i: f"T{i}" for i in range(1, 201)}
    sector = pd.Series({i: str(i % 5) for i in range(1, 201)})
    months = pd.period_range("2010-01", "2024-12", freq="M")
    rng = np.random.default_rng(3)
    rets = pd.DataFrame(rng.normal(0.01, 0.06, (len(months), 200)), index=months, columns=list(tmap.values()))
    px = 20 * (1 + rets).cumprod()
    rep = run_experiment85_report(years, sector, tmap, px, rets)
    assert "Fair value" in rep and "Health score" in rep and "app rule" in rep
