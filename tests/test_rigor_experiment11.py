"""
Tests for the strong rigor battery and experiment #11 strategies.
"""
import numpy as np
import pandas as pd

from src.backtest.rigor import (
    annualized_sharpe, t_stat, block_bootstrap_pvalue, deflated_ok,
    subperiod_stability, full_rigor,
)
from src.backtest.experiments_11 import (
    seasonality_returns, lead_lag_returns, weekday_returns, run_experiment11_report,
)

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def test_sharpe_and_tstat_signs():
    up = pd.Series(np.full(500, 0.001), index=IDX(500))
    assert annualized_sharpe(up) > 0 and t_stat(up) > 0
    flat = pd.Series(np.zeros(500), index=IDX(500))
    assert annualized_sharpe(flat) == 0.0


def test_bootstrap_pvalue_low_for_strong_positive_high_for_noise():
    rng = np.random.default_rng(0)
    strong = pd.Series(rng.normal(0.002, 0.005, 1000), index=IDX(1000))   # clearly positive
    noise = pd.Series(rng.normal(0.0, 0.01, 1000), index=IDX(1000))       # zero mean
    assert block_bootstrap_pvalue(strong) < 0.05
    assert block_bootstrap_pvalue(noise) > 0.10


def test_deflated_haircut_is_stricter():
    # p=0.03 passes at alpha=0.05 with 1 trial, fails with 20 trials
    assert deflated_ok(0.03, 1) is True
    assert deflated_ok(0.03, 20) is False


def test_subperiod_counts_positive_thirds():
    up = pd.Series(np.full(900, 0.001), index=IDX(900))
    parts, pos = subperiod_stability(up, 3)
    assert len(parts) == 3 and pos == 3


def test_full_rigor_flags_noise_as_no_edge():
    rng = np.random.default_rng(1)
    noise = pd.Series(rng.normal(0.0, 0.01, 1200), index=IDX(1200))
    res = full_rigor("noise", noise, n_trials=20)
    assert res["verdict"].startswith("❌")


def test_seasonality_and_weekday_are_causal_and_run():
    rng = np.random.default_rng(2)
    df = _df(100 + np.cumsum(rng.normal(0, 1, 1500)))
    s = seasonality_returns(df)
    w = weekday_returns(df)
    assert isinstance(s, pd.Series) and len(s) == 1500
    assert isinstance(w, pd.Series) and len(w) == 1500


def test_lead_lag_runs():
    rng = np.random.default_rng(3)
    a = _df(100 + np.cumsum(rng.normal(0, 1, 800)))
    b = _df(100 + np.cumsum(rng.normal(0, 1, 800)))
    r = lead_lag_returns(a, b)
    assert not r.empty


def test_experiment11_report_wellformed():
    rng = np.random.default_rng(4)
    data = {s: _df(100 + np.cumsum(rng.normal(0, 1, 1000))) for s in ["UNG", "CPER", "SPY", "BTC/USD"]}
    report = run_experiment11_report(
        get_ohlcv=lambda sym, tf, limit: data.get(sym, pd.DataFrame()),
        seasonality_symbols=["UNG"],
        lead_lag_pairs=[("CPER", "SPY")],
        term_structure=None,
        weekday_symbols=["BTC/USD"],
    )
    assert "Experiment #11" in report
    assert "p-value" in report
    assert "Summary" in report
