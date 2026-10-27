import numpy as np
import pandas as pd

from src.backtest.experiments_60 import (bar_returns, positions, evaluate, variance_ratio, analyse_symbol,
                                         run_experiment60_report, resample)


def _minutes(days=60, seed=0, ar=0.0, crypto=False):
    rng = np.random.default_rng(seed)
    if crypto:
        idx = pd.date_range("2024-01-01", periods=days * 1440, freq="min", tz="UTC")
    else:
        d = pd.bdate_range("2024-01-02", periods=days)
        idx = pd.DatetimeIndex([t for day in d for t in pd.date_range(day + pd.Timedelta(hours=14, minutes=30),
                                                                     periods=390, freq="min")]).tz_localize("UTC")
    e = rng.normal(0, 0.0005, len(idx))
    r = np.zeros(len(idx))
    for i in range(1, len(idx)):
        r[i] = ar * r[i - 1] + e[i]
    c = 100 * np.exp(np.cumsum(r))
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1.0}, index=idx)


def test_session_and_flat_overnight():
    d = bar_returns(_minutes(5), True)
    assert d["first"].sum() == 5 and d.groupby("day").size().iloc[0] == 390
    p = positions(d, "R1 momentum", True, 1)
    assert (p[d["last"]] == 0).all()


def test_planted_autocorrelation_found_by_momentum():
    d = bar_returns(_minutes(30, ar=0.3), True)
    ev = evaluate(d, positions(d, "R1 momentum", True, 1))
    ev2 = evaluate(d, positions(d, "R2 reversal", True, 1))
    assert ev["gross_total"] > 0 > ev2["gross_total"] and ev["t_gross"] > 3
    vr, z = variance_ratio(d["r"], 4)
    assert vr > 1 and z > 3


def test_no_lookahead_on_noise():
    d = bar_returns(_minutes(30, seed=4), True)
    ev = evaluate(d, positions(d, "R1 momentum", True, 1))
    assert abs(ev["t_gross"]) < 3.5


def test_analyse_and_report_stock_and_crypto():
    res = {"SPY": analyse_symbol(_minutes(40), "SPY"), "BTC/USD": analyse_symbol(_minutes(8, crypto=True), "BTC/USD")}
    assert 5 in res["SPY"]["bars"] and "R5 opening range" in res["SPY"]["bars"][1]["rules"]
    assert "R5 opening range" not in res["BTC/USD"]["bars"][1]["rules"]
    rep = run_experiment60_report(res)
    assert "Coverage" in rep and "break-even" in rep and "Selection honesty" in rep and "Summary" in rep
    assert len(resample(_minutes(2), 5)) < len(_minutes(2))


def test_month_edges_mixed_timezones():
    from src.backtest.experiments_60 import month_edges
    e = month_edges("2020-01-15", pd.Timestamp("2020-04-10", tz="UTC"))
    assert str(e.tz) == "UTC" and len(e) == 5 and e[0] == pd.Timestamp("2020-01-15", tz="UTC")
    assert e[-1] == pd.Timestamp("2020-04-10", tz="UTC")
