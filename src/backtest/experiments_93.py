"""
Experiment #93 — "follow the government money": what did theme stocks do after big policy
announcements? (requested 15.11.2026)

Pre-registered list of announcements (date = first trading day on or after the event) and the
theme instruments that existed at the time. Measured vs SPY (excess, percentage points):
  run-up      6 months BEFORE the announcement (was the theme already hot?)
  +1 month, +1 year, +3 years after the announcement close
  worst drawdown of the theme instrument within 1 year after
Few cases (≈ 15) → descriptive, no significance test. Theme ETFs are equal-weighted per event.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

EVENTS = [  # (date, label, [yahoo symbols])
    ("2021-08-05", "US EV goal 50 % by 2030 (executive order)", ["DRIV", "LIT"]),
    ("2021-11-05", "US infrastructure bill passes House (1.2 tn)", ["PAVE"]),
    ("2022-02-24", "Russia invades Ukraine → defence spending", ["ITA", "XAR"]),
    ("2022-08-08", "Inflation Reduction Act passes Senate (clean energy)", ["ICLN", "TAN", "QCLN"]),
    ("2022-08-09", "CHIPS and Science Act signed (semiconductors)", ["SOXX", "SMH"]),
    ("2022-10-06", "US cannabis: pardons + rescheduling review", ["MSOS"]),
    ("2023-08-30", "US cannabis: HHS recommends rescheduling", ["MSOS"]),
    ("2025-01-21", "Stargate: 500 bn AI infrastructure", ["SMH", "AIQ"]),
    ("2025-03-04", "ReArm Europe (800 bn EU defence plan)", ["EUAD"]),
    ("2025-03-06", "US strategic bitcoin reserve (executive order)", ["BTC-USD"]),
    ("2025-05-23", "US executive orders to expand nuclear power", ["URA", "NLR"]),
    ("2025-07-10", "Pentagon equity deal with MP Materials (rare earths)", ["MP", "REMX"]),
    ("2026-05-28", "Pentagon ~75 bn drone budget request", ["RCAT", "UMAC"]),
]
WINDOWS = {"+1 M": 21, "+1 Y": 252, "+3 Y": 756}


def _at(px: pd.Series, d: pd.Timestamp):
    i = px.index.searchsorted(d)
    return i if i < len(px) else None


def event_row(px: dict, spy: pd.Series, date: str, syms: list) -> dict:
    d = pd.Timestamp(date)
    out = {"n_sym": 0}
    vals = {k: [] for k in ["pre"] + list(WINDOWS) + ["dd"]}
    for s in syms:
        p = px.get(s)
        if p is None or len(p) < 30:
            continue
        i = _at(p, d)
        if i is None or (p.index[i] - d).days > 7:
            continue
        out["n_sym"] += 1
        d0 = p.index[i]
        s0 = spy.asof(d0)
        # run-up: 126 trading days before
        if i >= 126:
            dp = p.index[i - 126]
            vals["pre"].append(p.iloc[i] / p.iloc[i - 126] - 1 - (s0 / spy.asof(dp) - 1))
        for k, n in WINDOWS.items():
            if i + n < len(p):
                d1 = p.index[i + n]
                vals[k].append(p.iloc[i + n] / p.iloc[i] - 1 - (spy.asof(d1) / s0 - 1))
        w = p.iloc[i:i + 253]
        vals["dd"].append(float((w / w.cummax() - 1).min()))
    for k, v in vals.items():
        out[k] = float(np.mean(v)) if v else np.nan
    return out


def run_experiment93_report(px: dict, spy: pd.Series, events=EVENTS) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #93 — follow the government money ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("Theme instruments vs SPY (percentage points). Run-up = 6 months before; drawdown = worst fall of the "
             "theme within 1 year after. '—' = not enough history yet.")
    L.append("")
    L.append("| date | announcement | instruments | run-up 6 M before | +1 M | +1 Y | +3 Y | worst fall within 1 Y |")
    L.append("|---|---|---|--:|--:|--:|--:|--:|")
    f = lambda x: f"{100*x:+.0f}" if np.isfinite(x) else "—"
    rows = []
    for date, label, syms in events:
        r = event_row(px, spy, date, syms)
        rows.append(r)
        L.append(f"| {date} | {label} | {', '.join(syms)} ({r['n_sym']}) | {f(r['pre'])} | {f(r['+1 M'])} | "
                 f"{f(r['+1 Y'])} | {f(r['+3 Y'])} | {f(r['dd'])} % |")
    y1 = [r["+1 Y"] for r in rows if np.isfinite(r["+1 Y"])]
    y3 = [r["+3 Y"] for r in rows if np.isfinite(r["+3 Y"])]
    pre = [r["pre"] for r in rows if np.isfinite(r["pre"])]
    L.append("")
    if y1:
        L.append(f"- +1 Y vs SPY: beat SPY in {sum(x > 0 for x in y1)} of {len(y1)} cases; median {100*np.median(y1):+.0f} pp, "
                 f"mean {100*np.mean(y1):+.0f} pp")
    if y3:
        L.append(f"- +3 Y vs SPY: beat SPY in {sum(x > 0 for x in y3)} of {len(y3)} cases; median {100*np.median(y3):+.0f} pp")
    if pre:
        L.append(f"- run-up before the announcement: median {100*np.median(pre):+.0f} pp vs SPY "
                 f"({sum(x > 0 for x in pre)} of {len(pre)} themes were already ahead)")
    L.append("")
    L.append("Caveats: few cases, hand-picked by importance (list fixed before looking at outcomes); ETFs "
             "are price returns; some themes overlap in time (2022 bear market).")
    return "\n".join(L)
