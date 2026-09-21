"""
Experiment #19 — broad-universe scan across ALL asset classes.

Earlier experiments were criticised (fairly) for testing too few, crypto-heavy
symbols. This scans a WIDE universe on daily data (years of history): indices,
sectors, precious & industrial metals, energy, agriculture, currencies (incl. the
Swiss franc) and bonds, plus crypto. For every symbol it reports the market-
structure diagnostics (Hurst, variance ratio) AND runs the one real effect —
RSI(2) short-term mean reversion — through the full rigor battery. Grouped by class
so it is visible where (if anywhere) structure and a tradeable edge exist.
"""
from __future__ import annotations
from typing import Callable
import pandas as pd
from loguru import logger

from .rigor import full_rigor
from .quant_research import hurst_exponent, variance_ratio
from .experiments_12 import rsi2_returns


def run_experiment19_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    groups: dict[str, list[str]],
    n_trials: int = 60,
    limit: int = 2500,
) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #19 — broad-universe scan ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"All asset classes, daily data. Per symbol: Hurst (<0.45 mean-reverting, >0.55 "
                 f"trending), variance ratio, and RSI(2) mean-reversion through the full rigor "
                 f"battery (multiple-testing haircut α/{n_trials}, realistic costs).")
    lines.append("")

    all_results = []
    for group, syms in groups.items():
        lines.append(f"## {group}")
        lines.append("| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |")
        lines.append("|---|--:|--:|--:|--:|--:|:--:|---|")
        for sym in syms:
            try:
                df = get_ohlcv(sym, "1Day", limit)
            except Exception as e:
                logger.warning(f"Exp19: fetch {sym} failed: {e}")
                df = None
            if df is None or len(df) < 400:
                lines.append(f"| {sym} | — | — | — | — | — | — | no data |")
                continue
            c = df["close"].sort_index()
            h = hurst_exponent(c)
            vr = variance_ratio(c)
            res = full_rigor(f"RSI2 {sym}", rsi2_returns(df), n_trials)
            all_results.append((sym, res))
            hs = f"{h:.2f}" if h == h else "—"       # NaN check
            vrs = f"{vr:.2f}" if vr == vr else "—"
            if res.get("verdict") == "insufficient data":
                lines.append(f"| {sym} | {hs} | {vrs} | — | — | — | — | insufficient |")
            else:
                vshort = ("✅" if res["verdict"].startswith("✅")
                          else "⚠️" if res["verdict"].startswith("⚠") else "❌")
                lines.append(f"| {sym} | {hs} | {vrs} | {res['oos_ret']:+.0f} | {res['sharpe']} | "
                             f"{res['p_value']} | {'y' if res['sig_after_haircut'] else 'n'} | {vshort} |")
        lines.append("")

    survivors = [s for s, r in all_results if r.get("verdict", "").startswith("✅")]
    marginal = [s for s, r in all_results if r.get("verdict", "").startswith("⚠")]
    lines.append("---")
    lines.append(f"**Summary:** {len(all_results)} symbols scanned. "
                 f"RSI(2) survives full rigor on {len(survivors)} "
                 f"({', '.join(survivors) if survivors else 'none'}); "
                 f"marginal on {len(marginal)} ({', '.join(marginal) if marginal else 'none'}). "
                 f"With {len(all_results)} tests, expect ~{max(1, round(len(all_results)*0.05))} "
                 f"false positives at p<0.05 by chance — judge survivors against that.")
    return "\n".join(lines)
