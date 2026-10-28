import numpy as np
import pandas as pd

from src.backtest.experiments_61 import oos_r2, cell, nonoverlap, predictability_map, valuation_test, run_experiment61_report


def _slow_oos(r):
    x, y = r.to_numpy()[:-1], r.to_numpy()[1:]
    n = len(y); start = max(int(n / 3), 10); sm = sh = 0.0
    for t in range(start, n):
        b, a = np.polyfit(x[:t], y[:t], 1)
        sm += (y[t] - (a + b * x[t])) ** 2; sh += (y[t] - y[:t].mean()) ** 2
    return 1 - sm / sh


def test_fast_oos_matches_slow():
    r = pd.Series(np.random.default_rng(0).normal(0, 1, 300))
    assert abs(oos_r2(r) - _slow_oos(r)) < 1e-9


def test_planted_ar_found_noise_not():
    rng = np.random.default_rng(1)
    e = rng.normal(0, 1, 2000); x = np.zeros(2000)
    for i in range(1, 2000):
        x[i] = 0.3 * x[i - 1] + e[i]
    c = cell(pd.Series(x))
    assert c["t"] > 8 and c["oos"] > 0.05
    c0 = cell(pd.Series(rng.normal(0, 1, 2000)))
    assert abs(c0["t"]) < 3.5 and c0["oos"] < 0.01


def test_map_and_valuation_and_report():
    d = pd.bdate_range("1990-01-01", "2024-12-31")
    rng = np.random.default_rng(2)
    prices = {"A": pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(d)))), index=d)}
    m = predictability_map(prices)
    assert set(m["A"]) == {"1 day", "1 week", "1 month", "3 months", "12 months"}
    assert len(nonoverlap(np.log(prices["A"]), 21)) > 400
    idx = pd.date_range("1881-01-01", "2023-12-01", freq="MS")
    price = pd.Series(10 * np.exp(np.cumsum(rng.normal(0.004, 0.04, len(idx)))), index=idx)
    sh = pd.DataFrame({"price": price, "div": price * 0.04, "cpi": np.linspace(10, 300, len(idx)),
                       "cape": 15 * np.exp(rng.normal(0, 0.2, len(idx)))})
    rows = valuation_test(sh)
    assert {r["h"] for r in rows} == {1, 5, 10} and all(r["n_oos"] > 50 for r in rows if r["h"] == 1)
    rep = run_experiment61_report(prices, sh)
    assert "OOS R²" in rep and "Valuation predicts" in rep and "#60" in rep
