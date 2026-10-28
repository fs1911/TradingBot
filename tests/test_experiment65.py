import math
import numpy as np
import pandas as pd

from src.backtest.experiments_65 import latest_change, market_light, colour, build_cohorts, run_experiment65_report


def test_latest_change_point_in_time():
    con = ({2019: (math.log(1.10), pd.Timestamp("2020-02-20"), 110.0)},
           [(pd.Timestamp("2020-03-31"), math.log(0.97), pd.Timestamp("2020-05-05"), 97.0)])
    assert math.isnan(latest_change(con, pd.Period("2020-01", "M")))
    assert abs(latest_change(con, pd.Period("2020-03", "M")) - 0.10) < 1e-12
    assert abs(latest_change(con, pd.Period("2020-05", "M")) + 0.03) < 1e-12


def test_colour_rules():
    assert colour(0.06, "green") == "red" and colour(0.0, "red") == "red"
    assert colour(0.0, "yellow") == "yellow" and colour(float("nan"), "green") == "yellow"
    assert colour(-0.03, "green") == "green"
    sc = pd.Series([3, 1, 1], index=pd.period_range("2020-01", periods=3, freq="M"))
    st = pd.Series([False, False, True], index=sc.index)
    assert market_light(sc, st).tolist() == ["green", "yellow", "red"]


def test_cohorts_and_report_planted_dilution_penalty():
    rng = np.random.default_rng(0)
    months = pd.period_range("2009-01", "2026-06", freq="M")
    n = 200
    tick = [f"T{i}" for i in range(n)]
    dil = rng.random(n) < 0.25
    rets = rng.normal(0.008, 0.06, (len(months), n)) - np.where(dil, 0.004, 0.0)
    px = pd.DataFrame(20 * np.cumprod(1 + rets, axis=0), index=months, columns=tick)
    concepts = {i: ({y: (math.log(1.08) if dil[i] else math.log(0.99), pd.Timestamp(f"{y+1}-02-15"), 1.0)
                     for y in range(2008, 2026)}, []) for i in range(n)}
    tmap = {i: tick[i] for i in range(n)}
    sc = pd.Series(3, index=months)
    sc[(months >= pd.Period("2020-03", "M")) & (months <= pd.Period("2020-06", "M"))] = 0
    light = market_light(sc, pd.Series(True, index=months))
    d = build_cohorts(concepts, tmap, px, light, pd.period_range("2010-01", "2024-12", freq="M"))
    assert set(d["colour"]) == {"green", "red"}
    assert d.loc[d["colour"] == "red", "excess"].mean() < d.loc[d["colour"] == "green", "excess"].mean()
    rep = run_experiment65_report(d, light)
    assert "Component 1" in rep and "Component 2" in rep and "🔴" in rep
