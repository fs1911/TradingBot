"""
Experiment #23 — the rebalancing premium (volatility harvesting).

Every prediction-based idea has now failed. But #22 surfaced one honest fact: the
only Sharpe above 1.0 in the whole project was simply holding all names equally.
That points at a *structural*, non-predictive mechanism — the rebalancing premium
(a.k.a. the diversification return / volatility harvesting, Fernholz' stochastic
portfolio theory): periodically resetting a diversified basket back to equal weight
can earn more than buy-and-hold, purely because it systematically sells what rose
and buys what fell, with no forecasting at all.

This measures it cleanly. On the SAME universe it compares:
  - rebalanced  : reset to equal weight every period (monthly / quarterly), and
  - buy & hold  : equal weight once, then let it drift.
The EXCESS (rebalanced − buy&hold) isolates the pure rebalancing premium — beta and
survivorship bias affect both legs identically and cancel. Run through full rigor at
several frequencies and costs (rebalancing is turnover-sensitive). Reported: each
leg's Sharpe and the excess through the battery. Fully causal, reuses #20.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor, rigor_row, RIGOR_HEADER, annualized_sharpe
from .experiments_20 import build_price_panel, long_short_returns


def buy_and_hold_returns(panel: pd.DataFrame) -> pd.Series:
    """Equal-dollar weights on day 0, then hold (weights drift with price). Exact
    daily portfolio return from the drifting basket value."""
    p = panel.dropna()
    rets = p.pct_change().fillna(0.0)
    n = p.shape[1]
    growth = (1.0 + rets).cumprod()          # day-0 row = 1.0
    value = growth * (1.0 / n)               # equal dollars at inception
    total = value.sum(axis=1)
    return total.pct_change().fillna(0.0)


def rebalanced_returns(panel: pd.DataFrame, rebalance: str = "M",
                       cost_bps: float = 5.0) -> pd.Series:
    """Equal-weight the full universe, reset every `rebalance` period (net costs)."""
    p = panel.dropna()
    return long_short_returns(p, lambda ps: pd.Series(1.0, index=ps.columns),
                              rebalance=rebalance, top=1.0, cost_bps=cost_bps,
                              long_only=True)


def rebalancing_premium(panel: pd.DataFrame, rebalance: str = "M", cost_bps: float = 5.0):
    """Return (rebalanced, buyhold, excess) daily series on the common span."""
    p = panel.dropna()
    reb = rebalanced_returns(p, rebalance, cost_bps)
    bh = buy_and_hold_returns(p).reindex(reb.index).fillna(0.0)
    return reb, bh, (reb - bh)


def run_experiment23_report(get_ohlcv: Callable[[str, str, int], pd.DataFrame],
                            universe: list[str], n_trials: int = 74,
                            limit: int = 2500) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #23 — rebalancing premium (volatility harvesting) "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    panel = build_price_panel(get_ohlcv, universe, limit=limit)
    panel = panel.dropna() if not panel.empty else panel
    if panel.empty or panel.shape[1] < 20 or len(panel) < 400:
        lines.append(f"Insufficient data: {0 if panel.empty else panel.shape[1]} "
                     f"symbols on the common span (need ≥20 and ≥400 days).")
        return "\n".join(lines)

    n_names = panel.shape[1]
    span = f"{panel.index[0]:%Y-%m-%d} → {panel.index[-1]:%Y-%m-%d}"
    bh = buy_and_hold_returns(panel)
    bh_sharpe = round(annualized_sharpe(bh), 2)
    lines.append(f"Universe: {n_names} stocks, common span {span} ({len(panel)} days). "
                 f"Buy&hold equal-weight Sharpe = {bh_sharpe}. EXCESS (rebalanced − "
                 f"buy&hold) through full rigor; haircut α/{n_trials}.")
    lines.append("")
    lines.append("> The excess isolates the pure rebalancing premium: beta and "
                 "survivorship bias hit both legs equally and cancel. If the excess "
                 "survives, systematic rebalancing adds a real, forecast-free return.")
    lines.append("")
    lines.append("| Rebalance | cost | Rebal Sharpe | B&H Sharpe | Premium Sharpe | "
                 "Premium OOS% | Premium p | sig | Verdict |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|:--:|---|")

    configs = [("W", 1.0), ("M", 1.0), ("M", 5.0), ("Q", 5.0)]
    detail = []
    for freq, cost in configs:
        fname = {"W": "weekly", "M": "monthly", "Q": "quarterly"}[freq]
        try:
            reb, bhl, excess = rebalancing_premium(panel, rebalance=freq, cost_bps=cost)
            rs = round(annualized_sharpe(reb), 2)
            res = full_rigor(f"rebal premium {fname} @ {cost:.0f}bps", excess, n_trials)
            detail.append(res)
            if res.get("verdict") == "insufficient data":
                lines.append(f"| {fname} | {cost:.0f}bps | {rs} | {bh_sharpe} | — | — | "
                             f"— | — | insufficient |")
            else:
                vshort = ("✅" if res["verdict"].startswith("✅")
                          else "⚠️" if res["verdict"].startswith("⚠") else "❌")
                lines.append(
                    f"| {fname} | {cost:.0f}bps | {rs} | {bh_sharpe} | {res['sharpe']} | "
                    f"{res['oos_ret']:+.0f} | {res['p_value']} | "
                    f"{'y' if res['sig_after_haircut'] else 'n'} | {vshort} |")
        except Exception as e:
            logger.warning(f"Exp23 {fname}@{cost} failed: {e}")
            lines.append(f"| {fname} | {cost:.0f}bps | — | {bh_sharpe} | — | — | — | — | error |")
    lines.append("")

    survivors = [r for r in detail if r.get("verdict", "").startswith("✅")]
    marginal = [r for r in detail if r.get("verdict", "").startswith("⚠")]
    best = max([r for r in detail if "sharpe" in r], key=lambda r: r["sharpe"], default=None)
    lines.append("---")
    lines.append(
        f"**Summary:** buy&hold Sharpe = {bh_sharpe}. Rebalancing-premium survivors: "
        f"{len(survivors)}; marginal: {len(marginal)}. "
        + (f"Best premium Sharpe: {best['sharpe']} (p={best['p_value']}). " if best else "")
        + "A tiny/insignificant premium means rebalancing is a risk-control tool here, "
        "not an added-return edge.")
    return "\n".join(lines)
