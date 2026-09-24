"""
Experiment #31 — stress-testing the deep-drawdown signal from #30.

#30 found "drawdown ≤ −35% → +14% avg 90d forward return" and it went into
Finanzradar. That number needs the same hard scrutiny as everything else:

  1. BASELINE: is the in-zone forward return higher than the asset's ordinary
     (unconditional) 90d forward return? Crypto rises a lot anyway.
  2. REAL SAMPLE SIZE: overlapping daily windows inflate n. Count independent
     drawdown episodes (entry below −35%, re-armed only after recovering above −10%),
     and run a Welch t-test on NON-overlapping samples (every `horizon`-th day).
  3. OUT-OF-SAMPLE: does the excess hold in both halves of history?
  4. BREADTH / SURVIVORSHIP: include assets that did NOT recover well (emerging
     markets, energy, long bonds) alongside winners.
  5. PRACTICAL USE: monthly savings plan (DCA) vs a "dip reserve" plan that invests
     half each month, parks half in cash, and deploys the reserve whenever the asset is
     ≥35% below its high. Same total contributions; compare final wealth multiples.

Pure/causal, injected price fetcher for CI; the bot uses native broker prices.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

from .experiments_30 import drawdown_from_ath

ENTER = -0.35
RESET = -0.10


def drawdown_episodes(dd: pd.Series, enter: float = ENTER, reset: float = RESET) -> list:
    """Entry dates of independent deep-drawdown episodes: first day dd ≤ enter; the
    next episode can only start after dd has recovered above `reset`."""
    entries, armed = [], True
    for t, v in dd.dropna().items():
        if armed and v <= enter:
            entries.append(t)
            armed = False
        elif not armed and v > reset:
            armed = True
    return entries


def welch_t(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((a.mean() - b.mean()) / se) if se > 0 else float("nan")


def zone_stats(px: pd.Series, horizon: int = 90, enter: float = ENTER) -> dict:
    """Unconditional vs in-zone forward returns, non-overlapping t-test, OOS halves."""
    px = pd.Series(px).astype(float).dropna().sort_index()
    dd = drawdown_from_ath(px)
    fwd = px.shift(-horizon) / px - 1.0
    df = pd.concat({"dd": dd, "fwd": fwd}, axis=1).dropna()
    out = {"days": len(df), "zone_days": int((df["dd"] <= enter).sum()),
           "episodes": len(drawdown_episodes(dd, enter))}
    if len(df) < horizon * 3:
        out["insufficient"] = True
        return out
    out["uncond"] = float(df["fwd"].mean())
    zone = df[df["dd"] <= enter]
    out["zone"] = float(zone["fwd"].mean()) if len(zone) else float("nan")
    out["excess"] = out["zone"] - out["uncond"] if len(zone) else float("nan")
    # non-overlapping sample → roughly independent observations
    nov = df.iloc[::horizon]
    zin, zout = nov[nov["dd"] <= enter]["fwd"], nov[nov["dd"] > enter]["fwd"]
    out["nov_in"] = len(zin)
    out["t"] = welch_t(zin, zout)
    # out-of-sample halves
    half = len(df) // 2
    exc = []
    for part in (df.iloc[:half], df.iloc[half:]):
        z = part[part["dd"] <= enter]["fwd"]
        exc.append(float(z.mean() - part["fwd"].mean()) if len(z) else float("nan"))
    out["excess_h1"], out["excess_h2"] = exc
    return out


def dca_vs_dip_reserve(px: pd.Series, enter: float = ENTER) -> tuple:
    """Monthly contribution of 1. DCA invests all of it. Dip-reserve invests 0.5,
    parks 0.5 in cash (0% interest), and deploys all cash when dd ≤ enter.
    Returns (dca_multiple, dip_multiple) = final value / total contributed."""
    px = pd.Series(px).astype(float).dropna().sort_index()
    if len(px) < 300:
        return float("nan"), float("nan")
    dd = drawdown_from_ath(px)
    naive = px.index.tz_localize(None) if px.index.tz is not None else px.index
    month_ends = px.groupby(naive.to_period("M")).tail(1).index
    u_dca = u_dip = cash = 0.0
    n = 0
    for t in month_ends:
        p = float(px.loc[t])
        n += 1
        u_dca += 1.0 / p
        u_dip += 0.5 / p
        cash += 0.5
        if float(dd.loc[t]) <= enter and cash > 0:
            u_dip += cash / p
            cash = 0.0
    last = float(px.iloc[-1])
    return (u_dca * last) / n, (u_dip * last + cash) / n


def run_experiment31_report(fetch_prices: Callable[[str], pd.Series],
                            symbols: list[str], horizon: int = 90) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #31 — stress test of the deep-drawdown signal "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"Zone = drawdown ≤ {ENTER:.0%} from ATH. Compares in-zone {horizon}d "
                 f"forward return with the asset's ordinary {horizon}d return, counts "
                 f"independent episodes, t-test on non-overlapping samples, OOS halves, "
                 f"and a savings-plan comparison.")
    lines.append("")
    lines.append("| Asset | years | episodes | zone days | ordinary fwd% | zone fwd% | "
                 "excess pp | t (non-overl.) | excess H1 / H2 | DCA ×| dip-reserve × |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|--:|---|--:|--:|")

    reached, pos_excess, both_halves, dip_wins, sig = [], 0, 0, 0, 0
    tested = 0
    for sym in symbols:
        try:
            px = fetch_prices(sym)
        except Exception:
            px = None
        if px is None or len(px) < 400:
            lines.append(f"| {sym} | — | — | — | — | — | — | — | — | — | — | ")
            continue
        px = pd.Series(px).astype(float)
        px.index = pd.to_datetime(px.index)
        px.index = px.index.tz_localize(None) if px.index.tz is not None else px.index
        px = px.sort_index()
        st = zone_stats(px, horizon)
        yrs = len(px) / 252
        dca, dip = dca_vs_dip_reserve(px)
        tested += 1
        if dip == dip and dca == dca and dip > dca:
            dip_wins += 1
        if st.get("insufficient"):
            lines.append(f"| {sym} | {yrs:.1f} | — | — | — | — | — | — | — | "
                         f"{dca:.2f} | {dip:.2f} |")
            continue
        if st["zone_days"] == 0:
            lines.append(f"| {sym} | {yrs:.1f} | 0 | 0 | {100*st['uncond']:+.1f} | "
                         f"never reached | — | — | — | {dca:.2f} | {dip:.2f} |")
            continue
        reached.append(sym)
        if st["excess"] > 0:
            pos_excess += 1
        h1, h2 = st["excess_h1"], st["excess_h2"]
        if h1 == h1 and h2 == h2 and h1 > 0 and h2 > 0:
            both_halves += 1
        if st["t"] == st["t"] and st["t"] > 2.0:
            sig += 1
        f = lambda x: "—" if x != x else f"{100*x:+.1f}"
        lines.append(
            f"| {sym} | {yrs:.1f} | {st['episodes']} | {st['zone_days']} | "
            f"{100*st['uncond']:+.1f} | {100*st['zone']:+.1f} | {100*st['excess']:+.1f} | "
            f"{st['t']:.2f} (n={st['nov_in']}) | {f(h1)} / {f(h2)} | {dca:.2f} | {dip:.2f} |")
    lines.append("")

    lines.append("---")
    lines.append(
        f"**Summary:** zone reached in {len(reached)}/{tested} assets "
        f"({', '.join(reached) if reached else 'none'}). Positive excess over the "
        f"ordinary return in {pos_excess}/{len(reached) or 0}; positive in BOTH halves in "
        f"{both_halves}/{len(reached) or 0}; t>2 on non-overlapping samples in "
        f"{sig}/{len(reached) or 0}. Dip-reserve plan beat plain monthly DCA in "
        f"{dip_wins}/{tested}. Few independent episodes means wide uncertainty — "
        "judge the Finanzradar signal against that, not against the raw day count.")
    return "\n".join(lines)
