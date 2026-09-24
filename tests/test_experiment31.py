"""
Tests for experiment #31: stress test of the deep-drawdown signal.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_30 import drawdown_from_ath
from src.backtest.experiments_31 import (
    drawdown_episodes, welch_t, zone_stats, dca_vs_dip_reserve,
    run_experiment31_report,
)

IDX = lambda n: pd.date_range("2016-01-01", periods=n, freq="1D", tz="UTC")


def _crash_recover(n_cycles=3, up=300, down=120, rec=200):
    """Rising asset with repeated −50% crashes that fully recover."""
    vals, level = [], 100.0
    for _ in range(n_cycles):
        vals += list(np.linspace(level, level * 1.6, up))
        peak = level * 1.6
        vals += list(np.linspace(peak, peak * 0.5, down))
        vals += list(np.linspace(peak * 0.5, peak * 1.05, rec))
        level = peak * 1.05
    return pd.Series(vals, index=IDX(len(vals)))


def test_episodes_counts_independent_crashes():
    px = _crash_recover(n_cycles=3)
    eps = drawdown_episodes(drawdown_from_ath(px), enter=-0.35, reset=-0.10)
    assert len(eps) == 3          # one entry per crash, re-armed after recovery


def test_episodes_not_rearmed_without_recovery():
    dd = pd.Series([0, -0.4, -0.2, -0.4, -0.5, -0.05, -0.4], index=IDX(7))
    assert len(drawdown_episodes(dd, -0.35, -0.10)) == 2


def test_welch_t_sign_and_guard():
    assert welch_t([5, 6, 7, 8], [1, 2, 3, 2]) > 0
    assert np.isnan(welch_t([1], [1, 2]))


def test_zone_stats_positive_excess_on_crash_recover():
    st = zone_stats(_crash_recover(n_cycles=4), horizon=60)
    assert st["episodes"] == 4
    assert st["zone_days"] > 0
    assert st["excess"] > 0       # buying deep dips beat the ordinary return here


def test_zone_never_reached_for_calm_asset():
    n = 900
    px = pd.Series(100 + np.arange(n) * 0.1, index=IDX(n))
    st = zone_stats(px, horizon=90)
    assert st["zone_days"] == 0 and st["episodes"] == 0


def test_dca_vs_dip_reserve_finite_and_dip_helps_on_v_crash():
    dca, dip = dca_vs_dip_reserve(_crash_recover(n_cycles=3))
    assert np.isfinite(dca) and np.isfinite(dip)
    assert dip > dca


def test_report_structure_and_no_data():
    data = {"BTC/USD": _crash_recover(4), "SPY": pd.Series(100 + np.arange(900) * 0.1,
                                                            index=IDX(900))}
    rep = run_experiment31_report(lambda s: data.get(s), ["BTC/USD", "SPY", "MISSING"],
                                  horizon=60)
    assert "Experiment #31" in rep
    assert "never reached" in rep            # SPY-like calm asset
    assert "dip-reserve" in rep
    assert "Summary" in rep
