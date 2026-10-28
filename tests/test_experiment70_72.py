import numpy as np
import pandas as pd

from src.backtest.experiments_70_72 import real_series, lump_vs_staged, retirement, run_experiments70_72_report


def _shiller(n=1200, mu=0.006, sd=0.04, seed=0):
    idx = pd.date_range("1900-01-01", periods=n, freq="MS")
    rng = np.random.default_rng(seed)
    price = pd.Series(10 * np.exp(np.cumsum(rng.normal(mu, sd, n))), index=idx)
    return pd.DataFrame({"price": price, "div": price * 0.03, "cpi": 100.0, "gs10": 4.0, "cape": 15.0})


def test_lump_wins_in_rising_market_and_equal_without_returns():
    r = real_series(_shiller(mu=0.01, sd=0.0001))
    assert (lump_vs_staged(r, 12) > 1).all()
    z = r.copy(); z[:] = 0.0
    assert np.allclose(lump_vs_staged(z, 12), 1.0)


def test_retirement_math():
    r = real_series(_shiller(sd=0.0001, mu=0.0))
    r["stock"] = 0.0; r["bond"] = 0.0
    succ, worst, med, fails = retirement(r, 1.0, 0.03)
    assert succ == 1.0 and abs(med - (1 - 30 * 0.03)) < 1e-9      # no returns: 30 × 3 % = 90 % → 10 % left
    succ4, *_ = retirement(r, 1.0, 0.04)
    assert succ4 == 0.0                                          # 30 × 4 % = 120 % → runs out


def test_report():
    rep = run_experiments70_72_report(_shiller())
    assert "Lump sum" in rep and "Retirement" in rep and "60/40" in rep
