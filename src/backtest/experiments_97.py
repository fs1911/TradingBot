"""
Experiment #97 — stock-market Fear & Greed index (CNN-style), rebuilt from free data
(requested 20.11.2026 after the November chip crash).

CNN does not publish a long history, so the index is rebuilt from its seven ingredients with
Yahoo proxies. Each raw ingredient is oriented (high = greed) and turned into its percentile
rank within the previous 252 trading days (0–100); the index is the mean of the available ones.
  1 momentum      S&P 500 (SPY) vs its 125-day average
  2 strength      sector ETFs within 5 % of their 52-week high minus within 5 % of their low
  3 breadth       equal-weight (RSP) vs cap-weight (SPY), 20-day relative return
  4 options       VIX3M / VIX (term structure; low = fear)        [CNN: put/call ratio]
  5 volatility    − (VIX / its 50-day average)
  6 safe haven    SPY − IEF 20-day return (stocks vs Treasuries)
  7 junk bonds    HYG − IEF 20-day return                          [CNN: junk-bond spread]
Long version = 1, 2, 5, 6 (from ~2004); full version = all 7 (from ~2009). If CNN's own series can
be downloaded, the report shows the correlation with it.

Pre-registered tests (signal at the close of day t, entry at the close of day t+1):
  E events  extreme fear = index < 25, extreme greed = index > 75, counted when the zone is entered
            after ≥ 20 trading days outside it. Next 1 M / 3 M / 12 M return of SPY, QQQ, SMH
            vs all days; random-date bootstrap p; Holm over the 4 primary SPY tests
            (fear 3 M, fear 12 M, greed 3 M, greed 12 M).
  Q quintiles  index at month-ends (non-overlapping) → next-month SPY return per quintile.
  S strategies (SPY, net of 0.50 % per switch side ≈ Yuh; cash earns BIL when out):
            S1 avoid greed: out when index > 75, back in when < 50
            S2 buy fear: 70 % invested, 100 % when index < 25 until it is back > 50
            vs buy & hold and static 70 %.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SYMBOLS = ["SPY", "QQQ", "SMH", "^VIX", "^VIX3M", "IEF", "HYG", "RSP", "BIL"] + SECTORS
HORIZONS = {"1 M": 21, "3 M": 63, "12 M": 252}
FEAR, GREED, GAP = 25.0, 75.0, 20
LONG = ["momentum", "strength", "volatility", "safe haven"]


def _clean(s: pd.Series) -> pd.Series:
    s = s.dropna().astype(float)
    idx = s.index.tz_localize(None) if getattr(s.index, "tz", None) is not None else s.index
    s.index = pd.DatetimeIndex(idx).normalize()
    return s.groupby(level=0).last()


def components(px: dict) -> pd.DataFrame:
    """Raw oriented ingredients (high = greed) on SPY trading days."""
    spy = _clean(px["SPY"])
    idx = spy.index
    g = lambda s: _clean(px[s]).reindex(idx).ffill(limit=3) if s in px and len(px[s]) else pd.Series(np.nan, index=idx)
    out = pd.DataFrame(index=idx)
    out["momentum"] = spy / spy.rolling(125).mean() - 1
    hi, lo = [], []
    for s in SECTORS:
        p = g(s)
        mx, mn = p.rolling(252).max(), p.rolling(252).min()
        hi.append((p >= 0.95 * mx).astype(float).where(mx.notna()))
        lo.append((p <= 1.05 * mn).astype(float).where(mn.notna()))
    H, Lo = pd.concat(hi, axis=1), pd.concat(lo, axis=1)
    n = H.notna().sum(axis=1).astype(float)
    out["strength"] = ((H.sum(axis=1) - Lo.sum(axis=1)) / n.where(n > 0)).where(n >= 5)
    out["breadth"] = g("RSP").pct_change(20) - spy.pct_change(20)
    vix, vix3 = g("^VIX"), g("^VIX3M")
    out["options"] = vix3 / vix
    out["volatility"] = -(vix / vix.rolling(50).mean())
    ief = g("IEF")
    out["safe haven"] = spy.pct_change(20) - ief.pct_change(20)
    out["junk bonds"] = g("HYG").pct_change(20) - ief.pct_change(20)
    return out


def rolling_pct(x: pd.Series, win: int = 252) -> pd.Series:
    """Percentile (0–100) of today's value within the previous `win` days incl. today."""
    v = x.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    for i in range(win - 1, len(v)):
        w = v[i - win + 1:i + 1]
        w = w[np.isfinite(w)]
        if len(w) >= win // 2 and np.isfinite(v[i]):
            out[i] = 100.0 * (np.sum(w < v[i]) + 0.5 * np.sum(w == v[i])) / len(w)
    return pd.Series(out, index=x.index)


def fg_index(comp: pd.DataFrame, cols=None, min_n: int | None = None) -> pd.Series:
    cols = cols or list(comp.columns)
    sc = pd.concat({c: rolling_pct(comp[c]) for c in cols}, axis=1)
    need = min_n if min_n is not None else len(cols)
    return sc.mean(axis=1).where(sc.notna().sum(axis=1) >= need)


