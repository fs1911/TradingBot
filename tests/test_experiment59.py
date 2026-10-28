import math

from src.backtest.experiments_59 import years_needed, implied_te, power, skilled_share, p_lag, run_experiment59_report


def test_years_formula():
    assert abs(years_needed(0.02, 0.06, 2.0) - 36) < 1e-9
    assert math.isinf(years_needed(0.0, 0.06))


def test_implied_te_roundtrip():
    te = implied_te(0.026, 3.01, 17)
    assert abs(0.026 * math.sqrt(17) / te - 3.01) < 1e-9


def test_power_and_bayes():
    assert abs(power(0.0, 0.06, 10) - 0.0228) < 1e-3
    assert power(0.02, 0.06, 30) > power(0.02, 0.06, 10)
    assert skilled_share(0.1, 0.02, 0.06, 10) < skilled_share(0.25, 0.02, 0.06, 10)
    assert abs(p_lag(0.0, 0.06, 5) - 0.5) < 1e-12


def test_report():
    r = run_experiment59_report()
    assert "Bonferroni" in r and "Bayes" in r and "Counterpoint" in r
