"""
Experiment #18 — a NEW DATA REGIME: intraday (5-minute) bars instead of daily.

The whole project so far ran on daily bars — few observations, and blind to
intraday structure. This tests the user's hypothesis that the resolution was the
limitation. Intraday gives ~50-80x more observations and a different pattern class.

Strategy: intraday mean reversion, fully within-session (flat overnight, so no
gap risk). Within each trading day, a rolling z-score of price vs its recent
intraday mean; go long when stretched down (z < -entry), exit when it reverts
(z > -exit) or at the session close. Per-bar returns are aggregated to a DAILY P&L
series, which is then judged by the standard daily-calibrated rigor battery.

Honest note: intraday is where HFT has the structural edge and where costs/spreads
bite hardest — so costs matter a lot here. Causal throughout.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor


def intraday_meanrev_daily_returns(df, w=12, entry=1.5, exit=0.3,
                                   commission_pct=0.01, slippage_pct=0.02):
    """Within-day rolling-z mean reversion on intraday bars; returns a DAILY net
    return series (sum of per-bar P&L within each session). Flat overnight."""
    if df is None or len(df) < 500:
        return pd.Series(dtype=float)
    c = df["close"].sort_index()
    idx = c.index
    day = pd.Index(idx).tz_convert("UTC").normalize() if idx.tz is not None else pd.Index(idx).normalize()
    cost = (commission_pct + slippage_pct) / 100

    daily = {}
    close = c.to_numpy()
    # iterate per session
    df2 = pd.DataFrame({"c": close, "day": day.values})
    for d, grp in df2.groupby("day"):
        p = grp["c"].to_numpy()
        n = len(p)
        if n < w + 5:
            continue
        r = np.zeros(n)
        r[1:] = p[1:] / p[:-1] - 1
        # rolling mean/std over trailing w bars (causal, within day)
        pos = np.zeros(n)
        cur = 0
        for i in range(n):
            if i < w:
                pos[i] = 0; continue
            win = p[i - w:i]
            mu = win.mean(); sd = win.std()
            z = (p[i] - mu) / sd if sd > 0 else 0.0
            if i == n - 1:                     # force flat at session close
                cur = 0
            elif cur == 0 and z < -entry:
                cur = 1
            elif cur == 1 and z > -exit:
                cur = 0
            pos[i] = cur
        held = np.concatenate([[0.0], pos[:-1]])       # position during bar i = decision at i-1
        turn = np.abs(np.diff(np.concatenate([[0.0], held])))
        pnl = held * r - turn * cost
        daily[pd.Timestamp(d)] = float(pnl.sum())

    if not daily:
        return pd.Series(dtype=float)
    s = pd.Series(daily).sort_index()
    s.name = "ret"
    return s


def run_experiment18_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    symbols: list[str],
    timeframe: str = "5Min",
    n_trials: int = 50,
    limit: int = 20000,
) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #18 — intraday ({timeframe}) mean reversion "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"NEW DATA REGIME: intraday bars (~50-80x more observations than daily). "
                 f"Within-session rolling-z mean reversion, flat overnight, per-bar P&L aggregated "
                 f"to daily and judged by the full rigor battery (haircut α/{n_trials}). Intraday "
                 f"costs bite hard — watch whether any edge survives them.")
    lines.append("")
    lines.append("| Symbol | bars | days | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|:--:|:--:|:--:|---|")

    results = []
    for sym in symbols:
        try:
            df = get_ohlcv(sym, timeframe, limit)
        except Exception as e:
            logger.warning(f"Exp18: fetch {sym} failed: {e}")
            df = None
        if df is None or len(df) < 2000:
            lines.append(f"| {sym} | {0 if df is None else len(df)} | — | intraday data unavailable/too short |||||||")
            continue
        daily = intraday_meanrev_daily_returns(df)
        if daily.empty or len(daily) < 300:
            lines.append(f"| {sym} | {len(df)} | {len(daily)} | too few sessions |||||||")
            continue
        res = full_rigor(f"IntradayMR {sym}", daily, n_trials)
        results.append(res)
        lines.append(f"| {sym} | {len(df)} | {len(daily)} | {res['oos_ret']:+.0f} | {res['sharpe']} | "
                     f"{res['t_stat']} | {res['p_value']} | {'yes' if res['sig_after_haircut'] else 'no'} | "
                     f"{res['wf_pct']}% | {res['regime_positive']} | {res['verdict']} |")

    lines.append("")
    survivors = [r for r in results if r.get("verdict", "").startswith("✅")]
    lines.append(f"**Summary:** {len(survivors)}/{len(results)} survive the full battery on intraday data. "
                 + (", ".join(r["name"] for r in survivors) if survivors else
                    "None — more data / finer resolution did not reveal a cost-surviving intraday edge."))
    return "\n".join(lines)
