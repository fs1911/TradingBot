"""
Experiment #29 — funding rate as a froth gauge (a Finanzradar signal).

The funding rate is the perpetual's version of the basis and is reliably fetchable.
Economically it measures how crowded the leveraged-long side is: very high funding =
euphoric, over-leveraged longs (a classic contrarian "too hot" reading); negative
funding = fear/capitulation (a "cheap" reading). This tests whether that reading is a
real, usable signal — NOT a bot trade, but a clean input for the user's Finanzradar
Kaufen/Halten/Überhitzt light.

Two questions, per coin and combined:
  1. PREDICTIVE: bucket days by (trailing, smoothed) annualised funding and measure the
     mean forward `horizon`-day spot return per bucket. Contrarian if the top
     (high-funding) bucket has the lowest forward return.
  2. USABLE RULE: a causal long/flat filter — hold spot unless funding is in its top
     quantile (froth), then step aside — compared to buy & hold. If it lifts risk-
     adjusted return, it is a concrete rule the user can apply and encode.

Also emits the traffic-light thresholds (funding percentiles) for Finanzradar. Data
injected; fully causal.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

from .rigor import annualized_sharpe
from .experiments_24 import funding_to_daily_carry


def annualized_funding(funding: pd.Series, smooth: int = 7) -> pd.Series:
    """Daily funding summed per day, smoothed, annualised (×365). Positive = longs
    pay shorts = leveraged-long crowding."""
    daily = funding_to_daily_carry(funding)
    if len(daily) == 0:
        return pd.Series(dtype=float)
    return (daily.rolling(smooth, min_periods=1).mean() * 365.0).rename("ann_funding")


def froth_buckets(ann_funding: pd.Series, spot: pd.Series, horizon: int = 30,
                  n_buckets: int = 5) -> pd.DataFrame:
    """Mean forward `horizon`-day spot return by funding bucket (lagged → causal)."""
    df = pd.concat({"f": ann_funding.shift(1), "s": spot}, axis=1).dropna()
    if len(df) < horizon + 100:
        return pd.DataFrame()
    df["fwd"] = df["s"].shift(-horizon) / df["s"] - 1.0
    df = df.dropna()
    if len(df) < 100:
        return pd.DataFrame()
    try:
        df["b"] = pd.qcut(df["f"], n_buckets, labels=False, duplicates="drop")
    except ValueError:
        return pd.DataFrame()
    return df.groupby("b").agg(f_lo=("f", "min"), f_hi=("f", "max"),
                               fwd=("fwd", "mean"), n=("fwd", "size"))


def froth_filter_returns(ann_funding: pd.Series, spot: pd.Series,
                         window: int = 180, hot_q: float = 0.8):
    """Causal long/flat rule: hold spot unless trailing-percentile funding is in its
    top `hot_q` (froth), then step aside. Returns (strategy_daily, buyhold_daily)."""
    df = pd.concat({"f": ann_funding, "s": spot}, axis=1).dropna()
    if len(df) < window + 60:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    ret = df["s"].pct_change().fillna(0.0)
    pct = df["f"].rolling(window, min_periods=window // 2).apply(
        lambda x: (x.iloc[-1] >= np.nanpercentile(x, hot_q * 100)) * 1.0, raw=False)
    hot = pct.shift(1).fillna(0.0)               # yesterday's state → causal
    strat = ret.where(hot < 1.0, 0.0)            # step aside when hot
    return strat, ret


def run_experiment29_report(fetch_funding: Callable[[str], pd.Series],
                            fetch_prices: Callable[[str], pd.Series],
                            symbols: list[str], horizon: int = 30) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #29 — funding as a froth gauge (Finanzradar signal) "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"Funding = how crowded leveraged longs are. Tests whether high "
                 f"funding predicts lower forward {horizon}d returns (contrarian), and "
                 f"whether a 'step aside when hot' filter beats buy & hold. For "
                 f"Finanzradar, not a bot trade.")
    lines.append("")

    lines.append("## Predictive: forward return by funding bucket")
    lines.append("| Coin | low-funding fwd% | high-funding fwd% | contrarian? |")
    lines.append("|---|--:|--:|:--:|")
    contrarian = 0
    have = []
    filt_pairs = {}
    for sym in symbols:
        try:
            funding = fetch_funding(sym)
            spot = fetch_prices(sym)
        except Exception:
            funding = spot = None
        if funding is None or spot is None or len(funding) == 0 or len(spot) < 200:
            lines.append(f"| {sym} | — | — | no data |")
            continue
        annf = annualized_funding(funding)
        spot = pd.Series(spot).astype(float)
        spot.index = pd.to_datetime(spot.index)
        spot.index = spot.index.tz_localize(None) if spot.index.tz is not None else spot.index
        spot = spot.sort_index()
        annf.index = annf.index.tz_localize(None) if annf.index.tz is not None else annf.index
        b = froth_buckets(annf, spot, horizon)
        if b.empty:
            lines.append(f"| {sym} | — | — | short data |")
            continue
        have.append(sym)
        lo, hi = 100 * float(b["fwd"].iloc[0]), 100 * float(b["fwd"].iloc[-1])
        good = hi < lo
        contrarian += int(good)
        lines.append(f"| {sym} | {lo:+.1f} | {hi:+.1f} | {'✅ yes' if good else '❌ no'} |")
        filt_pairs[sym] = (annf, spot)
    lines.append("")

    if not have:
        lines.append("---")
        lines.append("**Summary:** no usable funding+price data — signal not testable here.")
        return "\n".join(lines)

    lines.append("## Usable rule: 'step aside when funding hot' vs buy & hold")
    lines.append("| Coin | B&H Sharpe | Filtered Sharpe | B&H ann% | Filtered ann% | better? |")
    lines.append("|---|--:|--:|--:|--:|:--:|")
    better = 0
    for sym, (annf, spot) in filt_pairs.items():
        strat, ret = froth_filter_returns(annf, spot)
        if len(strat) < 100:
            lines.append(f"| {sym} | — | — | — | — | — |")
            continue
        bh_s, f_s = annualized_sharpe(ret), annualized_sharpe(strat)
        bh_a, f_a = 100 * ret.mean() * 252, 100 * strat.mean() * 252
        win = f_s > bh_s
        better += int(win)
        lines.append(f"| {sym} | {bh_s:.2f} | {f_s:.2f} | {bh_a:+.0f} | {f_a:+.0f} | "
                     f"{'✅' if win else '❌'} |")
    lines.append("")

    lines.append("---")
    lines.append(
        f"**Summary:** high funding is a contrarian froth signal in {contrarian}/{len(have)} "
        f"coins; the 'step aside when hot' filter beats buy&hold (Sharpe) in {better}/"
        f"{len(filt_pairs)}. For Finanzradar: read annualised funding as a percentile — "
        "top quintile ≈ Überhitzt, middle ≈ Halten, negative/bottom ≈ Kaufen. This is a "
        "sentiment overlay, not a standalone forecast.")
    return "\n".join(lines)
