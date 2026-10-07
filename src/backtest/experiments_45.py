"""
Experiment #45 — the proposed Finanzradar signal, measured per asset.

Rule (monthly, at month-end): trend score = number of horizons (3, 6, 12 months)
in which the asset's total return beat cash (13-week T-bill). Displayed as
  score rises to ≥2 from ≤1 → ENTRY signal          score 3 → hold (full)
  score falls to 1 from ≥2  → PARTIAL sell          score 2 → hold (partial)
  score falls to 0          → EXIT signal
Optional confirmation: close above its 10-month average.

Per asset this measures what a user of the app would experience:
  - signals per year, time invested
  - average return 1/3/6/12 months after ENTRY and after EXIT signals vs the
    unconditional average (base rate)
  - false-signal rates: an entry reversed within 3 months at a loss; an exit
    reversed within 3 months at a higher price (missed gain)
  - following the signal (graded position score/3, and binary score≥2) vs buy &
    hold: CAGR, max drawdown, excess Sharpe, before/after 2013
  - placebo: the same position series circularly shifted (≥12 months) — is the
    TIMING better than chance?
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_38 import _naive

HORIZONS = (3, 6, 12)
COST_BPS = {"crypto": 25.0}
DEFAULT_COST_BPS = 10.0


def monthly_closes(daily: pd.Series) -> pd.Series:
    s = _naive(daily)
    return s.groupby(s.index.to_period("M")).last()


def monthly_cash(irx: pd.Series, index: pd.PeriodIndex) -> pd.Series:
    """^IRX (annual %) → monthly cash return earned during each month (yield at the
    previous month-end / 12). Missing → 0."""
    if irx is None or len(irx) == 0:
        return pd.Series(0.0, index=index)
    y = monthly_closes(irx).clip(lower=0)
    y = y.reindex(y.index.union(index)).ffill().reindex(index).fillna(0.0)
    return (y.shift(1).fillna(y) / 100.0 / 12.0)


def trend_score(px: pd.Series, cash: pd.Series, horizons=HORIZONS) -> pd.Series:
    """Score 0..3 at each month-end (NaN until the longest horizon is available)."""
    cash_idx = (1 + cash).cumprod()
    out = pd.Series(0.0, index=px.index)
    for h in horizons:
        r = px / px.shift(h) - 1
        c = cash_idx / cash_idx.shift(h) - 1
        out = out + (r > c).astype(float).where(r.notna())
    return out.where(px.shift(max(horizons)).notna())


def events(score: pd.Series) -> pd.DataFrame:
    s = score.dropna()
    prev = s.shift(1)
    kind = pd.Series("", index=s.index, dtype=object)
    kind[(prev <= 1) & (s >= 2)] = "entry"
    kind[(prev >= 2) & (s == 1)] = "partial"
    kind[(prev > 0) & (s == 0)] = "exit"
    return pd.DataFrame({"kind": kind, "score": s})[kind != ""]


def forward_returns(px: pd.Series, months=(1, 3, 6, 12)) -> pd.DataFrame:
    return pd.DataFrame({m: px.shift(-m) / px - 1 for m in months})


def false_rates(px: pd.Series, score: pd.Series, ev: pd.DataFrame, window: int = 3) -> tuple:
    """(false entry share, false exit share)."""
    fe = te = fx = tx = 0
    pos = {d: i for i, d in enumerate(score.index)}
    sc = score.to_numpy()
    p = px.reindex(score.index).to_numpy()
    for d, row in ev.iterrows():
        i = pos[d]
        nxt = range(i + 1, min(i + 1 + window, len(sc)))
        if row["kind"] == "entry":
            te += 1
            for j in nxt:
                if sc[j] <= 1:
                    fe += int(p[j] < p[i])
                    break
        elif row["kind"] == "exit":
            tx += 1
            for j in nxt:
                if sc[j] >= 2:
                    fx += int(p[j] > p[i])
                    break
    return (fe / te if te else float("nan")), (fx / tx if tx else float("nan"))


def follow(px: pd.Series, cash: pd.Series, w: pd.Series, cost_bps: float) -> pd.Series:
    """Monthly returns of holding weight w (decided at month-end t) during t+1."""
    r = px.pct_change()
    wl = w.shift(1).fillna(0.0)
    turn = wl.diff().abs().fillna(wl.abs())
    return (wl * r + (1 - wl) * cash - turn * cost_bps / 1e4).dropna()


def mstats(r: pd.Series, cash: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 24:
        return {}
    eq = (1 + r).cumprod()
    x = r - cash.reindex(r.index).fillna(0.0)
    sh = lambda z: float(z.mean() / z.std() * math.sqrt(12)) if len(z) > 24 and z.std() > 0 else float("nan")
    cut = pd.Period("2012-12", "M")
    return {"cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1), "maxdd": float((eq / eq.cummax() - 1).min()),
            "sharpe": sh(x), "pre": sh(x[x.index <= cut]), "post": sh(x[x.index > cut])}


def placebo_p(w: pd.Series, px: pd.Series, cash: pd.Series, min_shift: int = 12) -> tuple:
    """Timing edge Σ w_{t-1}(r_t − c_t) of the real series vs all circular shifts."""
    r = (px.pct_change() - cash).reindex(w.index)
    d = pd.concat({"w": w.shift(1), "x": r}, axis=1).dropna()
    if len(d) < 3 * min_shift:
        return float("nan"), float("nan"), np.array([])
    wv, xv = d["w"].to_numpy(), d["x"].to_numpy()
    n = len(xv)
    real = float(np.dot(wv, xv)) * 12 / n
    plc = np.array([np.dot(np.roll(wv, k), xv) * 12 / n for k in range(min_shift, n - min_shift + 1)])
    return real - float(plc.mean()), float((plc >= real).mean()), plc


def analyse_asset(name: str, cls: str, daily: pd.Series, irx: pd.Series, sma_confirm: bool = False) -> dict | None:
    if daily is None or len(daily) < 300:
        return None
    px = monthly_closes(daily)
    px = px[px > 0]
    if len(px) < 60:
        return None
    cash = monthly_cash(irx, px.index)
    score = trend_score(px, cash)
    if sma_confirm:
        above = px > px.rolling(10).mean()
        score = score.where(above | (score < 2), 1.0)  # without confirmation, ≥2 is capped at 1
    valid = score.dropna()
    px, cash = px.loc[valid.index], cash.loc[valid.index]
    ev = events(valid)
    fwd = forward_returns(px)
    base = fwd.mean()
    ent = fwd.loc[ev.index[ev["kind"] == "entry"]].mean()
    ext = fwd.loc[ev.index[ev["kind"] == "exit"]].mean()
    fe, fx = false_rates(px, valid, ev)
    cost = COST_BPS.get(cls, DEFAULT_COST_BPS)
    graded = follow(px, cash, valid / 3.0, cost)
    binary = follow(px, cash, (valid >= 2).astype(float), cost)
    bh = follow(px, cash, pd.Series(1.0, index=valid.index), 0.0)
    edge, p, plc = placebo_p(valid / 3.0, px, cash)
    years = len(valid) / 12
    return {"name": name, "cls": cls, "start": str(valid.index[0]), "years": years,
            "sig_py": len(ev) / years, "invested": float((valid / 3).mean()),
            "n_entry": int((ev["kind"] == "entry").sum()), "n_exit": int((ev["kind"] == "exit").sum()),
            "base": base, "ent": ent, "ext": ext, "false_entry": fe, "false_exit": fx,
            "graded": mstats(graded, cash), "binary": mstats(binary, cash), "bh": mstats(bh, cash),
            "edge": edge, "p": p, "plc": plc, "last_score": float(valid.iloc[-1]),
            "last_event": (f"{ev['kind'].iloc[-1]} {ev.index[-1]}" if len(ev) else "—")}


def _pct(x, d=1):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:+.{d}f}%"


def run_experiment45_report(assets: list, prices: dict, irx: pd.Series, n_trials: int = 210) -> str:
    """assets: [{name, yahoo, class}]; prices: {yahoo: daily Series}."""
    from datetime import datetime, timezone
    L = [f"# Experiment #45 — Finanzradar trend signal per asset "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("Score = # of 3/6/12-month horizons beating T-bills (^IRX). Entry: score rises to ≥2; partial: falls "
             "to 1; exit: falls to 0. Follow = graded position score/3 (binary: score≥2) vs buy & hold, monthly, "
             f"costs {DEFAULT_COST_BPS:.0f} bps (crypto 25). Placebo: same position series circularly shifted.")
    L.append("")
    res = [r for a in assets if (r := analyse_asset(a["name"], a["class"], prices.get(a["yahoo"]), irx))]
    res_c = {r["name"]: r for a in assets
             if (r := analyse_asset(a["name"], a["class"], prices.get(a["yahoo"]), irx, sma_confirm=True))}
    L.append(f"Assets analysed: {len(res)}/{len(assets)}. Cash data {'ok' if irx is not None and len(irx) > 100 else 'MISSING → 0%'}.")
    L.append("")
    L.append("### A — What a user sees: signals and what happened afterwards")
    L.append("| Asset | since | signals/yr | invested | entries | avg 12M after ENTRY | avg 12M after EXIT | "
             "avg 12M (all months) | false entries | false exits | current score |")
    L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for r in res:
        L.append(f"| {r['name']} | {r['start']} | {r['sig_py']:.1f} | {100*r['invested']:.0f}% | {r['n_entry']} | "
                 f"{_pct(r['ent'].get(12))} | {_pct(r['ext'].get(12))} | {_pct(r['base'].get(12))} | "
                 f"{_pct(r['false_entry'], 0)} | {_pct(r['false_exit'], 0)} | {r['last_score']:.0f} ({r['last_event']}) |")
    L.append("")
    L.append("### B — Following the signal vs buy & hold")
    L.append("| Asset | B&H CAGR / maxDD / Sharpe | graded CAGR / maxDD / Sharpe | binary CAGR / maxDD / Sharpe | "
             "+10M-SMA confirm Sharpe / maxDD | Sharpe ≤2012 (graded vs B&H) | Sharpe >2012 (graded vs B&H) | "
             "timing edge p.a. | placebo p |")
    L.append("|---|---|---|---|---|---|---|--:|--:|")
    crit = 0.05 / n_trials
    for r in res:
        b, g, y = r["bh"], r["graded"], r["binary"]
        c = res_c.get(r["name"], {}).get("graded", {})
        f = lambda s: f"{100*s['cagr']:+.1f}% / {100*s['maxdd']:.0f}% / {s['sharpe']:.2f}" if s else "—"
        L.append(f"| {r['name']} | {f(b)} | {f(g)} | {f(y)} | "
                 f"{c.get('sharpe', float('nan')):.2f} / {100*c.get('maxdd', float('nan')):.0f}% | "
                 f"{g.get('pre', float('nan')):.2f} vs {b.get('pre', float('nan')):.2f} | "
                 f"{g.get('post', float('nan')):.2f} vs {b.get('post', float('nan')):.2f} | "
                 f"{_pct(r['edge'])} | {r['p']:.3f} |")
    L.append("")
    L.append("### C — Summary by asset class (medians)")
    L.append("| Class | n | ΔmaxDD (graded − B&H) | ΔSharpe | ΔCAGR | 12M after entry − after exit | "
             "false entries | false exits | assets with placebo p<0.05 |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    rows = res + [dict(r, cls="ALL") for r in res]
    for cls in sorted({r["cls"] for r in rows}, key=lambda c: (c == "ALL", c)):
        sub = [r for r in rows if r["cls"] == cls and r["graded"] and r["bh"]]
        if not sub:
            continue
        md = lambda v: float(np.nanmedian(v)) if np.isfinite(np.asarray(v, dtype=float)).any() else float("nan")
        L.append(f"| {cls} | {len(sub)} | {_pct(md([r['graded']['maxdd'] - r['bh']['maxdd'] for r in sub]), 0)} | "
                 f"{md([r['graded']['sharpe'] - r['bh']['sharpe'] for r in sub]):+.2f} | "
                 f"{_pct(md([r['graded']['cagr'] - r['bh']['cagr'] for r in sub]))} | "
                 f"{_pct(md([r['ent'].get(12, np.nan) - r['ext'].get(12, np.nan) for r in sub]))} | "
                 f"{_pct(md([r['false_entry'] for r in sub]), 0)} | {_pct(md([r['false_exit'] for r in sub]), 0)} | "
                 f"{sum(r['p'] < 0.05 for r in sub)}/{len(sub)} |")
    L.append("")
    pooled = [r for r in res if len(r["plc"])]
    if pooled:
        rng = np.random.default_rng(45)
        real = np.mean([r["edge"] + r["plc"].mean() for r in pooled])
        draws = np.zeros(5000)
        for r in pooled:
            draws += r["plc"][rng.integers(0, len(r["plc"]), 5000)]
        draws /= len(pooled)
        p_pool = float((draws >= real).mean())
        L.append(f"Pooled placebo over {len(pooled)} assets: average timing edge "
                 f"{_pct(real - np.mean([r['plc'].mean() for r in pooled]), 2)} p.a., p = {p_pool:.4f} "
                 f"({'✅ beats chance' if p_pool < 0.05 else '❌ not distinguishable from chance'}; "
                 f"Bonferroni α/{n_trials} = {crit:.5f} → {'✅' if p_pool < crit else '❌'}).")
        L.append("")
    allp = [r["p"] for r in res if np.isfinite(r["p"])]
    better_dd = sum(r["graded"]["maxdd"] > r["bh"]["maxdd"] for r in res if r["graded"] and r["bh"])
    L.append(f"**Summary:** drawdown smaller than buy & hold in {better_dd}/{len(res)} assets; timing beats its "
             f"placebo (p<0.05) in {sum(p < 0.05 for p in allp)}/{len(allp)} (≈{0.05*len(allp):.1f} expected by "
             f"chance); after Bonferroni α/{n_trials}: {sum(p < crit for p in allp)}. Placebo p has a floor of "
             f"≈1/(months−24) per asset.")
    return "\n".join(L)
