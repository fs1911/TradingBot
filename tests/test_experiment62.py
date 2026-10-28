import numpy as np
import pandas as pd

from src.backtest.experiments_62 import (FEATURES, build_panel, ridge_fit, ridge_predict, gbm_fit, gbm_predict,
                                         walk_forward, rank_ic, run_experiment62_report)


def test_gbm_learns_nonlinear_and_ridge_linear():
    rng = np.random.default_rng(0)
    X = rng.random((4000, 3))
    y = np.where(X[:, 0] > 0.7, 1.0, 0.0) + 0.1 * rng.normal(size=4000)
    m = gbm_fit(X, y, n_trees=80)
    p = gbm_predict(m, X)
    assert np.corrcoef(p, y)[0, 1] > 0.9
    w = ridge_fit(X, 2 * X[:, 1], lam=1e-6)
    assert abs(w[2] - 2) < 1e-3


def _synthetic(years=range(2009, 2024), n=300, edge=0.04, seed=1):
    rng = np.random.default_rng(seed)
    tick = [f"T{i}" for i in range(n)]
    months = pd.period_range("2009-01", "2026-06", freq="M")
    bb = {y: pd.Series(rng.normal(0, 0.05, n), index=tick) for y in years}
    comp = {y: pd.DataFrame({"gross_profitability": rng.random(n), "roe": rng.random(n), "low_accruals": rng.random(n),
                             "low_leverage": rng.random(n), "assets": np.exp(rng.normal(22, 1, n))}, index=tick)
            for y in years}
    rets = pd.DataFrame(rng.normal(0.008, 0.06, (len(months), n)), index=months, columns=tick)
    for y in years:                         # planted: buybacks earn `edge` p.a. over the next 12 months
        form = pd.Period(f"{y + 1}-06", "M")
        r = bb[y].rank(pct=True) - 0.5
        for m in pd.period_range(form + 1, form + 12, freq="M"):
            if m in rets.index:
                rets.loc[m] += edge / 12 * 2 * r.to_numpy()
    px = (1 + rets).cumprod() * 20
    return comp, bb, px, rets


def test_panel_point_in_time_and_report():
    comp, bb, px, rets = _synthetic()
    p = build_panel(comp, bb, px, rets)
    assert set(f + "_r" for f in FEATURES) <= set(p.columns) and p["year"].nunique() >= 10
    preds = walk_forward(p)
    assert min(preds["M1 ridge"]["year"]) >= min(p["year"]) + 5
    ic_bb = rank_ic(preds["H1 buybacks"], p)
    assert ic_bb.mean() > 0.05
    ic_pl = rank_ic(preds["P placebo (shuffled)"], p)
    assert abs(ic_pl.mean()) < ic_bb.mean()
    rep = run_experiment62_report(p, px, rets)
    assert "M2 boosted trees" in rep and "placebo" in rep and "human rule" in rep
