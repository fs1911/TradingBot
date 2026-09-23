"""
Experiment #30 — valuation gauges for Finanzradar (drawdown-from-ATH & 200d MA).

Funding failed as a froth signal (#29). This tests the classic, human-readable
valuation logic instead — the "buy when it bleeds / beware when extended" idea — on
the reliable native daily-price path (broker OHLCV, NO ccxt, so it cannot hang the bot
like #28 did). Two contrarian gauges per asset:

  1. Drawdown from all-time-high: deep drawdown = "cheap". Does a deeper drawdown
     predict HIGHER forward `horizon`-day returns?
  2. Distance from the 200-day moving average: far below = "cheap", far above =
     "extended". Does being far below predict higher forward returns (and far above
     lower)?

For each asset it buckets days by the gauge and reports the mean forward return per
bucket, then pools across assets and emits concrete Kaufen/Halten/Überhitzt bands.
This is a valuation OVERLAY for Finanzradar, not a bot trade — a rigor pass here means
"cheap historically preceded better forward returns", which is a genuinely usable
sentiment read, honestly reported if it is weak. Pure/causal, injected for CI.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd


def drawdown_from_ath(prices: pd.Series) -> pd.Series:
    """price / running-max − 1 (≤ 0). 0 = at all-time-high, −0.5 = 50% below."""
    p = pd.Series(prices).astype(float).dropna()
    return (p / p.cummax() - 1.0).rename("dd")


def dist_from_ma(prices: pd.Series, ma: int = 200) -> pd.Series:
    """price / MA(ma) − 1. Positive = above the average (extended), negative = below."""
    p = pd.Series(prices).astype(float).dropna()
    return (p / p.rolling(ma).mean() - 1.0).rename("dist")


def _bucket_forward(signal: pd.Series, prices: pd.Series, horizon: int,
                    n_buckets: int = 5) -> pd.DataFrame:
    """Mean forward `horizon`-day return per bucket of `signal` (buckets ascending:
    bucket 0 = lowest signal = cheapest for both gauges)."""
    df = pd.concat({"sig": signal, "px": pd.Series(prices).astype(float)}, axis=1).dropna()
    if len(df) < horizon + 120:
        return pd.DataFrame()
    df["fwd"] = df["px"].shift(-horizon) / df["px"] - 1.0
    df = df.dropna()
    if len(df) < 120:
        return pd.DataFrame()
    try:
        df["b"] = pd.qcut(df["sig"], n_buckets, labels=False, duplicates="drop")
    except ValueError:
        return pd.DataFrame()
    return df.groupby("b").agg(sig_lo=("sig", "min"), sig_hi=("sig", "max"),
                               fwd=("fwd", "mean"), n=("fwd", "size"))


def run_experiment30_report(fetch_prices: Callable[[str], pd.Series],
                            symbols: list[str], horizon: int = 90,
                            limit: int = 2500) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #30 — valuation gauges for Finanzradar "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"Contrarian valuation: does 'cheap' (deep drawdown / far below the "
                 f"200d MA) predict higher forward {horizon}-day returns? Native daily "
                 f"prices. A read for Finanzradar, not a bot trade.")
    lines.append("")

    dd_pool, ma_pool = [], []
    dd_hits = ma_hits = dd_n = ma_n = 0

    lines.append("## Drawdown from ATH — forward return by depth")
    lines.append("| Asset | deepest-DD bucket fwd% | near-ATH bucket fwd% | contrarian? |")
    lines.append("|---|--:|--:|:--:|")
    for sym in symbols:
        try:
            px = fetch_prices(sym)
        except Exception:
            px = None
        if px is None or len(px) < 400:
            lines.append(f"| {sym} | — | — | no data |")
            continue
        px = pd.Series(px).astype(float)
        px.index = pd.to_datetime(px.index)
        px.index = px.index.tz_localize(None) if px.index.tz is not None else px.index
        px = px.sort_index()
        b = _bucket_forward(drawdown_from_ath(px), px, horizon)
        if b.empty:
            lines.append(f"| {sym} | — | — | short data |")
            continue
        dd_n += 1
        cheap = 100 * float(b["fwd"].iloc[0])     # bucket 0 = deepest drawdown
        rich = 100 * float(b["fwd"].iloc[-1])     # last = near ATH
        good = cheap > rich
        dd_hits += int(good)
        dd_pool.append((drawdown_from_ath(px), px))
        lines.append(f"| {sym} | {cheap:+.1f} | {rich:+.1f} | {'✅ yes' if good else '❌ no'} |")
    lines.append("")

    lines.append("## Distance from 200d MA — forward return by level")
    lines.append("| Asset | far-below bucket fwd% | far-above bucket fwd% | contrarian? |")
    lines.append("|---|--:|--:|:--:|")
    for sym in symbols:
        try:
            px = fetch_prices(sym)
        except Exception:
            px = None
        if px is None or len(px) < 400:
            continue
        px = pd.Series(px).astype(float)
        px.index = pd.to_datetime(px.index)
        px.index = px.index.tz_localize(None) if px.index.tz is not None else px.index
        px = px.sort_index()
        b = _bucket_forward(dist_from_ma(px), px, horizon)
        if b.empty:
            continue
        ma_n += 1
        below = 100 * float(b["fwd"].iloc[0])
        above = 100 * float(b["fwd"].iloc[-1])
        good = below > above
        ma_hits += int(good)
        ma_pool.append((dist_from_ma(px), px))
        lines.append(f"| {sym} | {below:+.1f} | {above:+.1f} | {'✅ yes' if good else '❌ no'} |")
    lines.append("")

    # pooled traffic-light bands from the drawdown gauge
    if dd_pool:
        allsig = pd.concat([s for s, _ in dd_pool])
        allfwd = pd.concat([(p.shift(-horizon) / p - 1.0) for _, p in dd_pool])
        pooled = pd.concat({"dd": allsig, "fwd": allfwd}, axis=1).dropna()
        lines.append(f"## Finanzradar bands (pooled drawdown, {len(pooled)} obs)")
        lines.append("| Zustand | Drawdown-Band | Ø Folge-Rendite (90T) |")
        lines.append("|---|---|--:|")
        bands = [("🟢 Kaufen", pooled["dd"] <= -0.35),
                 ("🟡 Halten", (pooled["dd"] > -0.35) & (pooled["dd"] <= -0.10)),
                 ("🔴 Überhitzt", pooled["dd"] > -0.10)]
        for name, mask in bands:
            seg = pooled.loc[mask, "fwd"]
            rng = ("≤ −35%" if "Kaufen" in name else
                   "−35% … −10%" if "Halten" in name else "> −10% (nahe ATH)")
            lines.append(f"| {name} | {rng} | {100*seg.mean():+.1f}% (n={len(seg)}) "
                         f"|" if len(seg) else f"| {name} | {rng} | — |")
        lines.append("")

    lines.append("---")
    lines.append(
        f"**Summary:** drawdown-from-ATH is contrarian (cheap → higher forward return) "
        f"in {dd_hits}/{dd_n} assets; distance-from-200d-MA in {ma_hits}/{ma_n}. "
        + ("The bands above are a usable Finanzradar overlay — deep drawdowns "
           "historically preceded better forward returns."
           if dd_hits >= max(1, dd_n) * 0.6 else
           "The effect is weak/inconsistent here — do not rely on it as a standalone "
           "Finanzradar rule."))
    return "\n".join(lines)
