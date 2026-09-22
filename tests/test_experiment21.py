"""
Tests for experiment #21: momentum refinements.
"""
import numpy as np
import pandas as pd

from src.backtest.experiments_20 import build_price_panel
from src.backtest.experiments_21 import (
    score_momentum, score_volscaled_momentum, score_residual_momentum,
    vol_managed, regime_filtered, _equal_weight_index,
    run_experiment21_report,
)

IDX = lambda n: pd.date_range("2015-01-01", periods=n, freq="1D", tz="UTC")


def _df(closes):
    c = np.asarray(closes, float)
    n = len(c)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=IDX(n))


def _make_universe(n_syms=30, n_days=900, seed=0):
    rng = np.random.default_rng(seed)
    return {f"S{i:02d}": _df(np.maximum(100 + np.cumsum(rng.normal(0.02, 1.0, n_days)), 1.0))
            for i in range(n_syms)}


def test_volscaled_prefers_steady_trend():
    n = 400
    steady = _df(100 + np.arange(n) * 0.5)["close"]            # smooth uptrend
    rng = np.random.default_rng(1)
    choppy = _df(100 + np.arange(n) * 0.5 + np.cumsum(rng.normal(0, 3, n)))["close"]
    panel = pd.DataFrame({"STEADY": steady, "CHOPPY": choppy})
    sc = score_volscaled_momentum(panel)
    # same drift, but steady has far lower vol → higher risk-adjusted score
    assert sc["STEADY"] > sc["CHOPPY"]


def test_residual_momentum_shape_and_causality():
    data = _make_universe()
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100)
    sc = score_residual_momentum(panel)
    assert list(sc.index) == list(panel.columns)
    # short slice → all NaN (not enough history), never raises
    assert score_residual_momentum(panel.iloc[:50]).isna().all()


def test_vol_managed_targets_volatility_and_is_causal():
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0.0005, 0.02, 800), index=IDX(800))
    m = vol_managed(r, target_ann=0.10, window=126)
    assert len(m) == len(r)
    assert m.iloc[0] == 0.0                        # no leverage before window fills
    # realised annual vol of the managed series is near the 10% target
    ann = m.iloc[200:].std() * np.sqrt(252)
    assert 0.05 < ann < 0.20


def test_regime_filter_zeros_out_below_ma():
    n = 500
    # index crashes in the middle then recovers
    level = pd.Series(np.concatenate([np.linspace(100, 160, 250),
                                      np.linspace(160, 90, 125),
                                      np.linspace(90, 140, 125)]), index=IDX(n))
    r = pd.Series(0.01, index=IDX(n))
    f = regime_filtered(r, level, ma=200)
    assert (f <= r + 1e-12).all()                   # never adds exposure
    assert (f == 0.0).sum() > 0                      # some days filtered out
    assert (f != 0.0).sum() > 0                      # but not all


def test_equal_weight_index_monotone_for_uptrend():
    data = {f"S{i:02d}": _df(100 + np.arange(300) * (0.1 + 0.005 * i)) for i in range(25)}
    panel = build_price_panel(lambda s, tf, lim: data[s], list(data), min_len=100)
    idx = _equal_weight_index(panel)
    assert idx.iloc[-1] > idx.iloc[0]               # rises with the universe


def test_report_structure():
    data = _make_universe(n_syms=30, n_days=900)
    report = run_experiment21_report(
        get_ohlcv=lambda s, tf, lim: data.get(s, pd.DataFrame()),
        universe=list(data), limit=900,
    )
    assert "Experiment #21" in report
    for tag in ["Raw 12-1", "Vol-scaled", "Residual", "Vol-managed",
                "Regime-filtered", "Long-only"]:
        assert tag in report
    assert "Survivorship bias" in report
    assert "Summary" in report