def zone_entries(ix: pd.Series, below: float | None = None, above: float | None = None, gap: int = GAP) -> list:
    """Dates when the index enters the zone after ≥ gap trading days outside it."""
    x = ix.dropna()
    inz = (x < below) if below is not None else (x > above)
    out, outside = [], gap
    for d, z in inz.items():
        if z and outside >= gap:
            out.append(d)
        outside = 0 if z else outside + 1
    return out


def fwd(px: pd.Series, n: int) -> pd.Series:
    """Return from the close of the NEXT day to n days later (entry one day after the signal)."""
    p = _clean(px)
    return p.shift(-(n + 1)) / p.shift(-1) - 1


def boot_p(base: np.ndarray, n: int, observed: float, reps: int = 5000, seed: int = 97) -> float:
    base = base[np.isfinite(base)]
    if n < 1 or len(base) < n or not np.isfinite(observed):
        return float("nan")
    m = base[np.random.default_rng(seed).integers(0, len(base), size=(reps, n))].mean(axis=1)
    c = m.mean()
    return float((np.abs(m - c) >= abs(observed - c)).mean())


def holm(p: dict) -> dict:
    items = sorted((v, k) for k, v in p.items() if np.isfinite(v))
    m, out, run = len(items), {}, 0.0
    for i, (v, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    return out


def strategy(spy: pd.Series, bil: pd.Series, ix: pd.Series, rule: str, cost_side: float = 0.005) -> pd.Series:
    """Daily returns; position decided at close t from the index, earns from t+1 → t+2."""
    spy = _clean(spy)
    r = spy.pct_change()
    rc = _clean(bil).reindex(spy.index).ffill().pct_change().fillna(0.0) if bil is not None and len(bil) else pd.Series(0.0, index=spy.index)
    x = ix.reindex(spy.index)
    w, cur = [], {"S1": 1.0, "S2": 0.7, "BH": 1.0, "70": 0.7}[rule]
    w0 = cur
    for v in x.to_numpy():
        if np.isfinite(v):
            if rule == "S1":
                cur = 0.0 if v > GREED else (1.0 if v < 50 else cur)
            elif rule == "S2":
                cur = 1.0 if v < FEAR else (0.7 if v > 50 else cur)
        w.append(cur)
    w = pd.Series(w, index=spy.index).shift(2).fillna(w0)   # decided at t, executed at t+1 close
    turn = w.diff().abs().fillna(0.0)
    out = w * r + (1 - w) * rc - cost_side * turn
    start = x.first_valid_index()
    return out[out.index > start].fillna(0.0)


def perf(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 250:
        return {"cagr": np.nan, "maxdd": np.nan, "sharpe": np.nan}
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    sd = r.std()
    return {"cagr": float(eq.iloc[-1] ** (1 / yrs) - 1), "maxdd": float((eq / eq.cummax() - 1).min()),
            "sharpe": float(r.mean() / sd * math.sqrt(252)) if sd > 0 else np.nan}


def parse_cnn(js: dict) -> pd.Series:
    """CNN graphdata JSON → daily Series (0–100)."""
    pts = (js.get("fear_and_greed_historical") or {}).get("data") or []
    if not pts:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(int(p["x"]), unit="ms").normalize(): float(p["y"]) for p in pts if "x" in p and "y" in p})
    return s.sort_index().groupby(level=0).last()


