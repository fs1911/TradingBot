"""
Technical indicators library.

All functions accept a pd.DataFrame with OHLCV columns
(open, high, low, close, volume) and return the computed
Series or DataFrame. Columns are lowercase throughout.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


# ── Moving averages ───────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


# ── Oscillators ───────────────────────────────────────────────────────────────

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": histogram})


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> pd.DataFrame:
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
    d = k.rolling(d_period).mean()
    return pd.DataFrame({"k": k, "d": d})


# ── Volatility ────────────────────────────────────────────────────────────────

def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean()


def bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.DataFrame:
    mid = sma(close, period)
    std = close.rolling(period).std()
    return pd.DataFrame(
        {"upper": mid + std_dev * std, "mid": mid, "lower": mid - std_dev * std}
    )


# ── Volume ────────────────────────────────────────────────────────────────────

def vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    typical = (high + low + close) / 3
    return (typical * volume).cumsum() / volume.cumsum()


def daily_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """VWAP that resets each calendar day — correct for intraday bars."""
    typical = (high + low + close) / 3
    tp_vol = typical * volume
    result = pd.Series(np.nan, index=close.index)
    dates = pd.Series(close.index.date, index=close.index)
    for d in dates.unique():
        mask = dates == d
        cum_vol = volume[mask].cumsum()
        result[mask] = tp_vol[mask].cumsum() / cum_vol.replace(0, np.nan)
    return result


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
    return sma(volume, period)


# ── Trend strength ────────────────────────────────────────────────────────────

def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.DataFrame:
    atr_val = atr(high, low, close, period)
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=close.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=close.index,
    )

    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = ema(dx, period)

    return pd.DataFrame({"adx": adx_val, "plus_di": plus_di, "minus_di": minus_di})


# ── Composite signal helpers ──────────────────────────────────────────────────

def add_all_indicators(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Compute and attach all indicators to a single OHLCV DataFrame."""
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    df["ema_fast"] = ema(c, params.get("fast_ema", 9))
    df["ema_slow"] = ema(c, params.get("slow_ema", 21))
    df["ema_50"] = ema(c, 50)
    df["ema_200"] = ema(c, 200)
    df["sma_20"] = sma(c, 20)

    df["rsi"] = rsi(c, params.get("rsi_period", 14))

    macd_df = macd(c, params.get("fast_period", 12), params.get("slow_period", 26), params.get("signal_period", 9))
    df["macd"] = macd_df["macd"]
    df["macd_signal"] = macd_df["signal"]
    df["macd_hist"] = macd_df["histogram"]

    df["atr"] = atr(h, l, c, params.get("atr_period", 14))
    df["vol_sma"] = volume_sma(v)

    bb = bollinger_bands(c)
    df["bb_upper"] = bb["upper"]
    df["bb_mid"] = bb["mid"]
    df["bb_lower"] = bb["lower"]

    stoch = stochastic(h, l, c)
    df["stoch_k"] = stoch["k"]
    df["stoch_d"] = stoch["d"]

    df["vwap"] = daily_vwap(h, l, c, v)
    df["obv"] = obv(c, v)

    adx_df = adx(h, l, c)
    df["adx"] = adx_df["adx"]
    df["adx_plus_di"] = adx_df["plus_di"]
    df["adx_minus_di"] = adx_df["minus_di"]

    return df
