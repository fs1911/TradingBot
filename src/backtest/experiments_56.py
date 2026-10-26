"""
Experiment #56 — can an implementable portfolio beat the MSCI World on RETURN?

User goal: more return than the MSCI World (higher volatility acceptable); 2011–2026 must
be part of the evidence. Design (pre-registered before seeing any 2011–2026 number):

  Data A (main): Kenneth French DEVELOPED markets (23 countries ≈ MSCI World), monthly,
    1990 → 2026, long-only value-weighted 2×3 portfolios (what factor ETFs hold).
  Data B (robustness): the same portfolios for the US, 1963 → 2026.
  Data C (reality check): real ETFs incl. fees (Yahoo adjusted closes) 2009/2014 → today.

Candidates (long-only, monthly rebalanced, costs subtracted p.a.):
  P1 Momentum big        big-cap winners (≈ MSCI World Momentum)       cost 1.0 %
  P2 Quality big         big-cap robust profitability (≈ Quality ETF)  cost 0.5 %
  P3 Small value         small-cap high book/market                    cost 0.8 %
  P4 Small momentum      small-cap winners                             cost 1.5 %
  P5 Multi-factor 3      ⅓ each P1, P2, P3                             costs of legs
  P6 Multi-factor 4      ¼ each P1–P4                                  costs of legs
  P7 Factor momentum     each month the 2 of {P1–P4, big value, market} with the best
                         return over the past 12 months (Ehsani & Linnainmaa 2019),
                         costs of legs + 0.2 % per leg switch
  Benchmark: market (value-weighted, all developed stocks) − 0.15 % p.a.

Blind selection rule: the candidate with the highest NET excess over the market in
1990–2010 (in-sample) is "the portfolio". Its 2011–2026 result (out-of-sample) decides.
A candidate counts as robust only if it beats the market in BOTH halves AND in the US.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

FILES = {  # label → candidate file names (French renames files occasionally)
    "dev_bm": ["Developed_6_Portfolios_ME_BE-ME_CSV.zip"],
    "dev_op": ["Developed_6_Portfolios_ME_OP_CSV.zip"],
    "dev_mom": ["Developed_6_Portfolios_ME_Prior_12_2_CSV.zip"],
    "dev_ff": ["Developed_5_Factors_CSV.zip", "Developed_3_Factors_CSV.zip"],
    "us_bm": ["6_Portfolios_2x3_CSV.zip"],
    "us_op": ["6_Portfolios_ME_OP_2x3_CSV.zip"],
    "us_mom": ["6_Portfolios_ME_Prior_12_2_CSV.zip"],
    "us_ff": ["F-F_Research_Data_5_Factors_2x3_CSV.zip", "F-F_Research_Data_Factors_CSV.zip"],
}
COSTS = {"P1 Momentum big": 0.010, "P2 Quality big": 0.005, "P3 Small value": 0.008,
         "P4 Small momentum": 0.015, "Big value": 0.005, "Market": 0.0015}
SWITCH_COST = 0.002
SPLIT = pd.Period("2010-12", "M")
ETFS_EUR = {"MSCI World (EUNL)": "EUNL.DE", "World Momentum (IS3R)": "IS3R.DE",
            "World Quality (IS3Q)": "IS3Q.DE", "World Value (IS3S)": "IS3S.DE",
            "World Small Cap (IUSN)": "IUSN.DE", "US Small Cap Value (ZPRV)": "ZPRV.DE",
            "Nasdaq-100 (EQQQ, hindsight control)": "EQQQ.DE"}
ETFS_USD = {"MSCI World (URTH)": "URTH", "S&P 500 (SPY)": "SPY", "US Momentum (MTUM)": "MTUM",
            "US Quality (QUAL)": "QUAL", "US Small Value (IJS)": "IJS", "US Small Value (AVUV)": "AVUV"}


def legs(bm: pd.DataFrame, op: pd.DataFrame, mom: pd.DataFrame, ff: pd.DataFrame) -> pd.DataFrame:
    """6-portfolio files (Small Lo/Mid/Hi, Big Lo/Mid/Hi; positional) + factors → gross legs."""
    out = {}
    if mom is not None and mom.shape[1] >= 6:
        out["P1 Momentum big"], out["P4 Small momentum"] = mom.iloc[:, 5], mom.iloc[:, 2]
    if op is not None and op.shape[1] >= 6:
        out["P2 Quality big"] = op.iloc[:, 5]
    if bm is not None and bm.shape[1] >= 6:
        out["P3 Small value"], out["Big value"] = bm.iloc[:, 2], bm.iloc[:, 5]
    if ff is not None and {"Mkt-RF", "RF"} <= set(ff.columns):
        out["Market"], out["RF"] = ff["Mkt-RF"] + ff["RF"], ff["RF"]
    return pd.DataFrame(out).dropna()


def net(r: pd.Series, cost_pa: float) -> pd.Series:
    return r - cost_pa / 12


def factor_momentum(L: pd.DataFrame, pool: list, k: int = 2, lookback: int = 12) -> tuple:
    """Hold the k pool legs with the best trailing `lookback`-month return (known at t−1).
    Returns (net return series, average switches per year)."""
    g = (1 + L[pool]).rolling(lookback).apply(np.prod, raw=True) - 1
    rows, prev, switches = {}, set(), 0
    for i in range(lookback, len(L)):
        past = g.iloc[i - 1].dropna()
        if len(past) < k:
            continue
        pick = set(past.nlargest(k).index)
        changed = len(pick - prev) if prev else 0
        switches += changed
        cost = sum(COSTS.get(p, 0.005) for p in pick) / k / 12 + changed * SWITCH_COST / k
        rows[L.index[i]] = float(L.iloc[i][list(pick)].mean()) - cost
        prev = pick
    s = pd.Series(rows, dtype=float)
    yrs = len(s) / 12
    return s, (switches / yrs if yrs else float("nan"))


def candidates(L: pd.DataFrame) -> tuple:
    """{name: net monthly returns}, net market, switches/yr of P7."""
    c = {}
    for p in ("P1 Momentum big", "P2 Quality big", "P3 Small value", "P4 Small momentum"):
        if p in L:
            c[p] = net(L[p], COSTS[p])
    if {"P1 Momentum big", "P2 Quality big", "P3 Small value"} <= set(c):
        c["P5 Multi-factor 3"] = (c["P1 Momentum big"] + c["P2 Quality big"] + c["P3 Small value"]) / 3
    if {"P1 Momentum big", "P2 Quality big", "P3 Small value", "P4 Small momentum"} <= set(c):
        c["P6 Multi-factor 4"] = (c["P1 Momentum big"] + c["P2 Quality big"] + c["P3 Small value"]
                                  + c["P4 Small momentum"]) / 4
    pool = [p for p in ("P1 Momentum big", "P2 Quality big", "P3 Small value", "P4 Small momentum",
                        "Big value", "Market") if p in L]
    sw = float("nan")
    if len(pool) >= 3:
        c["P7 Factor momentum"], sw = factor_momentum(L, pool)
    mkt = net(L["Market"], COSTS["Market"]) if "Market" in L else None
    return c, mkt, sw


def cagr(r: pd.Series) -> float:
    r = r.dropna()
    return float((1 + r).prod() ** (12 / len(r)) - 1) if len(r) >= 12 else float("nan")


def stats(r: pd.Series, mkt: pd.Series, rf: pd.Series | None = None) -> dict:
    d = pd.concat([r, mkt], axis=1, keys=["r", "m"]).dropna()
    if len(d) < 24:
        return {"n": len(d)}
    ex = d["r"] - d["m"]
    eq = (1 + d["r"]).cumprod()
    rel = (1 + d["r"]).cumprod() / (1 + d["m"]).cumprod()
    under, longest = 0, 0
    peak = rel.cummax()
    for v, pk in zip(rel, peak):
        under = under + 1 if v < pk else 0
        longest = max(longest, under)
    roll = (1 + d).rolling(60).apply(np.prod, raw=True)
    win5 = float((roll["r"] > roll["m"]).mean()) if len(d) >= 60 else float("nan")
    rfa = rf.reindex(d.index).fillna(0) if rf is not None else 0.0
    exr = d["r"] - rfa
    return {"n": len(d), "cagr": cagr(d["r"]), "mcagr": cagr(d["m"]),
            "diff": cagr(d["r"]) - cagr(d["m"]),
            "t": float(ex.mean() / ex.std() * math.sqrt(len(ex))) if ex.std() > 0 else float("nan"),
            "sh": float(exr.mean() / exr.std() * math.sqrt(12)) if exr.std() > 0 else float("nan"),
            "dd": float((eq / eq.cummax() - 1).min()), "reldd": float((rel / peak - 1).min()),
            "longest": longest, "win5": win5,
            "years_won": float(((1 + d).groupby(d.index.year).prod().pipe(lambda y: (y["r"] > y["m"]).mean())))}


def _p(x, d=1):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:+.{d}f}%"


def _row(name: str, s: dict) -> str:
    if s.get("n", 0) < 24:
        return f"| {name} | {s.get('n', 0)} | — | — | — | — | — | — | — | — |"
    return (f"| {name} | {s['n']} | {_p(s['cagr'])} | **{_p(s['diff'])}** | {s['t']:.2f} | {s['sh']:.2f} | "
            f"{100*s['dd']:.0f}% | {100*s['reldd']:.0f}% / {s['longest']} M | {_p(s['win5'], 0).lstrip('+')} | "
            f"{100*s['years_won']:.0f}% |")


HEAD = ("| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | "
        "5-y windows won | years won |", "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")


def region_tables(L: pd.DataFrame, label: str) -> tuple:
    """→ (markdown lines, {period: {name: stats}})."""
    c, mkt, sw = candidates(L)
    out, res = [], {}
    if mkt is None or not c:
        return [f"### {label}: data missing ({', '.join(L.columns) or 'none'})", ""], res
    rf = L.get("RF")
    periods = [("full", L.index[0], L.index[-1]), ("in-sample ≤2010", L.index[0], SPLIT),
               ("OUT-OF-SAMPLE 2011→", SPLIT + 1, L.index[-1]), ("2016→", pd.Period("2016-01", "M"), L.index[-1])]
    for pname, a, b in periods:
        out.append(f"### {label} — {pname} ({a} → {b})")
        out += HEAD
        res[pname] = {}
        for name, r in c.items():
            s = stats(r[(r.index >= a) & (r.index <= b)], mkt[(mkt.index >= a) & (mkt.index <= b)], rf)
            res[pname][name] = s
            out.append(_row(name, s))
        m = mkt[(mkt.index >= a) & (mkt.index <= b)]
        out.append(f"| Market (benchmark, net 0.15 %) | {len(m)} | {_p(cagr(m))} | — | — | — | — | — | — | — |")
        out.append("")
    out.append(f"P7 factor momentum switched {sw:.1f} legs per year on average.")
    out.append("")
    return out, res


def etf_table(prices: dict, bench: str) -> list:
    """Real ETFs (adjusted closes, fees included) vs the benchmark ETF over each common window."""
    L = []
    if bench not in prices or prices[bench] is None or len(prices[bench]) < 300:
        return [f"Benchmark {bench}: no data.", ""]
    from .experiments_53_55 import monthly_from_daily
    b = monthly_from_daily(prices[bench]).pct_change().dropna()
    L.append("| ETF | from | CAGR | benchmark CAGR | difference p.a. | max DD | years won |")
    L.append("|---|---|--:|--:|--:|--:|--:|")
    rets = {}
    for name, s in prices.items():
        if name == bench or s is None or len(s) < 300:
            if name != bench:
                L.append(f"| {name} | no data | — | — | — | — | — |")
            continue
        r = monthly_from_daily(s).pct_change().dropna()
        st = stats(r, b)
        rets[name] = r
        if st.get("n", 0) < 24:
            L.append(f"| {name} | too short | — | — | — | — | — |")
            continue
        start = r.index[0]
        L.append(f"| {name} | {start} | {_p(st['cagr'])} | {_p(st['mcagr'])} | **{_p(st['diff'])}** | "
                 f"{100*st['dd']:.0f}% | {100*st['years_won']:.0f}% |")
    L.append("")
    return L, rets, b


def run_experiment56_report(frames: dict, loaded: dict, etf_eur: dict, etf_usd: dict, n_trials: int = 270) -> str:
    """frames: {label from FILES: parsed DataFrame or None}; loaded: {label: file used or None};
    etf_eur / etf_usd: {display name: daily adjusted close Series}."""
    from datetime import datetime, timezone
    R = [f"# Experiment #56 — can an implementable portfolio beat the MSCI World on return? "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    R.append("Files: " + ", ".join(f"{k} → {v or 'MISSING'}" for k, v in loaded.items()) + ".")
    R.append(f"All returns NET of pre-registered costs (momentum 1.0 %, small momentum 1.5 %, small value 0.8 %, "
             f"quality 0.5 %, market 0.15 % p.a.; factor momentum + 0.2 % per switch). Bonferroni α/{n_trials} → "
             f"|t| ≳ 3.7. 'Worst lag' = deepest fall of the portfolio RELATIVE to the market; 'longest' = months "
             f"below its previous relative high.")
    R.append("")
    res = {}
    for reg, label in (("dev", "A Developed markets (≈ MSCI World)"), ("us", "B USA (robustness)")):
        L = legs(frames.get(f"{reg}_bm"), frames.get(f"{reg}_op"), frames.get(f"{reg}_mom"), frames.get(f"{reg}_ff"))
        R.append(f"## {label}")
        if L.empty:
            R += ["Data missing.", ""]
            continue
        lines, res[reg] = region_tables(L, label)
        R += lines

    R.append("## Blind selection (pre-registered)")
    dev = res.get("dev", {})
    ins, oos = dev.get("in-sample ≤2010", {}), dev.get("OUT-OF-SAMPLE 2011→", {})
    ranked = sorted(((v["diff"], k) for k, v in ins.items() if v.get("n", 0) >= 24 and np.isfinite(v.get("diff", np.nan))),
                    reverse=True)
    if ranked:
        best = ranked[0][1]
        o = oos.get(best, {})
        R.append(f"Best in 1990–2010: **{best}** ({_p(ranked[0][0])} p.a. vs market). "
                 f"Its out-of-sample 2011→ result: **{_p(o.get('diff', np.nan))} p.a.** (t {o.get('t', float('nan')):.2f}), "
                 f"CAGR {_p(o.get('cagr', np.nan))} vs market {_p(o.get('mcagr', np.nan))}.")
    robust = []
    us = res.get("us", {})
    for k in ins:
        a, b = ins.get(k, {}).get("diff", np.nan), oos.get(k, {}).get("diff", np.nan)
        u = us.get("full", {}).get(k, {}).get("diff", np.nan)
        if all(np.isfinite(x) and x > 0 for x in (a, b, u)):
            robust.append(f"{k} (≤2010 {_p(a)}, 2011→ {_p(b)}, US {_p(u)})")
    R.append("Robust (beats market ≤2010 AND 2011→ AND in the US, after costs): "
             + ("; ".join(robust) if robust else "**none**") + ".")
    R.append("")

    R.append("## C Reality check with real ETFs (fees included, adjusted closes)")
    for title, px, bench in (("EUR listings (Xetra) vs iShares Core MSCI World", etf_eur, "MSCI World (EUNL)"),
                             ("USD listings vs iShares MSCI World", etf_usd, "MSCI World (URTH)")):
        R.append(f"### {title}")
        out = etf_table(px, bench)
        if isinstance(out, tuple):
            lines, rets, b = out
            R += lines
            mix = [n for n in ("World Momentum (IS3R)", "World Quality (IS3Q)", "US Small Cap Value (ZPRV)")
                   if n in rets] if bench == "MSCI World (EUNL)" else \
                  [n for n in ("US Momentum (MTUM)", "US Quality (QUAL)", "US Small Value (IJS)") if n in rets]
            if len(mix) == 3:
                m = pd.concat([rets[n] for n in mix], axis=1).dropna().mean(axis=1)
                st = stats(m, b)
                if st.get("n", 0) >= 24:
                    R.append(f"Equal-weight ETF mix ({', '.join(mix)}), monthly rebalanced, from {m.index[0]}: "
                             f"CAGR {_p(st['cagr'])} vs {_p(st['mcagr'])} → **{_p(st['diff'])} p.a.** "
                             f"(t {st['t']:.2f}), max DD {100*st['dd']:.0f}%, years won {100*st['years_won']:.0f}%.")
                    R.append("")
        else:
            R += out
    R.append("Note: Nasdaq-100 is shown only as a hindsight control — choosing it today because it won is "
             "exactly the bias this test is built to avoid.")
    return "\n".join(R)
