import json
import numpy as np
import pandas as pd

from src.backtest.experiments_88_90 import (classify_rating, run_experiment88_report, parse_fng, parse_coinmetrics,
                                            first_cross, monthly_ic, run_experiment89_report, fetch_trends, asvi,
                                            run_experiment90_report, entry_indices)


def _px(start, n, seed, drift=0.0003):
    d = pd.bdate_range(start, periods=n)
    r = np.random.default_rng(seed).normal(drift, 0.02, n)
    return pd.Series(50 * np.exp(np.cumsum(r)), index=d)


def test_classify():
    assert classify_rating("Morgan Stanley Upgrades Nvidia to Overweight") == "UPGRADE"
    assert classify_rating("Goldman Downgrades Boeing To Sell") == "DOWNGRADE"
    assert classify_rating("Barclays Raises Price Target On Apple To $250") == "PT_RAISE"
    assert classify_rating("UBS Lowers PT On Tesla") == "PT_CUT"
    assert classify_rating("Analyst upgrades X while another downgrades Y") is None
    assert classify_rating("Tesla deliveries beat") is None


def test_entry_after_news_and_cooldown():
    idx = pd.bdate_range("2020-01-01", periods=30)
    k = entry_indices([idx[3], idx[4], idx[20]], idx, cooldown=5)
    assert k == [4, 21]


def test_report88():
    spy = _px("2016-01-01", 2000, 0)
    px = {"AAA": _px("2016-01-01", 2000, 1), "BBB": _px("2016-01-01", 2000, 2)}
    ts = pd.to_datetime(pd.bdate_range("2017-01-02", periods=60, freq="10B")).tz_localize("America/New_York").tz_convert("UTC")
    ev = {s: pd.DataFrame({"ts": ts, "tone": ["UPGRADE", "DOWNGRADE", "PT_RAISE"] * 20}) for s in px}
    rep = run_experiment88_report(ev, px, spy, ["probe"])
    assert "UPGRADE" in rep and "Holm" in rep


def test_crypto_parsers_and_report():
    body = json.dumps({"data": [{"timestamp": str(int(pd.Timestamp(d).timestamp())), "value": str(v)}
                                for d, v in zip(pd.date_range("2018-02-01", periods=2000), np.random.default_rng(3).integers(5, 95, 2000))]})
    fng = parse_fng(body)
    assert len(fng) == 2000 and fng.index.is_monotonic_increasing
    cm = parse_coinmetrics(json.dumps({"data": [{"asset": "btc", "time": "2020-01-01T00:00:00.000000000Z", "AdrActCnt": "100"},
                                                {"asset": "btc", "time": "2020-01-02T00:00:00.000000000Z", "AdrActCnt": "110"}]}))
    assert list(cm["AdrActCnt"]) == [100.0, 110.0]
    assert len(first_cross(pd.Series([10, 10, 50] + [50] * 40 + [10], index=pd.date_range("2020-01-01", periods=44)),
                           lambda v: v <= 20)) == 2
    d = pd.date_range("2018-02-01", periods=2000)
    px = {"BTC-USD": pd.Series(np.exp(np.cumsum(np.random.default_rng(4).normal(0, 0.04, 2000))) * 1e4, index=d)}
    oc = {"BTC-USD": pd.DataFrame({"AdrActCnt": np.random.default_rng(5).integers(1e5, 2e5, 2000) * 1.0}, index=d)}
    r = monthly_ic(fng, px["BTC-USD"])
    assert r["n"] > 24 and 0 <= r["p"] <= 1
    rep = run_experiment89_report(fng, oc, px, ["probe"])
    assert "extreme fear" in rep and "active addresses" in rep


def test_trends_parse_and_report():
    w = {"widgets": [{"id": "TIMESERIES", "token": "T", "request": {"a": 1}}]}
    weeks = pd.date_range("2021-11-07", periods=260, freq="W-SUN")
    data = {"default": {"timelineData": [{"time": str(int(t.timestamp())), "value": [int(v)]}
                                         for t, v in zip(weeks, np.random.default_rng(6).integers(20, 100, 260))]}}
    calls = []

    def get(url):
        calls.append(url)
        return ")]}'\n" + json.dumps(w) if "explore" in url else ")]}',\n" + json.dumps(data)
    s = fetch_trends(get, "Nvidia")
    assert len(s) == 260 and "token=T" in calls[1]
    assert asvi(s).notna().sum() > 240
    spy = _px("2021-01-01", 1500, 7)
    px, svi = {}, {}
    for i in range(20):
        px[f"S{i}"] = _px("2021-01-01", 1500, 10 + i)
        svi[f"S{i}"] = pd.Series(np.random.default_rng(30 + i).integers(10, 100, 260) * 1.0, index=weeks)
    rep = run_experiment90_report(svi, px, spy, ["probe"])
    assert "Weekly long top-20 %" in rep and "doubled" in rep


def test_trends_no_lookahead():
    from src.backtest.experiments_88_90 import _rets
    d = pd.Timestamp("2022-01-02")  # Sunday label
    idx = pd.date_range("2021-12-01", "2022-03-31", freq="D")
    p = pd.Series(100.0, index=idx)
    p[p.index >= pd.Timestamp("2022-01-05")] = 150.0  # jump inside the labelled week
    r0, r1, r4 = _rets(p, None, d)
    assert abs(r0 - 0.5) < 1e-9 and r1 == 0 and r4 == 0
