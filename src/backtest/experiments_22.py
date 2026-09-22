"""
Experiment #22 — is the long-only momentum result ALPHA or just BETA?

Exp #21's standout was the long-only top-decile momentum portfolio (Sharpe 0.72,
+106% OOS, positive in all regimes) — the strongest number in the whole project.
But a long-only equity portfolio is ~100% market exposure, so on a survivorship-
biased universe in a huge bull market that number could be pure market beta, not
stock-selection skill.

This experiment isolates the two. For each selection method it computes the
long-only top-quantile portfolio AND the fair no-skill benchmark — the equal-weight
return of the SAME universe — and runs full rigor on the EXCESS (portfolio minus
benchmark) return series. Excess return is, by construction, market-neutral: if it
survives, momentum genuinely picks better-than-average stocks (tradeable long-only
alpha). If it doesn't, #21's long-only result was beta.

Reported side by side: portfolio Sharpe, benchmark Sharpe, and alpha (excess) through
the battery — so the beta/alpha split is explicit. Fully causal, reuses #20/#21.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import (full_rigor, rigor_row, RIGOR_HEADER,
                    annualized_sharpe)
from .experiments_20 import build_price_panel, long_short_returns
from .experiments_21 import (score_momentum, score_residual_momentum,
                             score_volscaled_momentum)


def equal_weight_benchmark(panel: pd.DataFrame) -> pd.Series:
    """Fair no-skill benchmark: hold every stock equal-weight (daily EW return)."""
    return panel.pct_change().mean(axis=1).fillna(0.0)


def long_only_excess(panel: pd.DataFrame, score_fn: Callable[[pd.DataFrame], pd.Series],
                     top: float = 0.1, cost_bps: float = 5.0, rebalance: str = "M"):
    """Return (portfolio, benchmark, excess) daily series. Portfolio = long-only
    top-`top` quantile by score (net of costs); benchmark = equal-weight universe;
    excess = portfolio - benchmark (market-neutral by construction)."""
    port = long_short_returns(panel, score_fn, rebalance, top=top,
                              cost_bps=cost_bps, long_only=True)
    bench = equal_weight_benchmark(panel).reindex(port.index).fillna(0.0)
    return port, bench, (port - bench)


def run_experiment22_report(get_ohlcv: Callable[[str, str, int], pd.DataFrame],
                            universe: list[str], n_trials: int = 70,
                            limit: int = 2500, cost_bps: float = 5.0) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #22 — long-only momentum: alpha or beta? "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    panel = build_price_panel(get_ohlcv, universe, limit=limit)
    if panel.empty or panel.shape[1] < 20:
        lines.append(f"Insufficient data: only {0 if panel.empty else panel.shape[1]} "
                     f"symbols with enough history (need ≥20).")
        return "\n".join(lines)

    n_names = panel.shape[1]
    span = f"{panel.index[0]:%Y-%m-%d} → {panel.index[-1]:%Y-%m-%d}"
    bench = equal_weight_benchmark(panel)
    bench_sharpe = round(annualized_sharpe(bench), 2)
    lines.append(f"Universe: {n_names} stocks. Span: {span} ({len(panel)} days). "
                 f"Long-only, monthly, {cost_bps:.0f} bps. Equal-weight-universe "
                 f"benchmark Sharpe = {bench_sharpe}. Rigor on EXCESS returns; "
                 f"haircut α/{n_trials}.")
    lines.append("")
    lines.append("> The excess (portfolio − equal-weight benchmark) series is "
                 "market-neutral by construction: if IT survives rigor, the selection "
                 "adds real alpha; if not, the raw long-only Sharpe was market beta.")
    lines.append("")
    lines.append("| Selection | quantile | Port Sharpe | Bench Sharpe | Alpha Sharpe | "
                 "Alpha OOS% | Alpha p | sig | Verdict |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|:--:|---|")

    configs = [
        ("Raw 12-1", score_momentum, 0.1),
        ("Raw 12-1", score_momentum, 0.2),
        ("Raw 12-1", score_momentum, 0.3),
        ("Residual", score_residual_momentum, 0.1),
        ("Vol-scaled", score_volscaled_momentum, 0.1),
    ]

    detail = []
    for label, fn, top in configs:
        try:
            port, bm, excess = long_only_excess(panel, fn, top=top, cost_bps=cost_bps)
            ps = round(annualized_sharpe(port), 2)
            res = full_rigor(f"{label} q{int(top*100)} alpha", excess, n_trials)
            detail.append(res)
            if res.get("verdict") == "insufficient data":
                lines.append(f"| {label} | top {int(top*100)}% | {ps} | {bench_sharpe} | "
                             f"— | — | — | — | insufficient |")
            else:
                vshort = ("✅" if res["verdict"].startswith("✅")
                          else "⚠️" if res["verdict"].startswith("⚠") else "❌")
                lines.append(
                    f"| {label} | top {int(top*100)}% | {ps} | {bench_sharpe} | "
                    f"{res['sharpe']} | {res['oos_ret']:+.0f} | {res['p_value']} | "
                    f"{'y' if res['sig_after_haircut'] else 'n'} | {vshort} |")
        except Exception as e:
            logger.warning(f"Exp22 {label} q{top} failed: {e}")
            lines.append(f"| {label} | top {int(top*100)}% | — | {bench_sharpe} | "
                         f"— | — | — | — | error |")
    lines.append("")

    survivors = [r for r in detail if r.get("verdict", "").startswith("✅")]
    marginal = [r for r in detail if r.get("verdict", "").startswith("⚠")]
    best = max([r for r in detail if "sharpe" in r], key=lambda r: r["sharpe"], default=None)
    lines.append("---")
    lines.append(
        f"**Summary:** benchmark (equal-weight universe) Sharpe = {bench_sharpe}. "
        f"Excess-return survivors: {len(survivors)}; marginal: {len(marginal)}. "
        + (f"Best alpha Sharpe: {best['sharpe']} (p={best['p_value']}). " if best else "")
        + "If the alpha Sharpes are near 0 while the benchmark Sharpe is high, the "
        "long-only momentum result was market beta, not selection skill.")
    return "\n".join(lines)
