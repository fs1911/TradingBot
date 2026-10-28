import numpy as np
import pandas as pd

from src.backtest.experiments_82 import tail_counts, skip_days, cagr, clustering, run_experiment82_report


def test_tails_normal_vs_fat():
    rng = np.random.default_rng(0)
    d = pd.bdate_range("1960-01-01", periods=15000)
    normal = pd.Series(rng.normal(0, 0.01, len(d)), index=d)
    fat = pd.Series(rng.standard_t(3, len(d)) * 0.006, index=d)
    tn, tf = tail_counts(normal), tail_counts(fat)
    assert tn[2]["obs_all"] <= 3 and tf[2]["obs_all"] > 20      # 5 σ
    assert skip_days(fat, 10, "best") < cagr(fat) < skip_days(fat, 10, "worst")


def test_clustering_and_report():
    d = pd.bdate_range("2000-01-01", periods=3000)
    r = pd.Series(0.0005, index=d)
    r.iloc[1000:1010:2] = 0.08; r.iloc[1001:1011:2] = -0.08
    assert clustering(r, n=5) == 5
    px = 100 * (1 + r).cumprod()
    rep = run_experiment82_report({"Test": px})
    assert "fat tails" in rep.lower() and "RANDOM" in rep
