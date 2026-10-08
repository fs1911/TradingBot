"""
Experiment #46 — macro filters against the false signals of the trend score (#45).

#45: the 3/6/12-month trend score halves drawdowns in 35/35 assets but ~40% of its
signals reverse within 3 months and it costs ~1%/yr. Most false exits happen in
corrections WITHOUT a recession. Idea from the literature: let the trend take you out
only when an INDEPENDENT macro gauge confirms stress; otherwise stay invested.

Pre-registered rules (fixed from the literature, not tuned here). At each month-end t
using only data known at t (macro series lagged one month where they are published
with delay):
  F1 Growth-trend (unemployment): stress if US unemployment > its 12-month average
  F2 Credit spreads: stress if Moody's BAA − AAA spread > its 12-month average
  F3 Yield curve: stress if 10y − 3m Treasury spread was < 0 in any of the last 12 months
  F4 Volatility: stress if the VIX monthly average > 25
  F5 Valuation: stress if Shiller CAPE > its expanding median (only past data)
  F6 Macro vote: stress if ≥ 2 of F1, F2, F3
Position: stress → follow the trend (score/3); no stress → fully invested (1.0).

Measured per index: CAGR, max DD, excess Sharpe, before/after 2013, % invested,
exits per decade, false-exit rate, crisis returns; paired Sharpe bootstrap filtered vs
pure trend and vs buy & hold; PLACEBO = the same stress series circularly shifted
(same frequency of stress, random timing) — does the macro TIMING carry information?
Pure, injected for CI.
"""
from __future__ import annotations
import io
import math
import numpy as np
import pandas as pd

from .experiments_45 import monthly_closes, monthly_cash, trend_score, follow, mstats
from .experiments_43 import sharpe_diff_monthly

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
FRED_SERIES = ("UNRATE", "BAA", "AAA", "GS10", "TB3MS", "VIXCLS")
CRISES = (("1973–74", "1973-01", "1974-09"), ("1987", "1987-08", "1987-11"),
          ("2000–02", "2000-04", "2002-09"), ("2008–09", "2007-11", "2009-02"),
          ("2020", "2020-02", "2020-03"), ("2022", "2022-01", "2022-09"))