def run_experiment97_report(px: dict, cnn: pd.Series | None = None, diag: list | None = None) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #97 — stock-market Fear & Greed index, rebuilt ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    pc = lambda x: f"{100*x:+.1f} %" if np.isfinite(x) else "—"
    f = lambda x, d=2: f"{x:+.{d}f}" if np.isfinite(x) else "—"
    comp = components(px)
    full = fg_index(comp)
    long_ = fg_index(comp, LONG)
    L.append(f"Index history: long version (4 ingredients) from {long_.first_valid_index():%Y-%m-%d}, "
             f"full version (7) from {full.first_valid_index():%Y-%m-%d}." if full.first_valid_index() is not None else "Index history too short.")
    if cnn is not None and len(cnn):
        j = pd.concat([full.rename("ours"), cnn.rename("cnn")], axis=1).dropna()
        if len(j) > 50:
            L.append(f"Check vs CNN's own index ({len(j)} common days {j.index[0]:%Y-%m}–{j.index[-1]:%Y-%m}): "
                     f"correlation {j.corr().iloc[0, 1]:.2f}; both < 25 on the same day in "
                     f"{100*((j['ours'] < 25) & (j['cnn'] < 25)).sum() / max((j['cnn'] < 25).sum(), 1):.0f} % of CNN's extreme-fear days.")
    else:
        L.append("CNN's own series could not be downloaded — no direct check.")
    last = full.dropna()
    if len(last):
        d = last.index[-1]
        sc = {c: rolling_pct(comp[c]).get(d, np.nan) for c in comp.columns}
        L.append(f"**Latest ({d:%Y-%m-%d}): {last.iloc[-1]:.0f}** — " + ", ".join(f"{c} {v:.0f}" for c, v in sc.items() if np.isfinite(v)))
        lo20 = full.loc[d - pd.Timedelta(days=60):d]
        L.append(f"Lowest in the last 60 days: {lo20.min():.0f} on {lo20.idxmin():%Y-%m-%d}.")
    L.append("")
    # E events
    L.append("## 1 After entering extreme fear (< 25) / extreme greed (> 75) — vs all days (entry next day)")
    L.append("| index | zone | asset | events | " + " | ".join(f"{h} mean (all days) / beat-all p" for h in HORIZONS) + " |")
    L.append("|---|---|---|--:|" + "---|" * len(HORIZONS))
    pvals, keep = {}, {}
    for iname, ix in (("long", long_), ("full", full)):
        for zone, kw in (("fear < 25", {"below": FEAR}), ("greed > 75", {"above": GREED})):
            ev = zone_entries(ix, **kw)
            for a in ("SPY", "QQQ", "SMH"):
                if a not in px:
                    continue
                cells = []
                for h, n in HORIZONS.items():
                    fr = fwd(px[a], n)
                    base = fr[fr.index >= ix.first_valid_index()].dropna()
                    vals = fr.reindex(ev).dropna()
                    p = boot_p(base.to_numpy(), len(vals), vals.mean()) if len(vals) else np.nan
                    if iname == "long" and a == "SPY" and h in ("3 M", "12 M"):
                        pvals[f"{zone} {h}"] = p
                        keep[f"{zone} {h}"] = (vals.mean(), base.mean())
                    cells.append(f"{pc(vals.mean())} ({pc(base.mean())}) / {f(p, 3)}")
                L.append(f"| {iname} | {zone} | {a} | {len(ev)} | " + " | ".join(cells) + " |")
    adj = holm(pvals)
    L.append("")
    L.append("Primary (long index, SPY), Holm over 4: " + "; ".join(
        f"{k}: {pc(keep[k][0])} vs {pc(keep[k][1])}, p {f(pvals[k], 3)}, Holm {f(adj.get(k, np.nan), 3)}" for k in pvals))
    L.append("")
    # dates
    ev = zone_entries(long_, below=FEAR)
    L.append("Extreme-fear entries (long index) and SPY afterwards: " + ", ".join(
        f"{d:%Y-%m-%d} ({pc(fwd(px['SPY'], 63).get(d, np.nan))} 3 M)" for d in ev[-15:]))
    L.append("")
    # Q quintiles
    L.append("## 2 Month-end index quintile → next-month SPY return (non-overlapping)")
    me = long_.dropna().groupby(long_.dropna().index.to_period("M")).tail(1)
    nxt = fwd(px["SPY"], 21).reindex(me.index)
    dq = pd.DataFrame({"ix": me, "r": nxt}).dropna()
    if len(dq) > 50:
        dq["q"] = pd.qcut(dq["ix"].rank(method="first"), 5, labels=False) + 1
        L.append("| quintile | index range | months | next month mean | positive |")
        L.append("|---|---|--:|--:|--:|")
        for q, g in dq.groupby("q"):
            L.append(f"| Q{q} {'(fear)' if q == 1 else '(greed)' if q == 5 else ''} | {g['ix'].min():.0f}–{g['ix'].max():.0f} | {len(g)} | {pc(g['r'].mean())} | {100*(g['r'] > 0).mean():.0f} % |")
        a, b = dq.loc[dq["q"] == 1, "r"], dq.loc[dq["q"] == 5, "r"]
        se = math.sqrt(a.var() / len(a) + b.var() / len(b))
        L.append(f"- Q1 − Q5: {pc(a.mean() - b.mean())} per month (t {f((a.mean() - b.mean()) / se)})")
    L.append("")
    # S strategies
    L.append("## 3 Rules on SPY (long index; net of 0.50 % per switch side ≈ Yuh; out of market earns BIL)")
    L.append("| rule | CAGR | max drawdown | Sharpe | switches |")
    L.append("|---|--:|--:|--:|--:|")
    for nm, rule in (("buy & hold", "BH"), ("static 70 %", "70"), ("S1 avoid greed (out > 75, in < 50)", "S1"),
                     ("S2 buy fear (70 % → 100 % when < 25, back > 50)", "S2")):
        r = strategy(px["SPY"], px.get("BIL"), long_, rule)
        p = perf(r)
        L.append(f"| {nm} | {pc(p['cagr'])} | {100*p['maxdd']:.0f} % | {f(p['sharpe'])} | — |")
    L.append("")
    L.append("Reading: the index shows fear AFTER prices fell — so it cannot warn before a crash. The only useful "
             "question is whether buying in extreme fear (or leaving in extreme greed) paid off over many cases.")
    L.append("Caveats: rebuilt index (proxies, not CNN's exact formula); few independent events (crashes cluster); "
             "SPY/QQQ/SMH price returns; Yahoo history only.")
    return "\n".join(L)
