"""
Experiment #73 — cost mathematics for a Swiss saver (Yuh & co.): what do commission,
FX spread, stamp duty, fund fees and trading frequency do to the final wealth?

Real S&P 500 total return 1871–2023 (docs/finanzradar/sp500_real_monthly.json, same series
as #55), 500 CHF per month for 30 years, every start year; median and worst final real
wealth relative to a cost-free plan. Fee assumptions (public price lists, Oct 2026 — check
before use): Yuh commission 0.5 % (savings-plan ETFs 0 %), FX spread 0.95 % when the product
trades in a foreign currency, Swiss stamp duty 0.075 % (Swiss) / 0.15 % (foreign securities),
on buys and sells. Fund TER as stated. Active trading modelled as yearly turnover of the
portfolio, each round trip paying buy + sell costs.
Pure, no network.
"""
from __future__ import annotations
import json
import numpy as np

YUH_COMMISSION = 0.005
FX = 0.0095
STAMP_CH, STAMP_FOREIGN = 0.00075, 0.0015

SCENARIOS = [  # (label, cost per purchase, TER p.a., yearly turnover, cost per round trip)
    ("No costs at all (reference)", 0.0, 0.0, 0.0, 0.0),
    ("Yuh savings plan, CHF ETF, TER 0.07 %", STAMP_FOREIGN, 0.0007, 0.0, 0.0),
    ("Yuh savings plan, CHF ETF, TER 0.20 %", STAMP_FOREIGN, 0.0020, 0.0, 0.0),
    ("Yuh single buys, CHF ETF, TER 0.20 %", YUH_COMMISSION + STAMP_FOREIGN, 0.0020, 0.0, 0.0),
    ("Yuh single buys, USD ETF (FX 0.95 %), TER 0.07 %", YUH_COMMISSION + STAMP_FOREIGN + FX, 0.0007, 0.0, 0.0),
    ("Active fund TER 1.5 % (bank product)", STAMP_FOREIGN, 0.015, 0.0, 0.0),
    ("Savings plan + trading 50 % of the depot per year (CHF)", STAMP_FOREIGN, 0.0020, 0.5,
     2 * (YUH_COMMISSION + STAMP_FOREIGN)),
    ("Savings plan + trading 200 %/yr in USD stocks", STAMP_FOREIGN, 0.0020, 2.0,
     2 * (YUH_COMMISSION + STAMP_FOREIGN + FX)),
]


def load_real(path: str) -> np.ndarray:
    return np.array(json.load(open(path))["returns"], dtype=float)


def plan(real: np.ndarray, months: int, monthly: float, buy_cost: float, ter: float,
         turnover: float, rt_cost: float, sell_at_end: float = 0.0, step: int = 12) -> np.ndarray:
    """Final real wealth for every start (every `step` months)."""
    drag = (1 - ter / 12) * (1 - turnover / 12 * rt_cost)
    out = []
    for s in range(0, len(real) - months + 1, step):
        w = 0.0
        for x in real[s:s + months]:
            w = (w + monthly * (1 - buy_cost)) * (1 + x) * drag
        out.append(w * (1 - sell_at_end))
    return np.array(out)


def run_experiment73_report(real: np.ndarray, years: int = 30, monthly: float = 500.0) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #73 — cost mathematics for a Swiss saver ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"{monthly:.0f} CHF per month for {years} years, real S&P 500 total return 1871–2023, every start year "
             f"(results in today's money). Sale at the end pays commission + stamp duty once.")
    L.append("")
    base = plan(real, years * 12, monthly, 0, 0, 0, 0)
    L.append("| scenario | median final | vs no costs (median) | worst start | lost to costs (median, CHF) |")
    L.append("|---|--:|--:|--:|--:|")
    for lbl, buy, ter, to, rt in SCENARIOS:
        sell = 0.0 if buy == 0 else YUH_COMMISSION + STAMP_FOREIGN
        w = plan(real, years * 12, monthly, buy, ter, to, rt, sell)
        L.append(f"| {lbl} | {np.median(w):,.0f} | {100*(np.median(w)/np.median(base)-1):+.1f} % | {w.min():,.0f} | "
                 f"{np.median(base) - np.median(w):,.0f} |")
    L.append("")
    L.append("## What one percentage point costs")
    for ter in (0.0, 0.005, 0.01, 0.02):
        w = plan(real, years * 12, monthly, 0, ter, 0, 0)
        L.append(f"- {100*ter:.1f} % yearly cost → median {100*(np.median(w)/np.median(base)-1):+.1f} % final wealth")
    L.append("")
    L.append("Reading: one-off purchase costs (commission, stamp duty, even the 0.95 % FX spread) hurt much less than "
             "costs that repeat every year on the whole depot (fund fees, frequent trading). The FX spread matters "
             "mainly when it is paid again and again by trading.")
    return "\n".join(L)
