import json
import numpy as np
import pandas as pd

from src.backtest.experiments_87 import (parse_timeline, fetch_series, signals, event_days, excess_series,
                                         run_experiment87_report, UNIVERSE)


def _tl(dates, vals, name="Average Tone"):
    return json.dumps({"timeline": [{"series": name, "data": [{"date": f"{d:%Y%m%d}T000000Z", "value": v}
                                                              for d, v in zip(dates, vals)]}]})


def test_parse_and_fetch_daily_or_chunked():
    d = pd.date_range("2020-01-01", "2020-12-31", freq="D")
    s = parse_timeline(_tl(d, np.ones(len(d))))
    assert len(s) == len(d)
    calls = []

    def get(url):
        calls.append(url)
        if len(calls) == 1:  # first call: coarse (monthly) → triggers yearly chunks
            m = pd.date_range("2019-01-01", "2020-12-31", freq="MS")
            return _tl(m, np.ones(len(m)))
        y = 2019 if "startdatetime=2019" in url else 2020
        dd = pd.date_range(f"{y}-01-01", f"{y}-12-31", freq="D")
        return _tl(dd, np.full(len(dd), 2.0), "Article Count")
    out = fetch_series(get, '"X"', "timelinevolraw", pd.Timestamp("2019-01-01"), pd.Timestamp("2020-12-31"), sleep=0)
    assert len(calls) == 3 and len(out) == 731 and (out == 2.0).all()


def test_signals_events_and_entry_after_news_day():
    d = pd.date_range("2020-01-01", periods=200, freq="D")
    rng = np.random.default_rng(0)
    tone = pd.Series(rng.normal(0, 1, 200), index=d)
    tone.iloc[150] = 10.0
    count = pd.Series(rng.poisson(20, 200) * 1.0, index=d); count.iloc[150] = 2000.0
    s = signals(tone, count)
    assert s["tone_z"].iloc[150] > 2 and s["att_z"].iloc[150] > 3
    px_idx = pd.bdate_range("2020-01-01", periods=200)
    k = event_days(s["tone_z"] >= 2, px_idx)
    first = s.index[s["tone_z"] >= 2][0]
    assert k and px_idx[k[0]] > first


def test_report_runs():
    d = pd.bdate_range("2017-01-02", "2020-12-31")
    rng = np.random.default_rng(1)
    px, sig = {}, {}
    for q, sym in UNIVERSE[:25]:
        px[sym] = pd.Series(50 * np.exp(np.cumsum(rng.normal(0, 0.02, len(d)))), index=d)
        cd = pd.date_range("2017-01-01", "2020-12-31", freq="D")
        sig[sym] = signals(pd.Series(rng.normal(0, 1, len(cd)), index=cd), pd.Series(rng.poisson(30, len(cd)) * 1.0, index=cd))
    bench = {"SPY": pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(d)))), index=d)}
    ex = excess_series(px[UNIVERSE[0][1]], bench["SPY"])
    assert np.isnan(ex["1 d"][-1])
    rep = run_experiment87_report(sig, px, bench, ["probe: daily"])
    assert "E1 tone shock +" in rep and "Holm" in rep
