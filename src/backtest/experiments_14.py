"""
Experiment #14 — the last item on the defined research agenda: volatility
targeting. This is NOT a return-prediction edge; it is a risk-management overlay
on buy-and-hold that scales exposure inversely to recent volatility to hold a
constant risk budget. The honest question: does it improve RISK-ADJUSTED return
(MAR / Sharpe) and cut drawdowns versus plain buy-and-hold? Causal, net of costs.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .trend_follow import _curve_stats
from .rigor import annualized_sharpe


def _norm(s: pd.Series) -> pd.Series:
    s = s.sort_index(); s.index = s.index.normalize(); return s


def vol_target_returns(df, target_vol=0.10, lookback=20, max_leverage=1.5,
                       commission_pct=0.05, slippage_pct=0.03) -> pd.Series:
    """Scale buy-and-hold exposure to a target annualized volatility, using only
    past volatility (causal). Weight capped at max_leverage."""
    c = _norm(df["close"])
    r = c.pct_change().fillna(0)
    realized = r.rolling(lookback).std() * np.sqrt(252)
    weight = (target_vol / realized).clip(upper=max_leverage)
    weight = weight.shift(1).fillna(0.0)              # today's weight from past vol
    cost = (commission_pct + slippage_pct) / 100
    turn = weight.diff().abs().fillna(weight.abs())
    return (weight * r - turn * cost).rename("ret")


def run_experiment14_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    symbols: list[str],
    target_vol: float = 0.10,
    window: int = 252,
    step: int = 63,
    limit: int = 2500,
) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #14 — volatility targeting (risk overlay) "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"Scale buy-and-hold to a {int(target_vol*100)}% annual-vol target (causal, "
                 "capped leverage). NOT a return edge — the question is whether it beats plain "
                 "holding on RISK-ADJUSTED return (MAR/Sharpe) and drawdown.")
    lines.append("")
    lines.append("| Symbol | Hold ret% | Hold maxDD% | Hold MAR | Hold Sharpe | "
                 "VolTgt ret% | VolTgt maxDD% | VolTgt MAR | VolTgt Sharpe | WF MAR-win | better? |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|:--:|:--:|")

    wins = 0
    tested = 0
    for sym in symbols:
        df = get_ohlcv(sym, "1Day", limit)
        if df is None or len(df) < 400:
            lines.append(f"| {sym} | insufficient data |||||||||")
            continue
        hold = _norm(df["close"]).pct_change().fillna(0)
        vt = vol_target_returns(df, target_vol=target_vol)
        h, v = _curve_stats(hold), _curve_stats(vt)
        hs, vs = annualized_sharpe(hold), annualized_sharpe(vt)
        # walk-forward: fraction of windows where vol-target MAR beats hold MAR
        common = vt.index.intersection(hold.index)
        vv, hh = vt.loc[common], hold.loc[common]
        wf_hit = wf_tot = 0
        i = 0
        while i + window <= len(common):
            if _curve_stats(vv.iloc[i:i+window])["mar"] > _curve_stats(hh.iloc[i:i+window])["mar"]:
                wf_hit += 1
            wf_tot += 1
            i += step
        wf = f"{wf_hit}/{wf_tot}" if wf_tot else "—"
        better = "✅" if (v["mar"] > h["mar"] and vs > hs) else "—"
        if better == "✅":
            wins += 1
        tested += 1
        lines.append(f"| {sym} | {h['ret']:+.0f} | {h['dd']:.0f} | {h['mar']} | {round(hs,2)} | "
                     f"{v['ret']:+.0f} | {v['dd']:.0f} | {v['mar']} | {round(vs,2)} | {wf} | {better} |")

    lines.append("")
    lines.append(f"**Summary:** vol-targeting improved risk-adjusted return on {wins}/{tested} symbols. "
                 "Vol-targeting typically trims drawdowns and can raise Sharpe modestly, but it does "
                 "NOT add return — it is risk management, not an edge.")
    return "\n".join(lines)
