import io
import tarfile
import numpy as np
import pandas as pd

from src.backtest.experiments_100 import (parse_robintrack_tar, herd_events, event_returns, clustered_t, weekly_spread,
                                          flow_signal, flow_events, run_experiment100_report)


def _tar():
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode="w:gz") as tf:
        for tk, base in (("AAA", 200), ("BBB", 40)):
            rows = ["timestamp,users_holding"]
            for i, d in enumerate(pd.date_range("2019-01-01 15:00", periods=40, freq="D")):
                u = base * (2 if i == 20 else 1) if i < 21 else base * 2
                rows.append(f"{d:%Y-%m-%d %H:%M:%S},{u}")
            data = "\n".join(rows).encode()
            ti = tarfile.TarInfo(f"tmp/popularity_export/{tk}.csv"); ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
    b.seek(0)
    return b


def test_parse_and_herd_events_and_entry_next_day():
    users = parse_robintrack_tar(_tar())
    assert list(users.columns) == ["AAA"]          # BBB never reaches 100 users
    ev = herd_events(users)
    assert len(ev) == 1 and ev.iloc[0]["ticker"] == "AAA"
    d = pd.bdate_range("2018-12-01", "2019-03-30")
    p = pd.Series(np.arange(len(d), dtype=float) + 10, index=d)
    spy = pd.Series(100.0, index=d)
    er = event_returns(ev, {"AAA": p}, spy)
    i = p.index.searchsorted(ev.iloc[0]["date"], side="right")
    assert abs(er.iloc[0][1] - (p.iloc[i + 1] / p.iloc[i] - 1)) < 1e-12


def test_flow_signal_and_events():
    d = pd.date_range("2016-01-01", periods=1500, freq="D")
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"FlowInExNtv": rng.random(1500) * 100, "FlowOutExNtv": rng.random(1500) * 100,
                       "SplyExNtv": 1e5, "PriceUSD": 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 1500)))}, index=d)
    s = flow_signal(df)
    assert s.notna().sum() > 1400
    r = flow_events(s, df["PriceUSD"], 0.95, True)
    assert r["n"] > 5 and 7 in r and 30 in r


def test_report_without_robintrack():
    d = pd.date_range("2016-01-01", periods=1500, freq="D")
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"FlowInExNtv": rng.random(1500), "FlowOutExNtv": rng.random(1500), "SplyExNtv": 100.0,
                       "PriceUSD": 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 1500)))}, index=d)
    rep = run_experiment100_report(None, {}, None, {"btc": df}, ["diag"])
    assert "not available" in rep and "btc" in rep and "Holm" in rep
