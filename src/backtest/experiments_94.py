"""
Experiment #94 — "second-order" chains: when the first link of a theme runs, does the next link
follow with a delay? (user idea 15.11.2026: AI → data centres → electricity / grid / uranium;
literature: Cohen & Frazzini 2008 "Economic links and predictable returns", Menzly & Ozbas 2010.)

Pre-registered (fixed before any result was seen):
  CHAINS   leader basket → follower basket, equal weight, monthly rebalanced, Yahoo price returns.
           Chosen for economic logic, including chains that did NOT pay off, not only the famous ones.
  Signals  at each month-end m, all excess vs SPY:
           L = leader basket return over the past h months, F = follower basket return past h months,
           Y = follower basket return over the NEXT h months. h = 1 (primary), 3, 6 (non-overlapping).
  Primary  pooled regression Y ~ L + F (F controls for the follower's own momentum), standard errors
           clustered by month; placebo = leaders shuffled between chains (500×, no chain keeps its own
           leader set) → p = share of placebo slopes ≥ the real one. Holm over h = 1, 3, 6.
  Sanity   contemporaneous slope (Y measured in the SAME months as L) — shows the link itself exists.
  Strategy each month hold the followers of every chain whose leader beat SPY last month while the
           follower lagged the leader (L > 0 and F < L); otherwise SPY. Net of 0.10 % and 0.50 % per
           trade side (0.50 % ≈ Yuh). Compared with SPY and with holding all followers always.
  Halves   ≤ 2017 / 2018 →.  Case table: the AI chains 2023–2024, month by month.
Caveats: survivorship and hindsight in the chain list (mitigated by the placebo and the 'boring'
chains); price returns (utilities' dividends missing → biased AGAINST power followers).
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

CHAINS = [  # (name, leaders, followers)
    ("AI chips → power producers", ["SMH"], ["VST", "NRG", "CEG", "XLU"]),
    ("AI chips → grid & electrical equipment", ["SMH"], ["ETN", "PWR", "HUBB", "VRT"]),
    ("AI chips → uranium / nuclear", ["SMH"], ["CCJ", "URA"]),
    ("Nvidia → data-centre REITs", ["NVDA"], ["EQIX", "DLR"]),
    ("TSMC → chip equipment", ["TSM"], ["ASML", "AMAT", "LRCX", "KLAC"]),
    ("Apple → Apple suppliers", ["AAPL"], ["SWKS", "QRVO", "CRUS", "AVGO"]),
    ("Tesla → lithium", ["TSLA"], ["ALB", "SQM", "LIT"]),
    ("gold → gold miners", ["GLD"], ["GDX"]),
    ("oil → oil services", ["USO"], ["OIH", "SLB", "HAL"]),
    ("bitcoin → crypto stocks", ["BTC-USD"], ["MARA", "RIOT", "COIN"]),
    ("homebuilders → building materials", ["ITB"], ["VMC", "MLM", "MAS"]),
    ("copper → copper miners", ["HG=F"], ["FCX", "COPX"]),
]
START = pd.Period("2010-01", "M")
AI_CHAINS = CHAINS[:3]


def all_symbols(chains=CHAINS) -> list:
    return sorted({s for _, a, b in chains for s in a + b} | {"SPY"})


def monthly_returns(px: dict) -> pd.DataFrame:
    """{symbol: daily closes} → monthly returns (PeriodIndex M)."""
    cols = {}
    for s, p in px.items():
        p = p.dropna()
        if len(p) < 40:
            continue
        idx = p.index.tz_localize(None) if getattr(p.index, "tz", None) is not None else p.index
        p = pd.Series(p.to_numpy(dtype=float), index=idx)
        me = p.groupby(p.index.to_period("M")).last()
        cols[s] = me.pct_change()
    return pd.DataFrame(cols).sort_index()


def basket(mret: pd.DataFrame, syms) -> pd.Series:
    have = [s for s in syms if s in mret]
    if not have:
        return pd.Series(np.nan, index=mret.index)
    return mret[have].mean(axis=1, skipna=True)


def _cum(r: pd.Series, h: int) -> pd.Series:
    """Compounded return over the h months ending at each month (NaN if any month missing)."""
    return np.exp(np.log1p(r).rolling(h, min_periods=h).sum()) - 1


def chain_panel(mret: pd.DataFrame, chains=CHAINS, h: int = 1, same_period: bool = False,
                start: pd.Period = START) -> pd.DataFrame:
    spy = mret["SPY"]
    rows = []
    for k, (name, lead, foll) in enumerate(chains):
        lb, fb = basket(mret, lead), basket(mret, foll)
        L = _cum(lb, h) - _cum(spy, h)
        F = _cum(fb, h) - _cum(spy, h)
        fut = (_cum(fb, h) - _cum(spy, h)).shift(-h)
        Y = F if same_period else fut  # same_period: follower in the same months as the leader move
        df = pd.DataFrame({"L": L, "F": F, "Y": Y})
        df = df[df.index >= start]
        if h > 1:
            df = df[[(p - start).n % h == 0 for p in df.index]]
        df = df.dropna()
        for m, r in df.iterrows():
            rows.append((m, k, name, r["L"], r["F"], r["Y"]))
    return pd.DataFrame(rows, columns=["month", "chain", "name", "L", "F", "Y"])


def ols_cluster(y: np.ndarray, X: np.ndarray, groups) -> tuple:
    """OLS with constant; returns (beta, se) clustered by group."""
    X = np.column_stack([np.ones(len(y)), X])
    XtX = np.linalg.pinv(X.T @ X)
    b = XtX @ X.T @ y
    u = y - X @ b
    g = pd.Series(range(len(y))).groupby(np.asarray(groups)).indices
    meat = np.zeros((X.shape[1], X.shape[1]))
    for idx in g.values():
        s = X[idx].T @ u[idx]
        meat += np.outer(s, s)
    G = len(g)
    V = XtX @ meat @ XtX * (G / max(G - 1, 1))
    return b, np.sqrt(np.clip(np.diag(V), 0, None))


def pooled(panel: pd.DataFrame, control: bool = True) -> dict:
    if len(panel) < 20:
        return {"b": np.nan, "t": np.nan, "n": len(panel)}
    X = panel[["L", "F"]].to_numpy() if control else panel[["L"]].to_numpy()
    b, se = ols_cluster(panel["Y"].to_numpy(), X, panel["month"].astype(str))
    return {"b": float(b[1]), "t": float(b[1] / se[1]) if se[1] > 0 else np.nan, "n": len(panel)}


def placebo(mret: pd.DataFrame, chains=CHAINS, h: int = 1, n: int = 500, seed: int = 94) -> np.ndarray:
    rng = np.random.default_rng(seed)
    leads = [tuple(c[1]) for c in chains]
    out = []
    tries = 0
    while len(out) < n and tries < n * 50:
        tries += 1
        perm = rng.permutation(len(chains))
        if any(leads[perm[i]] == leads[i] for i in range(len(chains))):
            continue
        fake = [(c[0], list(leads[perm[i]]), c[2]) for i, c in enumerate(chains)]
        out.append(pooled(chain_panel(mret, fake, h))["b"])
    return np.array(out, dtype=float)


def holm(ps: list) -> list:
    order = np.argsort(ps)
    adj, run = [np.nan] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def strategy(mret: pd.DataFrame, chains=CHAINS, cost_side: float = 0.0, always: bool = False,
             start: pd.Period = START) -> pd.Series:
    """Monthly returns of the 'follow the lagging link' rule (or all followers always)."""
    spy = mret["SPY"]
    sig = {}
    for k, (_, lead, foll) in enumerate(chains):
        L = basket(mret, lead) - spy
        F = basket(mret, foll) - spy
        sig[k] = (L > 0) & (F < L)
    out, prev = {}, {}
    months = [m for m in mret.index if m >= start]
    for i, m in enumerate(months[:-1]):
        nxt = months[i + 1]
        w = {}
        active = [k for k in range(len(chains)) if always or bool(sig[k].get(m, False))]
        for k in active:
            have = [s for s in chains[k][2] if s in mret and np.isfinite(mret.at[m, s]) and np.isfinite(mret.at[nxt, s])]
            for s in have:
                w[s] = w.get(s, 0.0) + 1.0 / (len(active) * len(have))
        tot = sum(w.values())
        if tot <= 0:
            w = {"SPY": 1.0}
        else:
            w = {s: v / tot for s, v in w.items()}
        r = sum(v * mret.at[nxt, s] for s, v in w.items())
        keys = set(w) | set(prev)
        turn = sum(abs(w.get(s, 0.0) - prev.get(s, 0.0)) for s in keys) if prev else 1.0
        out[nxt] = float(r) - cost_side * turn
        prev = w
    return pd.Series(out).sort_index()


def perf(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 12:
        return {"cagr": np.nan, "maxdd": np.nan, "sharpe": np.nan}
    eq = (1 + r).cumprod()
    sd = r.std()
    return {"cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1), "maxdd": float((eq / eq.cummax() - 1).min()),
            "sharpe": float(r.mean() / sd * math.sqrt(12)) if sd > 0 else np.nan}


def tstat(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std(ddof=1) * math.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def run_experiment94_report(mret: pd.DataFrame, diag: list | None = None, n_perm: int = 500) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #94 — second-order chains (does the next link follow?) ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    f = lambda x, d=2: f"{x:+.{d}f}" if np.isfinite(x) else "—"
    pc = lambda x: f"{100*x:+.1f} %" if np.isfinite(x) else "—"
    # 1 primary
    L.append("## 1 Primary: pooled slope of the follower's NEXT return on the leader's PAST return (vs SPY)")
    L.append("Control = follower's own past return. Placebo = leaders shuffled between chains. Holm over the 3 horizons.")
    L.append("| horizon | chain-periods | slope on leader | t (clustered) | placebo p | Holm p | without control: slope (t) |")
    L.append("|---|--:|--:|--:|--:|--:|--:|")
    res = {}
    for h in (1, 3, 6):
        pan = chain_panel(mret, CHAINS, h)
        p1, p0 = pooled(pan), pooled(pan, control=False)
        pl = placebo(mret, CHAINS, h, n=n_perm)
        pl = pl[np.isfinite(pl)]
        pp = float((1 + np.sum(pl >= p1["b"])) / (1 + len(pl))) if len(pl) and np.isfinite(p1["b"]) else np.nan
        res[h] = (pan, p1, p0, pp)
    hs = [h for h in res if np.isfinite(res[h][3])]
    adj = dict(zip(hs, holm([res[h][3] for h in hs]))) if hs else {}
    for h, (pan, p1, p0, pp) in res.items():
        L.append(f"| {h} M | {p1['n']:,} | {f(p1['b'], 3)} | {f(p1['t'])} | {f(pp, 3)} | {f(adj.get(h, np.nan), 3)} | "
                 f"{f(p0['b'], 3)} ({f(p0['t'])}) |")
    same = pooled(chain_panel(mret, CHAINS, 1, same_period=True), control=False)
    L.append("")
    L.append(f"- Sanity check, SAME month (is the link real at all?): slope {f(same['b'], 3)} (t {f(same['t'])}).")
    pan1 = res[1][0]
    a = pan1[pan1["month"] <= pd.Period("2017-12", "M")]
    b = pan1[pan1["month"] > pd.Period("2017-12", "M")]
    pa, pb = pooled(a), pooled(b)
    L.append(f"- Halves (1 M): ≤ 2017 slope {f(pa['b'], 3)} (t {f(pa['t'])}); 2018 → {f(pb['b'], 3)} (t {f(pb['t'])}).")
    L.append("")
    # 2 per chain
    L.append("## 2 Per chain (1 M): follower next month vs SPY, after the leader was up / down")
    L.append("| chain | months | same-month slope | next-month slope (t) | next month if leader up & follower lagged | otherwise | difference (t) |")
    L.append("|---|--:|--:|--:|--:|--:|--:|")
    for k, (name, _, _) in enumerate(CHAINS):
        g = pan1[pan1["chain"] == k]
        s0 = pooled(chain_panel(mret, [CHAINS[k]], 1, same_period=True), control=False)
        s1 = pooled(g, control=False) if len(g) >= 20 else {"b": np.nan, "t": np.nan}
        on = (g["L"] > 0) & (g["F"] < g["L"])
        y_on, y_off = g.loc[on, "Y"], g.loc[~on, "Y"]
        diff = y_on.mean() - y_off.mean() if len(y_on) > 2 and len(y_off) > 2 else np.nan
        se = math.sqrt(y_on.var() / len(y_on) + y_off.var() / len(y_off)) if np.isfinite(diff) else np.nan
        L.append(f"| {name} | {len(g)} | {f(s0['b'], 2)} | {f(s1['b'], 3)} ({f(s1['t'])}) | {pc(y_on.mean())} | "
                 f"{pc(y_off.mean())} | {pc(diff)} ({f(diff / se if se else np.nan)}) |")
    L.append("")
    # 3 strategy
    L.append("## 3 Rule: hold the lagging followers after the leader beat SPY, else SPY (monthly)")
    L.append("| portfolio | CAGR gross | net 0.10 %/side | net 0.50 %/side (≈ Yuh) | max drawdown | Sharpe | vs SPY per month (t) |")
    L.append("|---|--:|--:|--:|--:|--:|--:|")
    spy = mret["SPY"]
    for nm, alw in (("follow the lagging link", False), ("all followers always", True)):
        g0, g1, g5 = strategy(mret, cost_side=0.0, always=alw), strategy(mret, cost_side=0.001, always=alw), strategy(mret, cost_side=0.005, always=alw)
        p = perf(g0)
        ex = g5 - spy.reindex(g5.index)
        L.append(f"| {nm} | {pc(p['cagr'])} | {pc(perf(g1)['cagr'])} | {pc(perf(g5)['cagr'])} | {100*p['maxdd']:.0f} % | "
                 f"{f(p['sharpe'])} | {pc(ex.mean())} ({f(tstat(ex))}) net Yuh |")
    sp = spy[spy.index > START].dropna()
    ps = perf(sp)
    L.append(f"| SPY | {pc(ps['cagr'])} | — | — | {100*ps['maxdd']:.0f} % | {f(ps['sharpe'])} | — |")
    L.append("")
    # 4 AI case
    L.append("## 4 Case: the AI chains 2023–2024 (✔ = rule would hold the follower next month)")
    L.append("| month | chips vs SPY | " + " | ".join(f"{c[0].split('→')[1].strip()}: past / signal / next" for c in AI_CHAINS) + " |")
    L.append("|---|--:|" + "---|" * len(AI_CHAINS))
    lead = basket(mret, ["SMH"]) - spy
    for m in [p for p in mret.index if pd.Period("2023-01", "M") <= p <= pd.Period("2024-12", "M")]:
        cells = []
        for _, ld, fo in AI_CHAINS:
            F = basket(mret, fo) - spy
            lv, fv = lead.get(m, np.nan), F.get(m, np.nan)
            on = np.isfinite(lv) and np.isfinite(fv) and lv > 0 and fv < lv
            nx = F.shift(-1).get(m, np.nan)
            cells.append(f"{pc(fv)} / {'✔' if on else '·'} / {pc(nx)}")
        L.append(f"| {m} | {pc(lead.get(m, np.nan))} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("Reading: the question is not whether AI → electricity is a true story (it is), but whether the "
             "follower reacts LATER than the leader in a way one could trade after costs.")
    L.append("Caveats: chain list chosen with today's knowledge (hindsight) — the placebo and the non-AI chains "
             "guard against that only partly; price returns without dividends; current tickers only (survivorship); "
             "several AI chains share the same leader (SMH), so they are not independent.")
    return "\n".join(L)
