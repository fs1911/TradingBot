"""
Experiment #52 (H1) — the small investor's edge: do value, profitability and momentum
premia survive publication among SMALL companies but not among big ones?

Buffett: "with small money I could make 50 % a year" — because small companies are
too small for big funds. If so, factor premia should be larger and more persistent in
the smallest size quintile. Data: Kenneth French 25 portfolios (5 size × 5 characteristic,
value-weighted, monthly, from 1926/1963), free.

Pre-registered, per characteristic and size quintile: spread = high − low characteristic
(value: high B/M; profitability: high OP; momentum: winners) → mean p.a., t, before/after
publication (value 1992, momentum 1993, profitability 2013), 2010+; plus the long-only
"small & high" portfolio vs the market (excess return, Sharpe).
Caveat: the smallest NYSE quintile contains micro caps — trading costs/liquidity matter.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

FILES_25 = {"Value (B/M)": ("25_Portfolios_5x5_CSV.zip", 1992),
            "Profitability (OP)": ("25_Portfolios_ME_OP_5x5_CSV.zip", 2013),
            "Momentum (12-2)": ("25_Portfolios_ME_Prior_12_2_CSV.zip", 1993)}


def size_spreads(df: pd.DataFrame) -> dict:
    """25 columns in French order (size 1..5 × characteristic 1..5) →
    {size quintile: high − low spread series, ('small_high'|'big_high')}."""
    if df is None or df.empty or df.shape[1] < 25:
        return {}
    cols = list(df.columns[:25])
    out = {}
    for s in range(5):
        lo, hi = df[cols[5 * s]], df[cols[5 * s + 4]]
        out[s + 1] = hi - lo
    out["small_high"], out["big_high"] = df[cols[4]], df[cols[24]]
    return out


def ms(x: pd.Series) -> dict:
    x = x.dropna()
    if len(x) < 36 or x.std() == 0:
        return {"ann": float("nan"), "t": float("nan"), "sh": float("nan"), "n": len(x)}
    return {"ann": float(x.mean() * 12), "t": float(x.mean() / x.std() * math.sqrt(len(x))),
            "sh": float(x.mean() / x.std() * math.sqrt(12)), "n": len(x)}


def _p(x):
    return "—" if not np.isfinite(x) else f"{100*x:+.1f}%"


def run_experiment52_report(data: dict, ff5: pd.DataFrame | None, n_trials: int = 250) -> str:
    """data: {label: parsed 25-portfolio DataFrame}; ff5: French 5-factor frame (Mkt-RF, RF)."""
    from datetime import datetime, timezone
    L = [f"# Experiment #52 (H1) — factor premia in small vs big companies "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"Files loaded: {', '.join(k for k, v in data.items() if v is not None and not v.empty) or 'none'}. "
             f"Spread = high − low characteristic within each size quintile (value-weighted). "
             f"Bonferroni α/{n_trials}.")
    L.append("")
    summary = []
    for lbl, df in data.items():
        if df is None or df.empty:
            L.append(f"## {lbl}: no data")
            continue
        pub = FILES_25[lbl][1]
        sp = size_spreads(df)
        if not sp:
            L.append(f"## {lbl}: unexpected format ({df.shape[1]} columns)")
            continue
        L.append(f"## {lbl} — {df.index[0]} → {df.index[-1]}, published {pub}")
        L.append("| Size quintile | spread p.a. | t | before pub. | after pub. (t) | 2010+ (t) |")
        L.append("|---|--:|--:|--:|--:|--:|")
        for s in range(1, 6):
            x = sp[s]
            a, pre = ms(x), ms(x[x.index <= pd.Period(f"{pub}-12", "M")])
            post, rec = ms(x[x.index > pd.Period(f"{pub}-12", "M")]), ms(x[x.index >= pd.Period("2010-01", "M")])
            name = {1: "1 (smallest)", 5: "5 (biggest)"}.get(s, str(s))
            L.append(f"| {name} | {_p(a['ann'])} | {a['t']:.2f} | {_p(pre['ann'])} | {_p(post['ann'])} ({post['t']:.1f}) | "
                     f"{_p(rec['ann'])} ({rec['t']:.1f}) |")
            if s in (1, 5):
                summary.append((lbl, s, post["ann"], post["t"]))
        if ff5 is not None and not ff5.empty and {"Mkt-RF", "RF"} <= set(ff5.columns):
            rf, mkt = ff5["RF"], ff5["Mkt-RF"]
            for k, nm in (("small_high", "Long-only small & high"), ("big_high", "Long-only big & high")):
                x = (sp[k] - rf.reindex(sp[k].index)).dropna()
                post = x[x.index > pd.Period(f"{pub}-12", "M")]
                m_post = mkt.reindex(post.index).dropna()
                L.append(f"- {nm}: excess p.a. {_p(ms(x)['ann'])} (Sharpe {ms(x)['sh']:.2f}); after publication "
                         f"{_p(ms(post)['ann'])} (Sharpe {ms(post)['sh']:.2f}) vs market {_p(ms(m_post)['ann'])} "
                         f"(Sharpe {ms(m_post)['sh']:.2f})")
        L.append("")
    L.append("**Summary (after publication):** " + "; ".join(
        f"{l} size {'small' if s == 1 else 'big'} {_p(a)} (t {t:.1f})" for l, s, a, t in summary) + ".")
    return "\n".join(L)
