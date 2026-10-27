import numpy as np
import pandas as pd

from src.backtest.experiments_57 import (corrections, deflated_sharpe, pbo_cscv, trend_grid, one_sided_p,
                                         run_experiment57_report)


def test_corrections_counts_unreported_trials():
    p = np.array([1e-6, 0.001, 0.02, 0.5])
    c = corrections(p, m=4)
    assert c["bonferroni"].tolist() == [True, True, False, False]
    c2 = corrections(p, m=270)
    assert c2["bonferroni"].tolist() == [True, False, False, False]
    assert c2["bh"].sum() >= c2["bonferroni"].sum()


def test_one_sided_p_direction():
    assert abs(one_sided_p("t", 1.96) - 0.025) < 1e-3
    assert one_sided_p("t", -3.0) > 0.99


def test_deflated_sharpe_falls_with_trials():
    a = deflated_sharpe(0.8, 30, 10, 0.3)
    b = deflated_sharpe(0.8, 30, 1000, 0.3)
    assert 0 <= b < a <= 1


def test_pbo_noise_vs_real_ranking():
    rng = np.random.default_rng(0)
    noise = pd.DataFrame(rng.normal(0, 0.04, (480, 20)))
    real = noise.copy()
    real[0] += 0.03                       # one strategy truly better
    assert 0.25 < pbo_cscv(noise)["pbo"] < 0.75
    assert pbo_cscv(real)["pbo"] < 0.1


def test_trend_grid_and_report():
    idx = pd.period_range("1950-01", periods=600, freq="M")
    rng = np.random.default_rng(1)
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.006, 0.04, 600))), index=idx)
    g = trend_grid(px, pd.Series(0.003, index=idx))
    assert g.shape[1] == 34
    rep = run_experiment57_report({"S&P trend grid": g})
    assert "Benjamini" in rep and "S&P trend grid" in rep and "Control" in rep
