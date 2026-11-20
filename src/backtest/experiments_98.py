"""
Experiment #98 — the bitcoin lead, tested properly: do crypto stocks follow bitcoin with a delay?
Weekly instead of monthly, NEW stocks, ethereum as a second leader, full Yuh costs.
(requested 20.11.2026; hint from #94/#95: bitcoin → crypto stocks next month t ≈ 1.5–2.4, not proven.)

Pre-registered:
  Data     Yahoo daily closes put on US trading days (#95 alignment), week = last trading day of the
           week (Friday close); bitcoin/ethereum taken at that same day.
  Groups   A (primary, stocks NOT used before): IREN, CIFR, WULF, BTBT (from 2020-06, mining pivot),
             HIVE, BTDR — leader bitcoin.
           B leader ethereum → the same group-A stocks.
           C (descriptive) the #94/#95 stocks MARA, RIOT, COIN, CLSK, HUT (from 2018), MSTR (from 2020-09).
  Signal   L = leader's past-week return − SPY; F = stock's past-week return − SPY;
           Y = stock's NEXT-week return − SPY. Panel (one row per stock-week), OLS Y ~ L + F,
           standard errors clustered by week. Robustness 'skip 1 day': next week measured from
           Monday's close. Placebo: leader series circularly shifted by a random 8+ weeks (500×).
           Holm over 3 primary tests: A next week, A skip 1 day, B next week. Halves ≤ 2023 / 2024 →.
  Rule     hold the group-A basket (equal weight) for the next week when the leader beat SPY and the
           basket lagged the leader (L > 0 and F < L), else cash. Net of 1.45 % per side
           (Yuh 0.50 % + 0.95 % currency exchange) and of 0.10 % per side (cheap broker, reference);
           vs holding the basket and vs SPY.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_94 import ols_cluster
from .experiments_97 import holm   # dict version
from .experiments_95 import aligned_daily

GROUP_A = {"IREN": None, "CIFR": None, "WULF": None, "BTBT": "2020-06-01", "HIVE": None, "BTDR": None}
GROUP_C = {"MARA": "2018-01-01", "RIOT": "2018-01-01", "COIN": None, "CLSK": "2018-01-01", "HUT": "2018-01-01",
           "MSTR": "2020-09-01"}
SYMBOLS = ["SPY", "BTC-USD", "ETH-USD"] + list(GROUP_A) + list(GROUP_C)
YUH_SIDE, CHEAP_SIDE = 0.0145, 0.001


def weekly_frames(daily: pd.DataFrame) -> tuple:
    """→ (weekly returns, 'skip-first-day' weekly returns = first-day close → week-end close)."""
    per = daily.index.to_period("W-FRI")
    we, fd = daily.groupby(per).last(), daily.groupby(per).first()
    return we.pct_change(), we / fd - 1


def _starts(w: pd.DataFrame, starts: dict) -> pd.DataFrame:
    w = w.copy()
    for s, st in starts.items():
        if s in w and st:
            w.loc[w.index < pd.Period(st, "W-FRI"), s] = np.nan
    return w


def panel(wret: pd.DataFrame, wskip: pd.DataFrame, leader: str, stocks: dict, mode: str = "next",
          leader_series: pd.Series | None = None) -> pd.DataFrame:
    spy, spy_s = wret["SPY"], wskip["SPY"]
    L = (leader_series if leader_series is not None else wret[leader]) - spy
    wr, ws = _starts(wret, stocks), _starts(wskip, stocks)
    rows = []
    for s in stocks:
        if s not in wr:
            continue
        F = wr[s] - spy
        Y = (ws[s] - spy_s).shift(-1) if mode == "skip" else F.shift(-1)
        d = pd.DataFrame({"L": L, "F": F, "Y": Y}).dropna()
        d = d[(d["F"].abs() < 2) & (d["Y"].abs() < 2)]   # drop data errors (> ±200 % in a week)
        for wk, r in d.iterrows():
            rows.append((wk, s, r["L"], r["F"], r["Y"]))
    return pd.DataFrame(rows, columns=["week", "stock", "L", "F", "Y"])


def pooled(p: pd.DataFrame) -> dict:
    if len(p) < 30:
        return {"b": np.nan, "t": np.nan, "n": len(p)}
    b, se = ols_cluster(p["Y"].to_numpy(), p[["L", "F"]].to_numpy(), p["week"].astype(str))
    return {"b": float(b[1]), "t": float(b[1] / se[1]) if se[1] > 0 else np.nan, "n": len(p)}


def placebo(wret, wskip, leader, stocks, mode="next", n=500, seed=98) -> np.ndarray:
    rng = np.random.default_rng(seed)
    lead = wret[leader]
    v = lead.to_numpy()
    out = []
    for _ in range(n):
        k = int(rng.integers(8, max(9, len(v) - 8)))
        sh = pd.Series(np.roll(v, k), index=lead.index)
        out.append(pooled(panel(wret, wskip, leader, stocks, mode, leader_series=sh))["b"])
    return np.array(out, dtype=float)


def basket(wret: pd.DataFrame, stocks: dict) -> pd.Series:
    w = _starts(wret, stocks)
    have = [s for s in stocks if s in w]
    x = w[have].where(w[have].abs() < 2)
    return x.mean(axis=1, skipna=True).where(x.notna().sum(axis=1) >= 2)


def rule_returns(wret: pd.DataFrame, leader: str, stocks: dict, cost_side: float) -> pd.Series:
    spy = wret["SPY"]
    b = basket(wret, stocks)
    L, F = wret[leader] - spy, b - spy
    sig = ((L > 0) & (F < L)).astype(float).where(L.notna() & F.notna())
    pos = sig.shift(1)
    nxt = b
    valid = pos.notna() & nxt.notna()
    pos, nxt = pos[valid], nxt[valid]
    turn = pos.diff().abs().fillna(pos.iloc[0] if len(pos) else 0.0)
    return pos * nxt - cost_side * turn


def perf_w(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 52:
        return {"cagr": np.nan, "maxdd": np.nan, "sharpe": np.nan}
    eq = (1 + r).cumprod()
    sd = r.std()
    return {"cagr": float(eq.iloc[-1] ** (52 / len(r)) - 1), "maxdd": float((eq / eq.cummax() - 1).min()),
            "sharpe": float(r.mean() / sd * math.sqrt(52)) if sd > 0 else np.nan}


def run_experiment98_report(wret: pd.DataFrame, wskip: pd.DataFrame, diag: list | None = None, n_perm: int = 500) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #98 — bitcoin lead, weekly, new stocks ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    f = lambda x, d=2: f"{x:+.{d}f}" if np.isfinite(x) else "—"
    pc = lambda x: f"{100*x:+.2f} %" if np.isfinite(x) else "—"
    L.append("## 1 Primary: slope of the stock's NEXT-week return on the leader's PAST-week return (vs SPY, own week controlled)")
    L.append("| test | stock-weeks | weeks | slope | t (clustered by week) | placebo p (shifted leader) | Holm p | ≤ 2023 slope (t) | 2024 → slope (t) |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    tests = [("A bitcoin → new stocks, next week", "BTC-USD", GROUP_A, "next", True),
             ("A bitcoin → new stocks, skip Monday", "BTC-USD", GROUP_A, "skip", True),
             ("B ethereum → new stocks, next week", "ETH-USD", GROUP_A, "next", True),
             ("C bitcoin → #94/#95 stocks, next week (descriptive)", "BTC-USD", GROUP_C, "next", False),
             ("C bitcoin → #94/#95 stocks, skip Monday (descriptive)", "BTC-USD", GROUP_C, "skip", False)]
    rows, ps = [], {}
    for name, lead, st, mode, prim in tests:
        if lead not in wret:
            continue
        p = panel(wret, wskip, lead, st, mode)
        r = pooled(p)
        pl = placebo(wret, wskip, lead, st, mode, n=n_perm)
        pl = pl[np.isfinite(pl)]
        pp = float((1 + np.sum(pl >= r["b"])) / (1 + len(pl))) if len(pl) and np.isfinite(r["b"]) else np.nan
        a = pooled(p[p["week"] <= pd.Period("2023-12-29", "W-FRI")])
        b = pooled(p[p["week"] > pd.Period("2023-12-29", "W-FRI")])
        rows.append((name, p, r, pp, a, b, prim))
        if prim:
            ps[name] = pp
    adj = holm(ps)
    for name, p, r, pp, a, b, prim in rows:
        L.append(f"| {name} | {r['n']:,} | {p['week'].nunique() if len(p) else 0} | {f(r['b'], 3)} | {f(r['t'])} | {f(pp, 3)} | "
                 f"{f(adj.get(name, np.nan), 3) if prim else '—'} | {f(a['b'], 3)} ({f(a['t'])}) | {f(b['b'], 3)} ({f(b['t'])}) |")
    L.append("")
    L.append("## 2 Per stock (bitcoin, next week): mean next-week return vs SPY after signal (bitcoin beat SPY, stock lagged) vs otherwise")
    L.append("| stock | weeks | after signal | otherwise | difference (t) |")
    L.append("|---|--:|--:|--:|--:|")
    for st in (GROUP_A, GROUP_C):
        for s in st:
            g = panel(wret, wskip, "BTC-USD", {s: st[s]}, "next")
            if len(g) < 30:
                L.append(f"| {s} | {len(g)} | — | — | — |")
                continue
            on = (g["L"] > 0) & (g["F"] < g["L"])
            yo, yf = g.loc[on, "Y"], g.loc[~on, "Y"]
            d = yo.mean() - yf.mean()
            se = math.sqrt(yo.var() / len(yo) + yf.var() / len(yf)) if len(yo) > 2 and len(yf) > 2 else np.nan
            L.append(f"| {s}{' (A)' if st is GROUP_A else ' (C)'} | {len(g)} | {pc(yo.mean())} | {pc(yf.mean())} | {pc(d)} ({f(d / se if se else np.nan)}) |")
    L.append("")
    L.append("## 3 Rule: hold the group-A basket next week after bitcoin beat SPY and the basket lagged, else cash")
    L.append("| portfolio | weeks invested | CAGR | max drawdown | Sharpe |")
    L.append("|---|--:|--:|--:|--:|")
    for nm, lead in (("rule, bitcoin", "BTC-USD"), ("rule, ethereum", "ETH-USD")):
        if lead not in wret:
            continue
        for cn, c in (("gross", 0.0), ("net 0.10 %/side", CHEAP_SIDE), ("net Yuh 1.45 %/side", YUH_SIDE)):
            r = rule_returns(wret, lead, GROUP_A, c)
            p = perf_w(r)
            inv = int((rule_returns(wret, lead, GROUP_A, 0.0) != 0).sum())
            L.append(f"| {nm} {cn} | {inv} of {len(r)} | {pc(p['cagr'])} | {100*p['maxdd']:.0f} % | {f(p['sharpe'])} |")
    bk = basket(wret, GROUP_A).dropna()
    pb = perf_w(bk)
    L.append(f"| group-A basket always (no costs) | {len(bk)} | {pc(pb['cagr'])} | {100*pb['maxdd']:.0f} % | {f(pb['sharpe'])} |")
    sp = wret["SPY"].reindex(bk.index).dropna()
    ps_ = perf_w(sp)
    L.append(f"| SPY (same weeks) | {len(sp)} | {pc(ps_['cagr'])} | {100*ps_['maxdd']:.0f} % | {f(ps_['sharpe'])} |")
    L.append("")
    L.append("Reading: group A is the real test (stocks never looked at before). If its slope is not clearly positive, "
             "the #94/#95 hint was most likely chance. Group C only shows the old stocks at weekly frequency.")
    L.append("Caveats: young stocks (mostly 2021 →), very volatile; current tickers only (failed miners missing); "
             "bitcoin closes ≈ 3 h after US stocks even after alignment (the skip-Monday test removes that).")
    return "\n".join(L)
