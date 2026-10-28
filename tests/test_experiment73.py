import numpy as np

from src.backtest.experiments_73 import plan, run_experiment73_report


def test_costs_reduce_wealth_and_zero_cost_matches_simple_sum():
    real = np.zeros(400)
    w = plan(real, 120, 100, 0, 0, 0, 0)
    assert np.allclose(w, 12000)
    w2 = plan(real, 120, 100, 0.01, 0, 0, 0)
    assert np.allclose(w2, 11880)
    r = np.full(400, 0.005)
    assert plan(r, 120, 100, 0, 0.01, 0, 0)[0] < plan(r, 120, 100, 0, 0, 0, 0)[0]
    assert plan(r, 120, 100, 0, 0, 1.0, 0.02)[0] < plan(r, 120, 100, 0, 0, 0, 0)[0]


def test_report():
    rep = run_experiment73_report(np.full(1800, 0.005))
    assert "Yuh" in rep and "What one percentage point costs" in rep
