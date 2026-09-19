"""
Research pipeline — the reusable rigor harness.

Every hypothesis in this project runs through the SAME bar so results are
comparable and honest, and so "many tries" can't turn into self-deception:
  IS/OOS split · walk-forward across windows · cost-sensitivity · vs a benchmark.

The higher the number of hypotheses tried, the more a good-looking single result
is likely noise (multiple-testing). So the verdict rules here are deliberately
strict: an edge must survive OUT-of-sample, across MOST walk-forward windows, AND
at realistic costs.

This module also holds the first economically-grounded experiment: mean reversion
of inter-commodity RATIOS (gold/silver, platinum/palladium, gold/oil) — pairs with
a real supply/demand linkage, not statistical coincidences.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .trend_follow import _curve_stats
from .oos_runner import split_is_oos

# (label, commission%, slippage%, borrow%/yr) — shared cost scenarios
COST_SCENARIOS = [
    ("optimistic", 0.02, 0.02, 0.0),
    ("base",       0.05, 0.03, 1.0),
    ("realistic",  0.05, 0.08, 3.0),
    ("harsh",      0.10, 0.15, 8.0),
]


def walk_forward(returns: pd.Series, window: int = 252, step: int = 63,
                 min_mar: float = 0.5) -> tuple[int, int]:
    """Count windows where the strategy is positive with MAR>min_mar."""
    r = returns.dropna()
    hits = total = 0
    i = 0
    while i + window <= len(r):
        st = _curve_stats(r.iloc[i:i + window])
        total += 1
        if st["ret"] > 0 and st["mar"] > min_mar:
            hits += 1
        i += step
    return hits, total


def evaluate_hypothesis(name: str, returns: pd.Series, window: int = 252,
                        step: int = 63) -> dict:
    """Run one strategy's daily-return series through the standard rigor and return
    a comparable result dict with an honest verdict."""
    returns = returns.dropna()
    if len(returns) < window + step:
        return {"name": name, "verdict": "insufficient data", "oos_mar": None,
                "oos_ret": None, "wf": "—"}
    is_r, oos_r = split_is_oos(returns.to_frame("r"))
    isst, oosst = _curve_stats(is_r["r"]), _curve_stats(oos_r["r"])
    hits, total = walk_forward(returns, window, step)
    pct = round(100 * hits / total) if total else 0
    if oosst["ret"] > 0 and oosst["mar"] > 0.8 and pct >= 60:
        verdict = "✅ survives"
    elif oosst["ret"] > 0 and pct >= 40:
        verdict = "⚠️ marginal / regime-dependent"
    else:
        verdict = "❌ no robust edge"
    return {"name": name, "is_ret": isst["ret"], "is_mar": isst["mar"],
            "oos_ret": oosst["ret"], "oos_mar": oosst["mar"], "oos_dd": oosst["dd"],
            "wf": f"{hits}/{total} ({pct}%)", "wf_pct": pct, "verdict": verdict}


# ─── first experiment: inter-commodity ratio mean reversion ──────────────────
def ratio_strategy_returns(a: pd.Series, b: pd.Series, *, z_window: int = 60,
                           entry: float = 2.0, exit: float = 0.5,
                           commission_pct: float = 0.05, slippage_pct: float = 0.03,
                           borrow_pct_annual: float = 0.0) -> pd.Series:
    """Market-neutral mean reversion on the ECONOMIC ratio A/B (fixed 1:1 legs, no
    fitted beta — the linkage is the ratio itself). Trades the z-score of the log
    ratio. Causal; net of costs + short borrow."""
    df = pd.concat({"a": a, "b": b}, axis=1).dropna()
    if len(df) < z_window + 40:
        return pd.Series(dtype=float)
    la, lb = np.log(df["a"]), np.log(df["b"])
    ratio = la - lb
    mu = ratio.rolling(z_window).mean()
    sd = ratio.rolling(z_window).std()
    z = ((ratio - mu) / sd).to_numpy()

    pos = np.zeros(len(df))
    cur = 0
    for i in range(len(df)):
        if np.isnan(z[i]):
            pos[i] = 0
            continue
        if cur == 0:
            if z[i] > entry:
                cur = -1          # ratio too high → short A, long B
            elif z[i] < -entry:
                cur = 1
        elif cur == 1 and z[i] >= -exit:
            cur = 0
        elif cur == -1 and z[i] <= exit:
            cur = 0
        pos[i] = cur

    pos_s = pd.Series(pos, index=df.index).shift(1).fillna(0)
    ra, rb = la.diff(), lb.diff()
    spread_ret = ((ra - rb) / 2).fillna(0)         # 1:1 legs, gross ≈ 2
    cost = (commission_pct + slippage_pct) / 100
    borrow_daily = (borrow_pct_annual / 100) / 252
    turn = pos_s.diff().abs().fillna(pos_s.abs())
    return (pos_s * spread_ret - turn * cost - borrow_daily * pos_s.abs()).rename("ret")


def run_ratio_research(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    experiments: list[tuple[str, str]],
    limit: int = 2500,
    window: int = 252,
    step: int = 63,
) -> str:
    """For each economic commodity ratio: cost-sensitivity sweep + walk-forward."""
    from datetime import datetime, timezone

    lines = [f"# Commodity-Ratio Research — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    lines.append("Mean reversion of economically-linked commodity ratios (fixed 1:1 legs, "
                 "market-neutral). Net of costs incl. short borrow. A real edge survives OOS, "
                 "most walk-forward windows, AND realistic costs.")
    lines.append("")

    cache: dict[str, pd.DataFrame] = {}
    def _fetch(sym: str):
        if sym not in cache:
            try:
                cache[sym] = get_ohlcv(sym, "1Day", limit)
            except Exception as e:
                logger.warning(f"Ratio: fetch {sym} failed: {e}")
                cache[sym] = pd.DataFrame()
        return cache[sym]

    any_survivor = False
    for a_sym, b_sym in experiments:
        da, db = _fetch(a_sym), _fetch(b_sym)
        lines.append(f"## {a_sym} / {b_sym}")
        if da is None or db is None or len(da) < 400 or len(db) < 400:
            lines.append("_insufficient data_\n")
            continue
        a = da["close"].sort_index(); a.index = a.index.normalize()
        b = db["close"].sort_index(); b.index = b.index.normalize()
        lines.append("| Scenario | comm/slip/borrow | OOS ret% | OOS MAR | Walk-fwd | Verdict |")
        lines.append("|---|---|--:|--:|:--:|---|")
        for label, comm, slip, borrow in COST_SCENARIOS:
            r = ratio_strategy_returns(a, b, commission_pct=comm, slippage_pct=slip,
                                       borrow_pct_annual=borrow)
            res = evaluate_hypothesis(f"{a_sym}/{b_sym}", r, window, step)
            if res.get("oos_mar") is None:
                lines.append(f"| {label} | {comm}/{slip}/{borrow}% | — | — | — | insufficient |")
                continue
            if label == "realistic" and res["verdict"].startswith("✅"):
                any_survivor = True
            lines.append(f"| {label} | {comm}/{slip}/{borrow}% | {res['oos_ret']:+.0f} | "
                         f"{res['oos_mar']} | {res['wf']} | {res['verdict']} |")
        lines.append("")

    lines.append("---")
    lines.append("**Summary:** " + ("at least one ratio SURVIVED at realistic costs — investigate further."
                 if any_survivor else "no ratio survived at realistic costs across the walk-forward."))
    return "\n".join(lines)


# ─── experiment #10: parameter robustness + dollar-index ratios ──────────────
PARAM_GRID = {
    "z_windows": [40, 60, 90],
    "entries":   [1.5, 2.0, 2.5],
    "exits":     [0.0, 0.5, 1.0],
}


def param_grid_robustness(a: pd.Series, b: pd.Series, *, commission_pct: float,
                          slippage_pct: float, borrow_pct_annual: float,
                          window: int = 252, step: int = 63) -> list[dict]:
    """Run the ratio strategy over a grid of (z_window, entry, exit) and evaluate
    each. A real edge survives across MOST of the grid; an overfit one only at one
    lucky corner."""
    rows = []
    for zw in PARAM_GRID["z_windows"]:
        for en in PARAM_GRID["entries"]:
            for ex in PARAM_GRID["exits"]:
                if ex >= en:
                    continue
                r = ratio_strategy_returns(a, b, z_window=zw, entry=en, exit=ex,
                                           commission_pct=commission_pct, slippage_pct=slippage_pct,
                                           borrow_pct_annual=borrow_pct_annual)
                res = evaluate_hypothesis(f"z{zw}/e{en}/x{ex}", r, window, step)
                res.update({"z": zw, "entry": en, "exit": ex})
                rows.append(res)
    return rows


def _grid_summary(rows: list[dict]) -> tuple[int, int, float]:
    """(#combos that survive-ish, total, median OOS MAR). Survive-ish = OOS ret>0
    and walk-forward ≥ 50%."""
    valid = [r for r in rows if r.get("oos_mar") is not None]
    if not valid:
        return 0, 0, 0.0
    good = sum(1 for r in valid if r["oos_ret"] > 0 and r["wf_pct"] >= 50)
    mars = sorted(r["oos_mar"] for r in valid)
    med = mars[len(mars) // 2]
    return good, len(valid), round(med, 2)


def run_experiment10_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    robust_pair: tuple[str, str],
    usd_pairs: list[tuple[str, str]],
    limit: int = 2500,
    window: int = 252,
    step: int = 63,
) -> str:
    from datetime import datetime, timezone

    cache: dict[str, pd.DataFrame] = {}
    def _series(sym: str):
        if sym not in cache:
            try:
                d = get_ohlcv(sym, "1Day", limit)
                s = d["close"].sort_index()
                s.index = s.index.normalize()
                cache[sym] = s
            except Exception as e:
                logger.warning(f"Exp10: fetch {sym} failed: {e}")
                cache[sym] = pd.Series(dtype=float)
        return cache[sym]

    lines = [f"# Experiment #10 — GLD/GDX robustness + Dollar ratios "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]

    # Part A: parameter robustness of the candidate pair
    a_sym, b_sym = robust_pair
    a, b = _series(a_sym), _series(b_sym)
    lines.append(f"## Part A — {a_sym}/{b_sym} parameter robustness (overfit check)")
    if len(a) < 400 or len(b) < 400:
        lines.append("_insufficient data_\n")
    else:
        for label, comm, slip, borrow in [("base", 0.05, 0.03, 1.0), ("realistic", 0.05, 0.08, 3.0)]:
            grid = param_grid_robustness(a, b, commission_pct=comm, slippage_pct=slip,
                                         borrow_pct_annual=borrow, window=window, step=step)
            good, total, med = _grid_summary(grid)
            pct = round(100 * good / total) if total else 0
            robust = "✅ robust across parameters" if pct >= 60 else (
                     "⚠️ works only in part of the grid" if pct >= 35 else "❌ overfit (lucky params only)")
            lines.append(f"**{label} costs:** {good}/{total} parameter combos survive "
                         f"(OOS+, WF≥50%) · median OOS MAR {med} → {robust}")
        lines.append("")
        # compact grid at realistic costs
        grid = param_grid_robustness(a, b, commission_pct=0.05, slippage_pct=0.08,
                                     borrow_pct_annual=3.0, window=window, step=step)
        lines.append("| z-win | entry | exit | OOS ret% | OOS MAR | Walk-fwd |")
        lines.append("|--:|--:|--:|--:|--:|:--:|")
        for r in grid:
            if r.get("oos_mar") is None:
                continue
            lines.append(f"| {r['z']} | {r['entry']} | {r['exit']} | {r['oos_ret']:+.0f} | "
                         f"{r['oos_mar']} | {r['wf']} |")
        lines.append("")

    # Part B: dollar-index ratios (the user's idea, done correctly via UUP)
    lines.append("## Part B — Dollar-index ratios (commodity vs USD strength)")
    lines.append("_Note: GLD etc. are already priced in USD, so 'X/USD' is a directional bet. "
                 "The real market-neutral 'vs dollar' spread uses the dollar-index ETF (UUP)._")
    lines.append("")
    lines.append("| Ratio | Scenario | OOS ret% | OOS MAR | Walk-fwd | Verdict |")
    lines.append("|---|---|--:|--:|:--:|---|")
    for a_sym, b_sym in usd_pairs:
        a, b = _series(a_sym), _series(b_sym)
        if len(a) < 400 or len(b) < 400:
            lines.append(f"| {a_sym}/{b_sym} | — | | | | insufficient data |")
            continue
        for label, comm, slip, borrow in COST_SCENARIOS:
            r = ratio_strategy_returns(a, b, commission_pct=comm, slippage_pct=slip,
                                       borrow_pct_annual=borrow)
            res = evaluate_hypothesis(f"{a_sym}/{b_sym}", r, window, step)
            if res.get("oos_mar") is None:
                lines.append(f"| {a_sym}/{b_sym} | {label} | — | — | — | insufficient |")
                continue
            lines.append(f"| {a_sym}/{b_sym} | {label} | {res['oos_ret']:+.0f} | {res['oos_mar']} | "
                         f"{res['wf']} | {res['verdict']} |")
    lines.append("")
    lines.append("Verdict rule: GLD/GDX is only real if it survives across MOST of the parameter grid "
                 "at realistic costs — not just at the single combo used in experiment #9.")
    return "\n".join(lines)
