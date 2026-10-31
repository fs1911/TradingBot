import json
import numpy as np
import pandas as pd

from src.backtest.experiments_77 import parse_rows, fetch_month, mid_month, panel, run_experiment77_report


def test_parse_and_fetch_paginates():
    calls = []

    def post(url, body):
        q = json.loads(body)
        calls.append(q["offset"])
        if q["offset"] >= 4:
            return "[]"
        return json.dumps([{"symbolCode": "AAA", "settlementDate": "2020-04-15", "currentShortPositionQuantity": 10,
                            "averageDailyVolumeQuantity": 5}, {"symbolCode": "ZZZ", "settlementDate": "2020-04-15",
                                                               "currentShortPositionQuantity": 1, "averageDailyVolumeQuantity": 1}])
    df, err = fetch_month(post, pd.Period("2020-04", "M"), {"AAA"}, limit=2)
    assert err is None and set(df["symbol"]) == {"AAA"} and calls == [0, 2, 4]
    assert parse_rows("[]").empty


def test_mid_month_and_report():
    d = pd.bdate_range("2018-01-01", "2021-12-31")
    rng = np.random.default_rng(3)
    prices = {f"S{i}": pd.Series(20 * np.exp(np.cumsum(rng.normal(0, 0.02, len(d)))), index=d) for i in range(80)}
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(d)))), index=d)
    rows = []
    for m in pd.period_range("2018-02", "2021-06", freq="M"):
        for day in (15, 28):
            for i in range(80):
                rows.append((f"S{i}", pd.Timestamp(m.year, m.month, day), float(rng.integers(1, 1000)), 100.0))
    si = pd.DataFrame(rows, columns=["symbol", "date", "short", "adv"])
    assert mid_month(si)["date"].dt.day.eq(15).all()
    p = panel(si, prices, spy)
    assert set(p["decile"]) == set(range(1, 11))
    rep = run_experiment77_report(si, [], prices, spy)
    assert "decile 10 − decile 1" in rep
