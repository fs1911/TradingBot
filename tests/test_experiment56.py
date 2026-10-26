import numpy as np
import pandas as pd

from src.backtest.experiments_56 import legs, candidates, factor_momentum, stats, run_experiment56_report


def _six(idx, rng, hi_bonus=0.0):
    df = pd.DataFrame(rng.normal(0.007, 0.045, (len(idx), 6)), index=idx,
                      columns=["SMALL LoX", "ME1 X2", "SMALL HiX", "BIG LoX", "ME2 X2", "BIG HiX"])
    df.iloc[:, 5] += hi_bonus
    return df


def _frames(n=432, start="1990-07", bonus=0.004):
    idx = pd.period_range(start, periods=n, freq="M")
    rng = np.random.default_rng(5)
    ff = pd.DataFrame({"Mkt-RF": rng.normal(0.005, 0.04, n), "RF": 0.002}, index=idx)
    return {"bm": _six(idx, rng), "op": _six(idx, rng), "mom": _six(idx, rng, bonus), "ff": ff}


def test_legs_positions():
    f = _frames()
    L = legs(f["bm"], f["op"], f["mom"], f["ff"])
    assert (L["P1 Momentum big"] == f["mom"].iloc[:, 5]).all()
    assert (L["P3 Small value"] == f["bm"].iloc[:, 2]).all()
    assert np.allclose(L["Market"], f["ff"]["Mkt-RF"] + 0.002)


def test_factor_momentum_uses_past_only():
    idx = pd.period_range("2000-01", periods=40, freq="M")
    a = pd.Series(0.0, index=idx); a.iloc[20] = 0.5          # huge month 20 must not be picked at 20
    L = pd.DataFrame({"P1 Momentum big": a, "P2 Quality big": 0.01, "Market": 0.005})
    s, _ = factor_momentum(L, list(L.columns), k=1)
    assert s.loc[idx[20]] < 0.1                               # picked P2 (best past), not P1
    assert s.loc[idx[21]] > 0.4 or s.loc[idx[21]] < 0.1       # month 21 may pick P1 (now in the past)


def test_costs_reduce_and_planted_edge_found():
    f = _frames(bonus=0.01)
    L = legs(f["bm"], f["op"], f["mom"], f["ff"])
    c, mkt, _ = candidates(L)
    assert (c["P1 Momentum big"] < L["P1 Momentum big"]).all()
    s = stats(c["P1 Momentum big"], mkt)
    assert s["diff"] > 0.03 and s["t"] > 2


def test_report_runs_and_selects():
    d, u = _frames(), _frames(n=700, start="1963-07")
    frames = {"dev_bm": d["bm"], "dev_op": d["op"], "dev_mom": d["mom"], "dev_ff": d["ff"],
              "us_bm": u["bm"], "us_op": u["op"], "us_mom": u["mom"], "us_ff": u["ff"]}
    di = pd.bdate_range("2009-10-01", "2026-09-30")
    rng = np.random.default_rng(1)
    px = lambda: pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(di)))), index=di)
    eur = {"MSCI World (EUNL)": px(), "World Momentum (IS3R)": px(), "World Quality (IS3Q)": px(),
           "US Small Cap Value (ZPRV)": px(), "World Value (IS3S)": pd.Series(dtype=float)}
    rep = run_experiment56_report(frames, {k: "x" for k in frames}, eur, {})
    assert "Blind selection" in rep and "OUT-OF-SAMPLE 2011→" in rep and "Equal-weight ETF mix" in rep
    assert "Benchmark MSCI World (URTH): no data" in rep
