import numpy as np
import pandas as pd

from src.backtest.experiments_71_74_83 import (mix_returns, risk_stats, portfolio_spread, hmm_fit, hmm_filter,
                                               run_experiments71_74_83_report)


def test_rebalancing_rules():
    idx = pd.period_range("2000-01", periods=24, freq="M")
    s, b = pd.Series(0.02, index=idx), pd.Series(0.0, index=idx)
    never = mix_returns(s, b, 0.5, "never")
    monthly = mix_returns(s, b, 0.5, "monthly")
    assert abs(monthly.iloc[5] - 0.01) < 1e-12 and never.iloc[-1] > monthly.iloc[-1]
    assert risk_stats(monthly)["dd"] == 0


def test_spread_shrinks_with_n():
    w = np.random.default_rng(0).lognormal(0, 1, 5000)
    sp = portfolio_spread(w, sizes=(1, 50), n=5000)
    assert sp[0]["p95"] - sp[0]["p5"] > sp[1]["p95"] - sp[1]["p5"]


def test_hmm_recovers_two_regimes():
    rng = np.random.default_rng(1)
    states = np.repeat([0, 1, 0, 1, 0], 120)
    x = np.where(states == 0, rng.normal(0.01, 0.02, len(states)), rng.normal(-0.01, 0.08, len(states)))
    pi, A, mu, sd = hmm_fit(x, iters=60)
    assert sd[0] < sd[1] and A[0, 0] > 0.9
    p = hmm_filter(x, pi, A, mu, sd)
    assert ((p > 0.5) == (states == 0)).mean() > 0.85


def test_report():
    idx = pd.date_range("1900-01-01", periods=900, freq="MS")
    rng = np.random.default_rng(2)
    price = pd.Series(10 * np.exp(np.cumsum(rng.normal(0.004, 0.04, len(idx)))), index=idx)
    sh = pd.DataFrame({"price": price, "div": price * 0.04, "cpi": 100.0, "gs10": 4.0 + rng.normal(0, 0.1, len(idx))})
    rep = run_experiments71_74_83_report(sh)
    assert "#71" in rep and "#74" in rep and "hidden Markov" in rep and "10-month trend rule" in rep
