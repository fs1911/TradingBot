import json
import numpy as np
import pandas as pd

from src.backtest.experiments_64 import (symbols, parse_timeseries, parse_splits, share_changes, classify,
                                         build_groups, run_experiment64_report)


def test_symbols_suffixes():
    s = symbols()
    assert s["NESN.SW"] == "CH" and s["SAP.DE"] == "DE" and s["ASML.AS"] == "NL" and len(s) > 150


def test_parse_and_split_safe_changes():
    js = {"timeseries": {"result": [{"meta": {"type": ["annualDilutedAverageShares"]},
          "annualDilutedAverageShares": [{"asOfDate": "2021-12-31", "reportedValue": {"raw": 100.0}},
                                         {"asOfDate": "2022-12-31", "reportedValue": {"raw": 97.0}},
                                         {"asOfDate": "2023-12-31", "reportedValue": {"raw": 194.0}}]}]}}
    ts = parse_timeseries(json.dumps(js))
    ch = share_changes(ts, pd.Series(dtype=float))
    assert abs(ch[pd.Timestamp("2022-12-31")] + 0.03) < 1e-12
    assert pd.Timestamp("2023-12-31") not in ch            # +100 % without a split → rejected
    sp = parse_splits(json.dumps({"chart": {"result": [{"events": {"splits": {"1": {
        "date": int(pd.Timestamp("2023-06-01").timestamp()), "numerator": 2, "denominator": 1}}}}]}}))
    ch2 = share_changes(ts, sp)
    assert abs(ch2[pd.Timestamp("2023-12-31")]) < 1e-12     # 2:1 split → 0 %
    assert classify(-0.03) == "buyback" and classify(0.06) == "dilution" and classify(0.01) == "neutral"


def test_point_in_time_and_report():
    rng = np.random.default_rng(0)
    country = {f"S{i}.SW": "CH" for i in range(40)}
    changes = {s: pd.Series({pd.Timestamp(f"{y}-12-31"): rng.choice([-0.04, 0.0, 0.08]) for y in range(2015, 2025)})
               for s in country}
    g = build_groups(changes, country, [2020])
    s0 = next(iter(g[2020]))
    assert g[2020][s0][2] == changes[s0][pd.Timestamp("2019-12-31")]   # FY2020 not yet known in June 2020
    d = pd.bdate_range("2014-01-01", "2026-06-30")
    prices = {s: pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(d)))), index=d) for s in country}
    rep = run_experiment64_report(changes, country, prices)
    assert "buyback − dilution" in rep and "formation (June)" in rep
