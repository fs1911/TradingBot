import json
import numpy as np
import pandas as pd

from src.backtest.experiments_75_79 import parse_px_divs, parse_eps, sue, drift, dividend_group, run_experiments75_79_report


def test_parse_px_divs():
    ts = [int(pd.Timestamp(d).timestamp()) for d in ("2020-01-02", "2020-01-03")]
    js = {"chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{"close": [10, 11]}], "adjclose": [{"adjclose": [9.5, 10.5]}]},
                                "events": {"dividends": {"x": {"date": ts[1], "amount": 0.25}}}}]}}
    px, dv = parse_px_divs(json.dumps(js))
    assert px.iloc[-1] == 10.5 and dv.iloc[0] == 0.25


def test_eps_sue():
    facts = []
    for y in range(2012, 2020):
        for q, (s, e) in enumerate([("01-01", "03-31"), ("04-01", "06-30"), ("07-01", "09-30")]):
            facts.append({"form": "10-Q", "start": f"{y}-{s}", "end": f"{y}-{e}", "filed": f"{y}-{e[:2]}-28",
                          "val": 1.0 + 0.1 * (y - 2012) + (0.5 if y == 2019 and q == 0 else 0)})
    d = parse_eps({"units": {"USD/shares": facts}})
    assert len(d) == 24
    s = sue(d)
    assert s["sue"].idxmax() == s.index[s["end"] == pd.Timestamp("2019-03-31")][0] or s["sue"].max() > 1


def test_dividend_groups():
    form = pd.Timestamp("2020-06-30")
    yrs = pd.date_range("2013-03-01", "2020-03-01", freq="YS-MAR")
    grower = pd.Series(np.linspace(1, 2, len(yrs)), index=yrs)
    assert dividend_group(grower, form) == "grower (5 y)"
    assert dividend_group(pd.Series(dtype=float), form) == "non-payer"
    cut = pd.Series([1.0, 1.0, 1.0, 0.5], index=pd.to_datetime(["2017-03-01", "2018-03-01", "2019-03-01", "2020-03-01"]))
    assert dividend_group(cut, form) == "cutter"
    init = pd.Series([0.3], index=pd.to_datetime(["2020-02-01"]))
    assert dividend_group(init, form) == "initiator"


def test_report_runs():
    d = pd.bdate_range("2005-01-03", "2024-12-31")
    rng = np.random.default_rng(0)
    prices = {f"T{i}": pd.Series(20 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, len(d)))), index=d) for i in range(60)}
    divs = {t: pd.Series(0.2, index=pd.date_range("2005-03-01", "2024-03-01", freq="QS")) for t in prices}
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(d)))), index=d)
    rep = run_experiments75_79_report({}, {}, prices, divs, spy)
    assert "#75" in rep and "#79" in rep and "steady" in rep