def fetch_fred(series: str, timeout: int = 20) -> pd.Series:
    import urllib.request
    try:
        req = urllib.request.Request(FRED + series, headers={"User-Agent": "Mozilla/5.0 (research)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return parse_fred_csv(r.read().decode("utf-8", "replace"))
    except Exception:
        return pd.Series(dtype=float)


def parse_fred_csv(text: str) -> pd.Series:
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception:
        return pd.Series(dtype=float)
    if df.shape[1] < 2:
        return pd.Series(dtype=float)
    idx = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    val = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx).dropna()
    return s[s.index.notna()].sort_index()


def to_monthly(s: pd.Series, how: str = "last") -> pd.Series:
    if s is None or len(s) == 0:
        return pd.Series(dtype=float)
    s = pd.Series(s).dropna()
    idx = pd.to_datetime(s.index)
    idx = idx.tz_localize(None) if idx.tz is not None else idx
    s.index = idx
    g = s.groupby(s.index.to_period("M"))
    return g.mean() if how == "mean" else g.last()


def stress_series(macro: dict, index: pd.PeriodIndex) -> dict:
    """{filter name: boolean Series on `index` (NaN where no data)}."""
    out = {}
    def align(s):
        # ffill only briefly: a series that ended (Shiller CAPE stops 2023) must not freeze its last state
        return s.reindex(s.index.union(index)).ffill(limit=3).reindex(index) if len(s) else pd.Series(np.nan, index=index)

    un = to_monthly(macro.get("UNRATE"))
    if len(un):
        st = (un > un.rolling(12).mean()).where(un.rolling(12).mean().notna())
        out["F1 unemployment"] = align(st.shift(1))      # published with ~1 month delay
    baa, aaa = to_monthly(macro.get("BAA")), to_monthly(macro.get("AAA"))
    if len(baa) and len(aaa):
        sp = (baa - aaa).dropna()
        st = (sp > sp.rolling(12).mean()).where(sp.rolling(12).mean().notna())
        out["F2 credit spread"] = align(st)
    g10, tb = to_monthly(macro.get("GS10")), to_monthly(macro.get("TB3MS"))
    if len(g10) and len(tb):
        curve = (g10 - tb).dropna()
        inv = (curve < 0).astype(float).rolling(12, min_periods=1).max() > 0
        out["F3 yield curve"] = align(inv.where(curve.notna()))
    vix = to_monthly(macro.get("VIXCLS"), "mean")
    if len(vix):
        out["F4 VIX>25"] = align(vix > 25)
    cape = macro.get("CAPE")
    if cape is not None and len(cape):
        c = to_monthly(cape)
        med = c.expanding(60).median()
        out["F5 CAPE>median"] = align((c > med).where(med.notna()).shift(1))
    parts = [out[k] for k in ("F1 unemployment", "F2 credit spread", "F3 yield curve") if k in out]
    if len(parts) == 3:
        df = pd.concat(parts, axis=1).astype(float)
        vote = (df.sum(axis=1) >= 2).where(df.notna().all(axis=1))
        out["F6 macro vote (≥2 of F1–F3)"] = vote
    return out


def filtered_weight(score: pd.Series, stress: pd.Series) -> pd.Series:
    """Stress → follow the trend (score/3); no stress → 1.0; unknown stress → trend."""
    w = score / 3.0
    return w.where(stress.reindex(score.index).fillna(1.0).astype(bool), 1.0)


def exits_and_false(px: pd.Series, w: pd.Series, window: int = 3) -> tuple:
    """Full exits per decade (weight falls to 0) and the share reversed within
    `window` months at a higher price."""
    w = w.dropna()
    exits = [i for i in range(1, len(w)) if w.iloc[i] == 0 and w.iloc[i - 1] > 0]
    p = px.reindex(w.index).to_numpy()
    false = 0
    for i in exits:
        for j in range(i + 1, min(i + 1 + window, len(w))):
            if w.iloc[j] > 0:
                false += int(p[j] > p[i])
                break
    dec = len(w) / 120
    return (len(exits) / dec if dec else float("nan")), (false / len(exits) if exits else float("nan"))


def placebo_filter(px, cash, score, stress, n_min: int = 24) -> tuple:
    """Sharpe of the filtered strategy vs the same strategy with the stress series
    circularly shifted (same stress frequency, random timing)."""
    s = stress.reindex(score.index)
    ok = s.notna() & score.notna()
    sc, st = score[ok], s[ok].astype(bool)
    if len(sc) < 3 * n_min:
        return float("nan"), float("nan")
    real = mstats(follow(px.loc[sc.index], cash.loc[sc.index], filtered_weight(sc, st), 10.0),
                  cash.loc[sc.index]).get("sharpe", float("nan"))
    vals = st.to_numpy()
    sh = []
    for k in range(n_min, len(vals) - n_min, max(1, (len(vals) - 2 * n_min) // 200)):
        sh.append(mstats(follow(px.loc[sc.index], cash.loc[sc.index],
                                filtered_weight(sc, pd.Series(np.roll(vals, k), index=sc.index)), 10.0),
                         cash.loc[sc.index]).get("sharpe", float("nan")))
    sh = np.array([v for v in sh if np.isfinite(v)])
    return real, float((sh >= real).mean()) if len(sh) else float("nan")


def crisis_ret(r: pd.Series, a: str, b: str) -> float:
    seg = r[(r.index >= pd.Period(a, "M")) & (r.index <= pd.Period(b, "M"))]
    return float((1 + seg).prod() - 1) if len(seg) >= 2 else float("nan")


def _p(x, d=0):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:+.{d}f}%"


def analyse_index(name: str, daily: pd.Series, irx: pd.Series, macro: dict, n_trials: int) -> list:
    L = [f"## {name}", ""]
    if daily is None or len(daily) < 300:
        return L + ["No data.", ""]
    px = monthly_closes(daily)
    cash = monthly_cash(irx, px.index)
    score = trend_score(px, cash).dropna()
    px, cash = px.loc[score.index], cash.loc[score.index]
    stresses = stress_series(macro, score.index)
    runs = {"Buy & hold": pd.Series(1.0, index=score.index), "Trend only (#45)": score / 3.0}
    for k, st in stresses.items():
        if st.notna().sum() >= 60:
            runs[k] = filtered_weight(score, st)
    rets = {k: follow(px, cash, w, 0.0 if k == "Buy & hold" else 10.0) for k, w in runs.items()}
    L.append(f"{score.index[0]} → {score.index[-1]}. Stress share: " +
             ", ".join(f"{k.split()[0]} {100*st.mean():.0f}%" for k, st in stresses.items() if st.notna().any()) + ".")
    L.append("")
    L.append("| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | "
             "ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    crit = 0.05 / n_trials
    for k, r in rets.items():
        s = mstats(r, cash)
        if not s:
            continue
        w = runs[k]
        ex, fx = exits_and_false(px, w)
        xr = r - cash.reindex(r.index)
        if k in ("Buy & hold", "Trend only (#45)"):
            dt = db = "—"
            pp = "—"
        else:
            x_tr = rets["Trend only (#45)"] - cash.reindex(rets["Trend only (#45)"].index)
            x_bh = rets["Buy & hold"] - cash.reindex(rets["Buy & hold"].index)
            a = sharpe_diff_monthly(xr, x_tr, n=1000)
            b = sharpe_diff_monthly(xr, x_bh, n=1000)
            dt = f"{a['obs']:+.2f} [{a['lo']:+.2f}, {a['hi']:+.2f}]"
            db = f"{b['obs']:+.2f} [{b['lo']:+.2f}, {b['hi']:+.2f}]"
            _, p = placebo_filter(px, cash, score, stresses[k])
            pp = f"{p:.3f}{' ✅' if p < crit else ''}" if np.isfinite(p) else "—"
        L.append(f"| {k} | {_p(s['cagr'], 1)} | {_p(s['maxdd'])} | {s['sharpe']:.2f} | {s['pre']:.2f} | "
                 f"{s['post']:.2f} | {100*w.mean():.0f}% | {ex:.1f} | {_p(fx)} | {dt} | {db} | {pp} |")
    L.append("")
    L.append("| Crisis | " + " | ".join(rets) + " |")
    L.append("|---|" + "--:|" * len(rets))
    for lbl, a, b in CRISES:
        vals = [crisis_ret(r, a, b) for r in rets.values()]
        if any(np.isfinite(v) for v in vals):
            L.append(f"| {lbl} | " + " | ".join(_p(v) for v in vals) + " |")
    L.append("")
    return L


def run_experiment46_report(indices: list, prices: dict, irx: pd.Series, macro: dict,
                            n_trials: int = 216) -> str:
    """indices: [{name, yahoo}]; macro: {FRED id: Series, 'CAPE': Series}."""
    from datetime import datetime, timezone
    L = [f"# Experiment #46 — macro filters against false trend signals "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    have = {k: (len(v) if v is not None else 0) for k, v in macro.items()}
    L.append("Macro data: " + ", ".join(f"{k} {'✓' if n else '✗'}" for k, n in have.items()) +
             f". Haircut α/{n_trials} = {0.05/n_trials:.5f} (placebo p floor ≈ 1/200).")
    L.append("Rule: stress → follow the 3/6/12M trend score; no stress → fully invested. "
             "Costs 10 bps per unit turnover. US macro data are applied to non-US indices too.")
    L.append("")
    for a in indices:
        L += analyse_index(a["name"], prices.get(a["yahoo"]), irx, macro, n_trials)
    return "\n".join(L)
