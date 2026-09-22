"""
Experiment #26 — hunting a bigger / more robust structural carry.

#24-25 established one real edge: flat delta-neutral funding carry on a few coins,
~8%/yr gross but thin over cash net of costs. #26 asks whether the SAME structural
premium can be made larger or steadier by breadth and selection — three variants,
all on the funding data we can already fetch:

  1. Broad basket   — equal-weight carry across a wide (~24-coin) perp universe;
                       does diversification steady the drip?
  2. Carry-weighted — overweight coins with historically higher funding (weights from
                       TRAILING funding, lagged one day so it is causal); does tilting
                       toward high carry add return without proportional risk?
  3. Cross-sectional spread — each day long the high-funding half's carry and short the
                       low-funding half's, harvesting the DISPERSION in funding rather
                       than its level (funding-neutral to the market-wide level).

Each daily series goes through the full rigor battery. Honesty carries over from #24:
a ✅ = persistent in-sample carry, not risk-free; the spread variant needs shorting
low-funding perps too, i.e. more legs, more cost and more counterparty exposure. Data
injected; fully causal.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

from .rigor import full_rigor, rigor_row, RIGOR_HEADER, annualized_sharpe
from .experiments_24 import funding_to_daily_carry


def build_carry_panel(fetch_funding: Callable[[str], pd.Series],
                      symbols: list[str], min_days: int = 300) -> pd.DataFrame:
    """Daily carry (delta-neutral short-perp) per coin, aligned by calendar date."""
    cols = {}
    for s in symbols:
        try:
            f = fetch_funding(s)
        except Exception:
            f = None
        d = funding_to_daily_carry(f) if f is not None else pd.Series(dtype=float)
        if len(d) >= min_days:
            cols[s] = d
    if len(cols) < 3:
        return pd.DataFrame()
    return pd.DataFrame(cols).sort_index()


def equal_weight_carry(panel: pd.DataFrame) -> pd.Series:
    """Mean daily carry across all coins available that day."""
    return panel.mean(axis=1, skipna=True).dropna()


def carry_weighted(panel: pd.DataFrame, window: int = 30, min_periods: int = 10) -> pd.Series:
    """Weight each coin by its TRAILING mean funding (lagged 1 day → causal),
    clipped at zero and normalised across the coins available that day."""
    trailing = panel.rolling(window, min_periods=min_periods).mean().shift(1)
    w = trailing.clip(lower=0.0)
    wsum = w.sum(axis=1)
    w = w.div(wsum.where(wsum > 0), axis=0)
    daily = (w * panel).sum(axis=1, skipna=True)
    return daily.where(wsum > 0).dropna()


def cross_sectional_spread(panel: pd.DataFrame, window: int = 30,
                           min_periods: int = 10) -> pd.Series:
    """Long the high-funding half's carry, short the low-funding half's, ranked by
    trailing funding (lagged → causal). Harvests dispersion, not the level."""
    trailing = panel.rolling(window, min_periods=min_periods).mean().shift(1)
    out = {}
    for dt, row in trailing.iterrows():
        valid = row.dropna()
        if len(valid) < 4:
            continue
        med = valid.median()
        hi = valid[valid > med].index
        lo = valid[valid <= med].index
        today = panel.loc[dt]
        hi_r, lo_r = today[hi].mean(), today[lo].mean()
        if pd.notna(hi_r) and pd.notna(lo_r):
            out[dt] = float(hi_r - lo_r)
    return pd.Series(out).sort_index()


def run_experiment26_report(fetch_funding: Callable[[str], pd.Series],
                            symbols: list[str], n_trials: int = 84) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #26 — broader / smarter structural carry "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    panel = build_carry_panel(fetch_funding, symbols)
    if panel.empty:
        lines.append("Insufficient funding data (need ≥3 coins with ≥300 daily points).")
        return "\n".join(lines)

    n_coins = panel.shape[1]
    span = f"{panel.index[0]:%Y-%m-%d} → {panel.index[-1]:%Y-%m-%d}"
    lines.append(f"{n_coins} coins with usable funding history ({', '.join(panel.columns)}). "
                 f"Span {span}. Each variant's daily carry through the full rigor "
                 f"battery; haircut α/{n_trials}.")
    lines.append("")
    lines.append("> Same honesty as #24: ✅ = persistent in-sample carry, NOT risk-free "
                 "(counterparty/liquidation/basis unmodeled). The spread variant also "
                 "shorts low-funding perps — more legs, more cost, more exposure.")
    lines.append("")

    variants = {
        "1. Broad basket (equal-weight)": equal_weight_carry(panel),
        "2. Carry-weighted (tilt to high funding)": carry_weighted(panel),
        "3. Cross-sectional spread (dispersion)": cross_sectional_spread(panel),
    }

    lines.append("| Variant | ann.return% | Sharpe | p-value | sig | Walk-fwd | regimes+ | Verdict |")
    lines.append("|---|--:|--:|--:|:--:|:--:|:--:|---|")
    results = []
    for name, series in variants.items():
        s = series.dropna()
        ann = round(100 * float(s.mean()) * 365, 1) if len(s) else float("nan")
        res = full_rigor(name, s, n_trials)
        results.append((name, ann, res))
        if res.get("verdict") == "insufficient data":
            lines.append(f"| {name} | {ann} | — | — | — | — | — | insufficient |")
        else:
            vshort = ("✅" if res["verdict"].startswith("✅")
                      else "⚠️" if res["verdict"].startswith("⚠") else "❌")
            lines.append(f"| {name} | {ann} | {res['sharpe']} | {res['p_value']} | "
                         f"{'y' if res['sig_after_haircut'] else 'n'} | {res['wf_pct']}% | "
                         f"{res['regime_positive']} | {vshort} |")
    lines.append("")

    # compare to the #24 finding: is the broad/weighted basket bigger than ~8%/yr?
    eq = next((a for n, a, r in results if n.startswith("1.")), float("nan"))
    cw = next((a for n, a, r in results if n.startswith("2.")), float("nan"))
    lines.append("---")
    note = []
    if eq == eq and cw == cw:
        if cw > eq * 1.15:
            note.append(f"Carry-weighting lifts the annual return ({eq}%→{cw}%) — tilting "
                        "toward high-funding coins helps.")
        else:
            note.append(f"Carry-weighting ({cw}%) does not beat the plain broad basket "
                        f"({eq}%) — the level, not selection, is what pays.")
    lines.append("**Summary:** " + " ".join(note) +
                 " Breadth may steady the drip, but the same cost-fragility and unpriced "
                 "tail risks from #25 still bound how tradeable this is.")
    return "\n".join(lines)
