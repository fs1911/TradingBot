"""
Experiment #27 — cross-exchange funding differential (a low-turnover carry).

#25 showed the funding carry's enemy is TURNOVER: constant rehedging of the spot leg
eats the margin. This tests a structurally-related carry that needs NO spot leg and
almost no rehedging: the same perpetual has slightly different funding on different
exchanges. Going long the perp on the LOW-funding venue and short it on the
HIGH-funding venue is market-neutral (perp vs perp, no spot) and earns the funding
DIFFERENTIAL — a documented venue-dislocation carry.

For each coin it aligns per-venue funding, and each day (causally, from trailing
funding lagged one day) shorts the highest-funding venue and longs the lowest,
earning today's differential. Combined across coins, run through the full rigor
battery. Reported: the average annualised differential (how thin it is) and the
strategy's rigor verdict.

Honesty: the differential across major venues is small and heavily arbitraged; this
needs collateral on ≥2 exchanges, cross-venue transfer/latency, and liquidation risk
on both legs — none of which the battery prices. Data injected; fully causal.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

from .rigor import full_rigor, annualized_sharpe
from .experiments_24 import funding_to_daily_carry


def cross_exchange_spread(per_ex_daily: dict, window: int = 30,
                          min_periods: int = 10) -> pd.Series:
    """Daily funding differential: short the highest-trailing-funding venue, long the
    lowest (ranking lagged 1 day → causal). Perp-vs-perp, market-neutral."""
    cols = {k: v for k, v in per_ex_daily.items() if v is not None and len(v)}
    if len(cols) < 2:
        return pd.Series(dtype=float)
    panel = pd.DataFrame(cols).sort_index()
    trailing = panel.rolling(window, min_periods=min_periods).mean().shift(1)
    out = {}
    for dt, row in trailing.iterrows():
        valid = row.dropna()
        if len(valid) < 2:
            continue
        hi, lo = valid.idxmax(), valid.idxmin()
        today = panel.loc[dt]
        if pd.notna(today[hi]) and pd.notna(today[lo]):
            out[dt] = float(today[hi] - today[lo])   # receive hi, pay lo
    return pd.Series(out).sort_index()


def run_experiment27_report(fetch_multi: Callable[[str], dict],
                            symbols: list[str], n_trials: int = 90) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #27 — cross-exchange funding differential "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append("Perp-vs-perp across venues (long low-funding venue, short "
                 "high-funding venue): market-neutral, ~no spot leg, harvests the "
                 f"funding DIFFERENTIAL. Combined series through full rigor; α/{n_trials}.")
    lines.append("")
    lines.append("> Honesty: the differential is small and arbitraged; needs collateral "
                 "on ≥2 exchanges, cross-venue transfers, and dual liquidation risk — "
                 "unpriced here. A ✅ = persistent in-sample differential, not free money.")
    lines.append("")

    per_symbol = {}
    lines.append("| Coin | venues | avg differential%/yr | days |")
    lines.append("|---|--:|--:|--:|")
    for sym in symbols:
        try:
            multi = fetch_multi(sym)
        except Exception:
            multi = None
        if not multi:
            lines.append(f"| {sym} | 0 | — | — |")
            continue
        per_ex_daily = {ex: funding_to_daily_carry(f) for ex, f in multi.items()
                        if f is not None and len(f)}
        per_ex_daily = {ex: d for ex, d in per_ex_daily.items() if len(d) >= 200}
        spread = cross_exchange_spread(per_ex_daily)
        if len(spread) < 200:
            lines.append(f"| {sym} | {len(per_ex_daily)} | — | {len(spread)} |")
            continue
        per_symbol[sym] = spread
        ann = 100 * float(spread.mean()) * 365
        lines.append(f"| {sym} | {len(per_ex_daily)} | {ann:+.2f} | {len(spread)} |")
    lines.append("")

    if not per_symbol:
        lines.append("---")
        lines.append("**Summary:** no coin had ≥2 venues with enough aligned funding "
                     "history — cross-exchange differential not measurable here.")
        return "\n".join(lines)

    combined = pd.concat(per_symbol.values(), axis=1).mean(axis=1).dropna()
    ann = round(100 * float(combined.mean()) * 365, 2)
    sharpe = round(annualized_sharpe(combined), 2)
    res = full_rigor("cross-exchange differential", combined, n_trials)
    verdict = res.get("verdict", "insufficient data")
    lines.append("---")
    lines.append(f"**Combined ({len(per_symbol)} coins):** ~{ann:+.2f}%/yr, Sharpe {sharpe}, "
                 f"p={res.get('p_value', '—')}, walk-fwd {res.get('wf_pct', '—')}%, "
                 f"verdict: {verdict}.")
    lines.append("")
    thin = abs(ann) < 3.0
    lines.append("**Summary:** " + (
        "the differential is tiny (<3%/yr gross) — after two-venue fees, transfers and "
        "dual liquidation risk it is not a real edge; the level carry (#24-26) remains "
        "the only worthwhile version."
        if thin else
        "the differential is non-trivial; the honest next step is a two-venue net-cost "
        "and operational-risk study before believing it."))
    return "\n".join(lines)
