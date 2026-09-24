"""
Tests for experiment #32: decades of history (parsers + pure analysis).
"""
import json
import numpy as np
import pandas as pd

from src.backtest.experiments_32 import (
    parse_stooq_csv, parse_yahoo_json, perf, sma_filter_returns, tsmom_returns,
    trend_comparison, run_experiment32_report,
)

IDX = lambda n: pd.bdate_range("1990-01-01", periods=n)


def test_parse_stooq_csv():
    txt = "Date,Open,High,Low,Close,Volume\n2020-01-02,1,2,0.5,1.5,100\n2020-01-03,1,2,0.5,1.7,100\n"
    s = parse_stooq_csv(txt)
    assert list(s.values) == [1.5, 1.7]
    assert parse_stooq_csv("No data").empty


def test_parse_yahoo_json():
    j = {"chart": {"result": [{"timestamp": [1577923200, 1578009600],
                               "indicators": {"quote": [{"close": [10.0, 11.0]}],
                                              "adjclose": [{"adjclose": [9.5, 10.5]}]}}]}}
    s = parse_yahoo_json(json.dumps(j))
    assert list(s.values) == [9.5, 10.5]
    assert parse_yahoo_json("not json").empty


def test_perf_basic():
    r = pd.Series([0.01] * 252, index=IDX(252))
    p = perf(r)
    assert p["cagr"] > 0.5 and p["maxdd"] == 0.0


def test_sma_filter_avoids_crash():
    # long rise then a long crash: the SMA filter should cut the drawdown
    up = np.linspace(100, 300, 1500)
    down = np.linspace(300, 90, 500)
    px = pd.Series(np.concatenate([up, down]), index=IDX(2000))
    bh = perf(px.pct_change().fillna(0.0))
    sma = perf(sma_filter_returns(px))
    assert sma["maxdd"] > bh["maxdd"]          # less negative = smaller drawdown


def test_tsmom_is_causal_and_finite():
    rng = np.random.default_rng(0)
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 1500))), index=IDX(1500))
    r = tsmom_returns(px)
    assert len(r) == len(px) and np.isfinite(r.to_numpy()).all()


def test_trend_comparison_shape():
    rng = np.random.default_rng(1)
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 1500))), index=IDX(1500))
    tc = trend_comparison(px, n_trials=10)
    assert {"bh", "sma", "ts", "rigor"} <= set(tc)


def test_report_structure_and_no_data():
    rng = np.random.default_rng(2)
    series = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, 3000))), index=IDX(3000))
    assets = [{"name": "Index A", "stooq": "a", "yahoo": "A"},
              {"name": "Missing", "stooq": "m", "yahoo": "M"}]
    fetch = lambda a: (series, "stooq") if a["name"] == "Index A" else (pd.Series(dtype=float), "none")
    rep = run_experiment32_report(fetch, assets)
    assert "Experiment #32" in rep
    assert "A — Deep-drawdown signal" in rep and "B — Trend filters" in rep
    assert "Summary A" in rep and "Summary B" in rep
    rep2 = run_experiment32_report(lambda a: (pd.Series(dtype=float), "none"), assets)
    assert "No long-history data" in rep2
