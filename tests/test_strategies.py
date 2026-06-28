"""Unit tests for all trading strategies."""
import pytest
import numpy as np
import pandas as pd

from src.indicators.technical import add_all_indicators
from src.strategies.ema_crossover import EMACrossoverStrategy
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from src.strategies.macd_momentum import MACDMomentumStrategy
from src.strategies.base_strategy import SignalType


PARAMS = {
    "fast_ema": 9, "slow_ema": 21, "signal_ema": 5,
    "volume_filter": True, "volume_multiplier": 1.2,
    "atr_period": 14, "sl_atr_multiplier": 1.5, "tp_atr_multiplier": 2.5,
    "confirmation_candles": 1,
    "rsi_period": 14, "oversold_threshold": 30, "overbought_threshold": 70,
    "extreme_oversold": 20, "extreme_overbought": 80,
    "ema_trend_filter": 50,
    "fast_period": 12, "slow_period": 26, "signal_period": 9,
    "min_histogram_magnitude": 0.001,
}


def make_trending_df(n=300, trend="up") -> pd.DataFrame:
    """Synthetic data with a clear up or down trend."""
    np.random.seed(99)
    drift = 0.003 if trend == "up" else -0.003
    returns = drift + np.random.randn(n) * 0.01
    close = 100 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(np.random.randn(n) * 0.003))
    low = close * (1 - np.abs(np.random.randn(n) * 0.003))
    vol = np.random.randint(500_000, 2_000_000, n).astype(float)
    idx = pd.date_range("2023-01-01", periods=n, freq="1h")
    df = pd.DataFrame({"open": close * 0.999, "high": high, "low": low,
                       "close": close, "volume": vol}, index=idx)
    return add_all_indicators(df, PARAMS).dropna()


def make_oversold_df(n=300) -> pd.DataFrame:
    """Synthetic data that dips then recovers (RSI test)."""
    np.random.seed(7)
    close = np.concatenate([
        100 + np.cumsum(np.random.randn(200) * 0.5),  # random walk
        np.linspace(100, 85, 50),                      # sharp drop → RSI oversold
        np.linspace(85, 95, 50),                       # recovery
    ])
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    vol = np.random.randint(300_000, 800_000, n).astype(float)
    idx = pd.date_range("2023-01-01", periods=n, freq="1h")
    df = pd.DataFrame({"open": close - 0.05, "high": high, "low": low,
                       "close": close, "volume": vol}, index=idx)
    return add_all_indicators(df, PARAMS).dropna()


class TestEMACrossover:
    def test_returns_list(self):
        df = make_trending_df()
        strat = EMACrossoverStrategy(PARAMS)
        signals = strat.generate_signals(df, "TEST")
        assert isinstance(signals, list)

    def test_signals_have_sl_tp(self):
        df = make_trending_df()
        strat = EMACrossoverStrategy(PARAMS)
        # Scan all windows for any signal
        for i in range(50, len(df)):
            signals = strat.generate_signals(df.iloc[:i], "TEST")
            for sig in signals:
                assert sig.stop_loss is not None
                assert sig.take_profit is not None
                if sig.signal == SignalType.LONG:
                    assert sig.stop_loss < df["close"].iloc[i - 1]
                    assert sig.take_profit > df["close"].iloc[i - 1]
                break

    def test_score_in_range(self):
        df = make_trending_df()
        strat = EMACrossoverStrategy(PARAMS)
        for i in range(50, len(df)):
            signals = strat.generate_signals(df.iloc[:i], "TEST")
            for sig in signals:
                assert 0.0 <= sig.score <= 1.0


class TestRSIMeanReversion:
    def test_returns_list(self):
        df = make_oversold_df()
        strat = RSIMeanReversionStrategy(PARAMS)
        signals = strat.generate_signals(df, "TEST")
        assert isinstance(signals, list)

    def test_score_in_range(self):
        df = make_oversold_df()
        strat = RSIMeanReversionStrategy(PARAMS)
        for i in range(60, len(df)):
            signals = strat.generate_signals(df.iloc[:i], "TEST")
            for sig in signals:
                assert 0.0 <= sig.score <= 1.0


class TestMACDMomentum:
    def test_needs_enough_history(self):
        df = make_trending_df(100)
        strat = MACDMomentumStrategy(PARAMS)
        signals = strat.generate_signals(df, "TEST")
        assert signals == []  # Not enough history for EMA200

    def test_strategy_name(self):
        strat = MACDMomentumStrategy(PARAMS)
        assert strat.name == "macd_momentum"

    def test_signal_direction_vs_trend(self):
        df = make_trending_df(300, trend="up")
        strat = MACDMomentumStrategy(PARAMS)
        all_signals = []
        for i in range(210, len(df)):
            all_signals.extend(strat.generate_signals(df.iloc[:i], "TEST"))
        if all_signals:
            # In an uptrend, should predominantly generate LONG signals
            longs = sum(1 for s in all_signals if s.signal == SignalType.LONG)
            assert longs >= len(all_signals) * 0.5
