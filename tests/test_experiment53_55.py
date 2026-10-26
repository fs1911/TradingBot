import numpy as np
import pandas as pd

from src.backtest.experiments_53_55 import (crash_events, simulate, trend_score_m, plan_wealth,
                                            shiller_monthly, run_experiments53_55_report)


def test_crash_events_once_per_episode():
    lvl = pd.Series([100, 90, 75, 70, 80, 101, 70, 60], index=pd.period_range("2000-01", periods=8, freq="M"))
    ev = crash_events(lvl, -0.20)
    assert ev == [pd.Period("2000-03", "M"), pd.Period("2000-07", "M")]


def test_same_money_in_all_rules_without_returns():
    idx = pd.period_range("2000-01", periods=120, freq="M")
    tr = pd.Series(0.0, index=idx)
    cash = pd.Series(0.0, index=idx)
    lvl = pd.Series(np.linspace(100, 50, 120), index=idx)   # deep drawdown
    sc = trend_score_m(lvl, cash)
    for r in ("DCA", "R20", "R30", "RTR"):
        assert abs(simulate(tr, cash, lvl, sc, r) - 120) < 1e-9


def test_plan_wealth_fees_hurt():
    real = pd.Series(0.005, index=pd.period_range("1900-01", periods=600, freq="M"))
    a, b = plan_wealth(real, 360, 500, 0.002), plan_wealth(real, 360, 500, 0.02)
    assert (a > b).all() and a[0] > 500 * 360


def test_report_runs():
    idx = pd.date_range("1900-01-01", periods=1500, freq="MS")
    rng = np.random.default_rng(2)
    price = pd.Series(10 * np.exp(np.cumsum(rng.normal(0.004, 0.045, len(idx)))), index=idx)
    sh = pd.DataFrame({"price": price, "div": price * 0.03, "cpi": np.linspace(10, 300, len(idx)), "gs10": 4.0})
    assert not shiller_monthly(sh).empty
    d = pd.bdate_range("1990-01-01", "2024-12-31")
    mk = {"Test": (pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(d)))), index=d), False)}
    irx = pd.Series(3.0, index=d)
    rep = run_experiments53_55_report(sh, mk, irx)
    assert "#53" in rep and "#54" in rep and "#55" in rep and "30 years, fee 2.0 %" in rep
