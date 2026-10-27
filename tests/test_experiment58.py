import numpy as np
import pandas as pd

from src.backtest.experiments_58 import (coin_gurus, managers, stock_market, pickers, wealth_concentration,
                                         empirical, run_experiment58_report)


def test_coin_gurus_spread():
    g = coin_gurus(n_sims=300)
    assert 0.55 < g["best_median"] < 0.70 and 0.30 < g["worst_median"] < 0.45


def test_managers_luck_produces_streaks():
    m = managers(n=5000)
    assert m["beat_5_in_row_first5"] > 0 and m["t10_gt_2"] > 0 and m["share_behind_after_15y"] > 0.5


def test_market_calibrated_and_skewed():
    sm = stock_market(n_stocks=4000)
    assert 2.5 < sm["market_multiple"] < 5.5
    wc = wealth_concentration(sm["w"], sm["tbill_multiple"])
    assert wc["share_below_tbill"] > 0.5 and wc["top_share_all_net_wealth"] < 0.3
    pk = pickers(sm["w"], n=5000)
    assert pk[1]["lost"] > pk[20]["lost"]


def test_empirical_and_report():
    idx = pd.bdate_range("2009-01-01", "2021-01-01")
    rng = np.random.default_rng(3)
    prices = {f"S{i}": pd.Series(10 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, len(idx)))), index=idx)
              for i in range(80)}
    e = empirical(prices, n=2000)
    assert e["n_stocks"] == 80
    rep = run_experiment58_report(prices, prices["S0"])
    assert "Coin-flip" in rep and "Reality check" in rep and "random 5-stock" in rep


def test_empirical_drops_artefacts():
    idx = pd.bdate_range("2009-01-01", "2021-01-01")
    base = {f"S{i}": pd.Series(np.linspace(10, 30, len(idx)), index=idx) for i in range(60)}
    base["PENNY"] = pd.Series(np.linspace(0.01, 50, len(idx)), index=idx)
    e = empirical(base, n=500)
    assert e["n_stocks"] == 60 and e["best_multiple"] < 1000
