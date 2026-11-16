"""
Experiment #95 — commodity → producer: does the producer follow its commodity with a delay?
(requested 16.11.2026; hypothesis from #94, where gold→miners, copper→miners and bitcoin→crypto
stocks looked positive but were not significant after 12 tests.)

Pre-registered:
  Group A (NEW commodities, the real test): silver, natural gas, Brent oil → E&P producers,
          grains → fertiliser / farm machinery, platinum+palladium → PGM miners, aluminium → smelters.
  Group B (replication with NEW stocks for the #94 leaders): gold → royalty companies,
          copper → other copper miners, bitcoin → bitcoin-treasury / other miners (from 2020-09).
  Group C (the #94 chains re-measured, descriptive only — they generated the hypothesis).
  Timing fix vs #94: every series is put on SPY's trading days before month-ends are taken, so a
  24/7 asset (bitcoin) cannot carry weekend moves into 'this month' that stocks only show next month.
  Measures (vs SPY): pooled slope of the follower's next-month return on the leader's past-month
          return, controlling for the follower's own past month; clustered by month; placebo =
          leaders shuffled within the group (500×). Robustness 'skip 1 day': the next-month return
          starts at the close of the first trading day (removes any closing-time effect).
          Holm over 4 primary tests (A, A skip, B, B skip). Halves ≤ 2017 / 2018 →.
  Rule as #94 (hold followers of chains whose leader beat SPY last month and the follower lagged,
          else SPY), groups A+B, net of 0.50 %/side ≈ Yuh, vs all followers always and SPY.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_94 import basket, _cum, pooled, holm, perf, tstat, strategy, START

# (name, leaders, followers, start)
GROUP_A = [
    ("silver → silver miners", ["SLV"], ["SIL", "PAAS", "AG", "HL"], "2010-01"),
    ("natural gas → gas producers", ["UNG"], ["EQT", "RRC", "AR", "CTRA"], "2010-01"),
    ("Brent oil → oil producers", ["BNO"], ["XOP", "COP", "EOG", "OXY"], "2010-01"),
    ("grains → fertiliser & farm machinery", ["DBA"], ["MOS", "CF", "NTR", "DE", "AGCO"], "2010-01"),
    ("platinum/palladium → PGM miners", ["PPLT", "PALL"], ["SBSW", "IMPUY"], "2010-01"),
    ("aluminium → aluminium smelters", ["ALI=F"], ["AA", "CENX"], "2010-01"),
]
GROUP_B = [
    ("gold → royalty companies", ["GLD"], ["FNV", "WPM", "RGLD"], "2010-01"),
    ("copper → other copper miners", ["HG=F"], ["SCCO", "TECK"], "2010-01"),
    ("bitcoin → treasury & other miners", ["BTC-USD"], ["MSTR", "CLSK", "HUT", "BITF"], "2020-09"),
]
GROUP_C = [
    ("#94 gold → gold miners", ["GLD"], ["GDX"], "2010-01"),
    ("#94 copper → copper miners", ["HG=F"], ["FCX", "COPX"], "2010-01"),
    ("#94 bitcoin → crypto stocks", ["BTC-USD"], ["MARA", "RIOT", "COIN"], "2014-10"),
]
GROUPS = {"A new commodities": GROUP_A, "B replication, new stocks": GROUP_B, "C #94 chains re-measured": GROUP_C}


def all_symbols() -> list:
    return sorted({s for g in GROUPS.values() for _, a, b, _ in g for s in a + b} | {"SPY"})


def aligned_daily(px: dict, ref: str = "SPY") -> pd.DataFrame:
    """All series on the reference trading days (last known value, at most 5 days stale)."""
    def clean(p):
        p = p.dropna()
        idx = p.index.tz_localize(None) if getattr(p.index, "tz", None) is not None else p.index
        return pd.Series(p.to_numpy(dtype=float), index=pd.DatetimeIndex(idx).normalize()).groupby(level=0).last()
    ref_idx = clean(px[ref]).index
    out = {}
    for s, p in px.items():
        c = clean(p)
        if len(c) < 40:
            continue
        out[s] = c.reindex(c.index.union(ref_idx)).ffill(limit=5).reindex(ref_idx)
        out[s][ref_idx < c.index[0]] = np.nan
    return pd.DataFrame(out)


def monthly_frames(daily: pd.DataFrame) -> tuple:
    """→ (monthly returns, 'skip-first-day' monthly returns = first-day close → month-end close)."""
    per = daily.index.to_period("M")
    me = daily.groupby(per).last()
    fd = daily.groupby(per).first()
    return me.pct_change(), me / fd - 1


def panel(mret: pd.DataFrame, skip: pd.DataFrame, chains, mode: str = "next") -> pd.DataFrame:
    """mode: next | skip | same. One row per (month, chain); L, F = past month vs SPY; Y outcome."""
    spy, spy_s = mret["SPY"], skip["SPY"]
    rows = []
    for k, (name, lead, foll, st) in enumerate(chains):
        L = basket(mret, lead) - spy
        F = basket(mret, foll) - spy
        if mode == "same":
            Y = F
        elif mode == "skip":
            Y = (basket(skip, foll) - spy_s).shift(-1)
        else:
            Y = F.shift(-1)
        df = pd.DataFrame({"L": L, "F": F, "Y": Y})
        df = df[df.index >= max(START, pd.Period(st, "M"))].dropna()
        for m, r in df.iterrows():
            rows.append((m, k, name, r["L"], r["F"], r["Y"]))
    return pd.DataFrame(rows, columns=["month", "chain", "name", "L", "F", "Y"])


def placebo(mret, skip, chains, mode="next", n=500, seed=95) -> np.ndarray:
    rng = np.random.default_rng(seed)
    leads = [tuple(c[1]) for c in chains]
    out, tries = [], 0
    while len(out) < n and tries < n * 50:
        tries += 1
        perm = rng.permutation(len(chains))
        if any(leads[perm[i]] == leads[i] for i in range(len(chains))):
            continue
        fake = [(c[0], list(leads[perm[i]]), c[2], c[3]) for i, c in enumerate(chains)]
        out.append(pooled(panel(mret, skip, fake, mode))["b"])
    return np.array(out, dtype=float)


def _signal_strategy(mret, chains, cost_side):
    # #94 rule; chain start dates respected by blanking followers before their start
    m2 = mret.copy()
    ch = []
    for name, lead, foll, st in chains:
        fo = []
        for s in foll:
            if s in m2:
                col = f"{s}@{st}"
                m2[col] = m2[s].where(m2.index >= pd.Period(st, "M"))
                fo.append(col)
        ch.append((name, lead, fo))
    return ch, m2


def run_experiment95_report(mret: pd.DataFrame, skip: pd.DataFrame, diag: list | None = None, n_perm: int = 500) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #95 — commodity → producer: does the producer follow later? ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    f = lambda x, d=2: f"{x:+.{d}f}" if np.isfinite(x) else "—"
    pc = lambda x: f"{100*x:+.1f} %" if np.isfinite(x) else "—"
    L.append("## 1 Primary: slope of the producer's NEXT month on the commodity's PAST month (vs SPY, own momentum controlled)")
    L.append("| group | timing | chain-months | slope | t (clustered) | placebo p | Holm p | same-month slope (t) | ≤ 2017 slope (t) | 2018 → slope (t) |")
    L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    rows, ps = [], []
    for gname, chains in GROUPS.items():
        for mode in ("next", "skip"):
            pan = panel(mret, skip, chains, mode)
            p = pooled(pan)
            pl = placebo(mret, skip, chains, mode, n=n_perm)
            pl = pl[np.isfinite(pl)]
            pp = float((1 + np.sum(pl >= p["b"])) / (1 + len(pl))) if len(pl) and np.isfinite(p["b"]) else np.nan
            same = pooled(panel(mret, skip, chains, "same"), control=False)
            a = pooled(pan[pan["month"] <= pd.Period("2017-12", "M")])
            b = pooled(pan[pan["month"] > pd.Period("2017-12", "M")])
            primary = not gname.startswith("C")
            rows.append([gname, mode, p, pp, same, a, b, primary])
            if primary:
                ps.append(pp)
    adj = iter(holm([x if np.isfinite(x) else 1.0 for x in ps]))
    for gname, mode, p, pp, same, a, b, primary in rows:
        hp = next(adj) if primary else np.nan
        L.append(f"| {gname} | {'next month' if mode == 'next' else 'skip 1st day'} | {p['n']:,} | {f(p['b'], 3)} | {f(p['t'])} | "
                 f"{f(pp, 3)} | {f(hp, 3) if primary else 'descriptive'} | {f(same['b'], 2)} ({f(same['t'])}) | "
                 f"{f(a['b'], 3)} ({f(a['t'])}) | {f(b['b'], 3)} ({f(b['t'])}) |")
    L.append("")
    L.append("## 2 Per chain: producer next month vs SPY after the commodity beat SPY and the producer lagged")
    L.append("| chain | months | same-month slope | next-month slope (t) | after signal | otherwise | difference (t) | skip-1st-day difference |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|")
    for gname, chains in GROUPS.items():
        for c in chains:
            g = panel(mret, skip, [c], "next")
            gs = panel(mret, skip, [c], "skip")
            if len(g) < 20:
                L.append(f"| {c[0]} | {len(g)} | — | — | — | — | — | — |")
                continue
            s0 = pooled(panel(mret, skip, [c], "same"), control=False)
            s1 = pooled(g, control=False)

            def dif(d):
                on = (d["L"] > 0) & (d["F"] < d["L"])
                yo, yf = d.loc[on, "Y"], d.loc[~on, "Y"]
                if len(yo) < 3 or len(yf) < 3:
                    return np.nan, np.nan, np.nan, np.nan
                df_ = yo.mean() - yf.mean()
                se = math.sqrt(yo.var() / len(yo) + yf.var() / len(yf))
                return yo.mean(), yf.mean(), df_, df_ / se if se > 0 else np.nan
            on_, off_, d_, t_ = dif(g)
            _, _, ds, ts = dif(gs)
            L.append(f"| {c[0]} | {len(g)} | {f(s0['b'], 2)} | {f(s1['b'], 3)} ({f(s1['t'])}) | {pc(on_)} | {pc(off_)} | "
                     f"{pc(d_)} ({f(t_)}) | {pc(ds)} ({f(ts)}) |")
    L.append("")
    L.append("## 3 Rule (groups A + B): hold lagging producers after the commodity beat SPY, else SPY")
    L.append("| portfolio | CAGR gross | net 0.50 %/side (≈ Yuh) | max drawdown | Sharpe | vs SPY per month net (t) |")
    L.append("|---|--:|--:|--:|--:|--:|")
    ch, m2 = _signal_strategy(mret, GROUP_A + GROUP_B, 0.0)
    spy = mret["SPY"]
    for nm, alw in (("follow the lagging producer", False), ("all producers always", True)):
        g0, g5 = strategy(m2, ch, 0.0, always=alw), strategy(m2, ch, 0.005, always=alw)
        p = perf(g0)
        ex = g5 - spy.reindex(g5.index)
        L.append(f"| {nm} | {pc(p['cagr'])} | {pc(perf(g5)['cagr'])} | {100*p['maxdd']:.0f} % | {f(p['sharpe'])} | {pc(ex.mean())} ({f(tstat(ex))}) |")
    sp = spy[spy.index > START].dropna()
    ps_ = perf(sp)
    L.append(f"| SPY | {pc(ps_['cagr'])} | — | {100*ps_['maxdd']:.0f} % | {f(ps_['sharpe'])} | — |")
    L.append("")
    L.append("Reading: group A is the real test (commodities not looked at before). Group B uses the #94 leaders "
             "with stocks not used in #94. Group C only shows whether the #94 hints survive the trading-day alignment.")
    L.append("Caveats: price returns without dividends; current tickers only (survivorship: bankrupt gas/coal/miners "
             "missing → biases producers upwards); futures (ALI=F, HG=F) are front-month continuation series with "
             "roll jumps; bitcoin closes ≈ 3 h after US stocks even after alignment.")
    return "\n".join(L)
