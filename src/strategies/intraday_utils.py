"""
Shared helpers for intraday / session-based strategies (ORB, Judas, Bullet).

These setups are anchored to session-open times in UTC. The OHLCV DataFrame
carries a datetime index (tz-aware UTC from the broker; we tolerate tz-naive
by assuming UTC). All times below are UTC minutes-of-day (hour*60 + minute).

NOTE: on 5-minute bars these are faithful but coarse approximations of setups
that purists trade on 1–5m charts. Honest caveat, documented in each strategy.
"""
from __future__ import annotations
import pandas as pd

# Session opens in UTC minutes-of-day
LONDON_OPEN = 7 * 60          # 07:00 UTC
NEW_YORK_OPEN = 13 * 60 + 30  # 13:30 UTC (US equities open / NY session)


def _utc_minutes(idx: pd.DatetimeIndex) -> pd.Series:
    """Minutes-of-day (UTC) for every bar in the index."""
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    return pd.Series(idx.hour * 60 + idx.minute, index=idx)


def session_bars(df: pd.DataFrame, open_minute: int) -> pd.DataFrame:
    """Return the current day's bars from `open_minute` (UTC) up to the latest
    bar. 'Current day' = the calendar date of the most recent bar."""
    if df.empty:
        return df
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    mins = idx.hour * 60 + idx.minute
    last_date = idx[-1].date()
    mask = (idx.date == last_date) & (mins >= open_minute)
    return df[mask]


def bar_minute(df: pd.DataFrame) -> int:
    """UTC minute-of-day of the latest bar."""
    ts = df.index[-1]
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.hour * 60 + ts.minute


def in_window(df: pd.DataFrame, start_min: int, end_min: int) -> bool:
    """Is the latest bar within [start_min, end_min) UTC minutes-of-day?"""
    m = bar_minute(df)
    return start_min <= m < end_min
