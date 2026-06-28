"""Unit tests for technical indicators."""
import pytest
import numpy as np
import pandas as pd

from src.indicators.technical import (
    ema, sma, rsi, macd, atr, bollinger_bands, stochastic,
    volume_sma, adx, add_all_indicators,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    np.random.seed(42)
    n = 300
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    vol = np.random.randint(100_000, 500_000, n).astype(float)
    idx = pd.date_range("2023-01-01", periods=n, freq="1h")
    return pd.DataFrame({"open": close - 0.1, "high": high, "low": low,
                         "close": close, "volume": vol}, index=idx)


def test_ema_length(sample_df):
    result = ema(sample_df["close"], 20)
    assert len(result) == len(sample_df)


def test_ema_convergence(sample_df):
    # EMA should not contain NaN after the period
    result = ema(sample_df["close"], 20)
    assert not result.iloc[20:].isna().any()


def test_sma_values(sample_df):
    result = sma(sample_df["close"], 10)
    # Manual check: last SMA = mean of last 10 close prices
    expected = sample_df["close"].iloc[-10:].mean()
    assert abs(result.iloc[-1] - expected) < 1e-9


def test_rsi_bounds(sample_df):
    result = rsi(sample_df["close"], 14)
    valid = result.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_macd_columns(sample_df):
    result = macd(sample_df["close"])
    assert set(result.columns) == {"macd", "signal", "histogram"}
    assert not result["macd"].iloc[30:].isna().any()


def test_atr_positive(sample_df):
    result = atr(sample_df["high"], sample_df["low"], sample_df["close"], 14)
    assert (result.dropna() > 0).all()


def test_bollinger_bands_structure(sample_df):
    result = bollinger_bands(sample_df["close"], 20, 2.0).dropna()
    assert (result["upper"] > result["mid"]).all()
    assert (result["mid"] > result["lower"]).all()


def test_stochastic_bounds(sample_df):
    result = stochastic(sample_df["high"], sample_df["low"], sample_df["close"])
    valid_k = result["k"].dropna()
    assert (valid_k >= 0).all() and (valid_k <= 100).all()


def test_volume_sma(sample_df):
    result = volume_sma(sample_df["volume"], 20)
    assert len(result) == len(sample_df)


def test_adx_columns(sample_df):
    result = adx(sample_df["high"], sample_df["low"], sample_df["close"], 14)
    assert "adx" in result.columns
    assert "plus_di" in result.columns
    assert "minus_di" in result.columns


def test_add_all_indicators(sample_df):
    params = {"fast_ema": 9, "slow_ema": 21, "rsi_period": 14,
              "fast_period": 12, "slow_period": 26, "signal_period": 9, "atr_period": 14}
    result = add_all_indicators(sample_df.copy(), params)
    expected_cols = ["ema_fast", "ema_slow", "ema_50", "ema_200", "rsi",
                     "macd", "atr", "bb_upper", "bb_lower"]
    for col in expected_cols:
        assert col in result.columns, f"Missing column: {col}"
