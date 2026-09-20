"""
Experiment #13 — the decisive test for the RSI(2) survivor from experiment #12.

RSI(2) mean-reversion was the first strategy to clear the full rigor battery
(significant after the multiple-testing haircut, walk-forward 76-81%, positive in
all regimes) on SPY and QQQ. But so did GLD/GDX in experiment #9 — until the
parameter-robustness grid (#10) exposed it as a lucky corner. So RSI(2) gets the
same treatment: a grid over its parameters (oversold threshold, exit MA, trend
filter on/off) at base / realistic / harsh costs. A real edge survives across most
of the grid at realistic costs; an overfit one only at oversold=10 / exit=SMA5.
"""
from __future__ import annotations
from typing import Callable
import pandas as pd
from loguru import logger

from .rigor import full_rigor
from .experiments_12 import rsi2_returns

GRID = {
    "oversold": [5, 10, 15, 20],
    "exit_sma": [2, 5, 10],
    "use_trend": [True, False],
}
COSTS = [("base", 0.05, 0.03), ("realistic", 0.05, 0.08), ("harsh", 0.10, 0.15)]


def rsi2_grid(df, comm, slip, n_trials=30):
    """Run RSI(2) across the parameter grid at one cost level; return result dicts."""
    rows = []
    for ov in GRID["oversold"]:
        for ex in GRID["exit_sma"]:
            for tr in GRID["use_trend"]:
                r = rsi2_returns(df, oversold=ov, exit_sma=ex, use_trend=tr,
                                 commission_pct=comm, slippage_pct=slip)
                res = full_rigor(f"ov{ov}/ex{ex}/tr{int(tr)}", r, n_trials)
                res.update({"ov": ov, "ex": ex, "tr": tr})
                rows.append(res)
    return rows


def _summary(rows):
    valid = [r for r in rows if r.get("verdict", "") != "insufficient data"]
    survive = sum(1 for r in valid if r["verdict"].startswith("✅"))
    sig = sum(1 for r in valid if r.get("sig_after_haircut"))
    poswf = sum(1 for r in valid if r.get("wf_pct", 0) >= 60 and r.get("oos_ret", 0) > 0)
    return survive, sig, poswf, len(valid)


def run_experiment13_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    symbols: list[str],
    n_trials: int = 30,
    limit: int = 2500,
) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #13 — RSI(2) parameter robustness "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append("Grid: oversold {5,10,15,20} × exit-MA {2,5,10} × trend-filter {on,off} = 24 combos. "
                 "A real edge survives across MOST of the grid at realistic costs — not just the "
                 "oversold=10/exit=SMA5 corner used in experiment #12.")
    lines.append("")

    overall_ok = True
    for sym in symbols:
        df = get_ohlcv(sym, "1Day", limit)
        lines.append(f"## {sym}")
        if df is None or len(df) < 400:
            lines.append("_insufficient data_\n")
            continue
        for label, comm, slip in COSTS:
            rows = rsi2_grid(df, comm, slip, n_trials)
            surv, sig, poswf, total = _summary(rows)
            pct = round(100 * surv / total) if total else 0
            verdict = ("✅ robust across parameters" if pct >= 50 else
                       "⚠️ partial" if pct >= 25 else "❌ overfit / not robust")
            if label == "realistic" and pct < 50:
                overall_ok = False
            lines.append(f"- **{label} costs:** {surv}/{total} combos survive full rigor · "
                         f"{sig}/{total} significant · {poswf}/{total} walk-forward≥60% → {verdict}")
        lines.append("")
        # compact grid at realistic costs
        rows = rsi2_grid(df, 0.05, 0.08, n_trials)
        lines.append("| oversold | exit-MA | trend | OOS ret% | Sharpe | p-value | sig | WF | verdict |")
        lines.append("|--:|--:|:--:|--:|--:|--:|:--:|:--:|---|")
        for r in rows:
            if r.get("verdict") == "insufficient data":
                continue
            lines.append(f"| {r['ov']} | {r['ex']} | {'y' if r['tr'] else 'n'} | "
                         f"{r['oos_ret']:+.0f} | {r['sharpe']} | {r['p_value']} | "
                         f"{'y' if r['sig_after_haircut'] else 'n'} | {r['wf_pct']}% | "
                         f"{'✅' if r['verdict'].startswith('✅') else '❌'} |")
        lines.append("")

    lines.append("---")
    lines.append("**Verdict:** " + (
        "RSI(2) SURVIVES the parameter grid at realistic costs on the tested indices — the first "
        "strategy in the whole project to pass every test. Worth a small paper trial."
        if overall_ok else
        "RSI(2) does NOT hold broadly across the parameter grid at realistic costs — like GLD/GDX, "
        "the #12 result leaned on favourable parameters."))
    return "\n".join(lines)
