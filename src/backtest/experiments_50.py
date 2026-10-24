"""
Experiment #50 — "follow the money" of the company itself: share buybacks vs issuance.

Net share issuance (Pontiff & Woodgate 2008; Daniel & Titman 2006; McLean, Pontiff &
Watanabe 2009 internationally): companies that shrink their share count (buybacks)
outperform, companies that issue many new shares underperform. Management is the
best-informed buyer/seller of its own stock and pays real money.

Data: SEC XBRL companyconcept per company, tag WeightedAverageNumberOfDilutedSharesOutstanding
(fallback ...SharesOutstandingBasic). Split-safe: current AND prior-year share count are
taken from the SAME 10-K, which restates both for splits. Point-in-time: a 10-K for fiscal
year Y is used only if FILED by the end of June Y+1 (portfolio formation date).

Pre-registered signal: net issuance NI = ln(shares_Y / shares_{Y−1}).
Score = −NI (Q5 = largest buybacks, Q1 = largest issuance). Universe, formation and
holding exactly as #49 (Assets ≥ $1bn, price ≥ $5, end of June, 12 months, equal-weight).
Also: buybacks combined with the #49 quality score (top-quintile buyback ∩ quality ≥ median).
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_49 import (components, quality_score, monthly_returns, form_portfolios, mstat, perf, _p)

CONCEPT = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/{tag}.json"
SHARE_TAGS = ("WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic")


def issuance_from_concept(js: dict) -> dict:
    """companyconcept JSON → {fiscal year Y: (net issuance ln(cur/prior), filed date)}.
    Both values from the same 10-K (split-consistent)."""
    try:
        facts = js["units"]["shares"]
    except (KeyError, TypeError):
        return {}
    out = {}
    by_accn = {}
    for f in facts:
        if f.get("form") != "10-K" or f.get("fp") != "FY" or not f.get("start") or not f.get("end"):
            continue
        try:
            start, end = pd.Timestamp(f["start"]), pd.Timestamp(f["end"])
            val = float(f["val"])
        except (ValueError, TypeError):
            continue
        if not (330 <= (end - start).days <= 400) or val <= 0:
            continue
        by_accn.setdefault(f.get("accn"), []).append((end, val, f.get("fy"), f.get("filed")))
    for accn, rows in by_accn.items():
        rows = sorted(set(rows), key=lambda r: r[0])
        if len(rows) < 2:
            continue
        cur = rows[-1]
        prior = [r for r in rows[:-1] if 300 <= (cur[0] - r[0]).days <= 430]
        if not prior:
            continue
        p = prior[-1]
        fy = cur[0].year if cur[0].month >= 6 else cur[0].year - 1   # fiscal year by period end
        ni = math.log(cur[1] / p[1])
        filed = pd.Timestamp(cur[3]) if cur[3] else None
        if fy not in out or (filed is not None and out[fy][1] is not None and filed < out[fy][1]):
            out[fy] = (ni, filed)       # keep the original (earliest) filing per year
    return out


def fetch_issuance(ciks: list, ua: str, timeout: int = 30, log=None) -> tuple:
    """{cik: {fy: (ni, filed)}} via companyconcept (≤ 8 requests/second)."""
    import json
    import time as _t
    import urllib.request
    out, fails = {}, 0
    for i, cik in enumerate(ciks):
        got = {}
        for tag in SHARE_TAGS:
            try:
                req = urllib.request.Request(CONCEPT.format(cik=int(cik), tag=tag),
                                             headers={"User-Agent": ua, "Accept-Encoding": "identity"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    got = issuance_from_concept(json.loads(r.read().decode("utf-8")))
            except Exception:
                got = {}
            _t.sleep(0.13)
            if got:
                break
        if got:
            out[int(cik)] = got
        else:
            fails += 1
        if log and i % 250 == 0:
            log(f"SEC companyconcept {i}/{len(ciks)}")
    return out, fails


def issuance_scores(iss: dict, ticker_map: dict, years, max_abs: float = 1.5) -> dict:
    """{fy: Series ticker → −NI}, only if the 10-K was filed by end of June fy+1."""
    scores = {}
    for y in years:
        cutoff = pd.Timestamp(f"{y + 1}-06-30")
        vals = {}
        for cik, d in iss.items():
            t = ticker_map.get(int(cik))
            if not t or y not in d:
                continue
            ni, filed = d[y]
            if filed is None or filed > cutoff or not np.isfinite(ni) or abs(ni) > max_abs:
                continue   # |ln| > 1.5 ≈ ×4.5: mergers/data errors, not buybacks
            vals[t] = -ni
        if vals:
            scores[y] = pd.Series(vals)
    return scores


def selected_portfolio(sel: dict, px: pd.DataFrame, rets: pd.DataFrame, min_price: float = 5.0) -> pd.Series:
    """EW monthly returns of an explicit selection {fy: list of tickers}, formed end of
    June fy+1 and held 12 months (same timing as form_portfolios)."""
    out = {}
    for y, names in sorted(sel.items()):
        form = pd.Period(f"{y + 1}-06", "M")
        if form not in px.index:
            continue
        p0 = px.loc[form]
        keep = [t for t in names if t in px.columns and p0.get(t, np.nan) >= min_price]
        if len(keep) < 5:
            continue
        for m in pd.period_range(form + 1, form + 12, freq="M"):
            if m in rets.index:
                out[m] = float(rets.loc[m].reindex(keep).mean())
    return pd.Series(out, dtype=float)


def run_experiment50_report(frames: dict, iss: dict, iss_fails: int, ticker_map: dict, prices: dict,
                            spy: pd.Series, market_w: pd.Series | None = None, cash_m: pd.Series | None = None,
                            min_assets: float = 1e9, n_trials: int = 232, n_placebo: int = 200) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #50 — share buybacks vs issuance (SEC, split-safe, point-in-time) "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    # universe & quality from #49 frames
    universe, qual = {}, {}
    for y, df in frames.items():
        if df is None or df.empty:
            continue
        comp = components(df)
        comp = comp[comp["assets"] >= min_assets]
        comp.index = [ticker_map.get(int(c)) for c in comp.index]
        comp = comp[comp.index.notna()]
        comp = comp[~comp.index.duplicated()]
        universe[y] = set(comp.index)
        qual[y] = quality_score(comp)
    scores_all = issuance_scores(iss, ticker_map, sorted(universe))
    scores = {y: s[s.index.isin(universe.get(y, set()))] for y, s in scores_all.items()}
    scores = {y: s for y, s in scores.items() if len(s) >= 50}
    L.append(f"Companies with share data: {len(iss):,} (no data: {iss_fails:,}); scored per year: "
             f"{', '.join(f'{y}:{len(s)}' for y, s in sorted(scores.items()))}.")
    if not scores:
        return "\n".join(L + ["", "Too little data."])
    allni = pd.concat([-s for s in scores.values()])
    L.append(f"Net issuance distribution (ln): 10% {allni.quantile(.1):+.3f}, median {allni.median():+.3f}, "
             f"90% {allni.quantile(.9):+.3f} (≈ {100*(math.exp(allni.quantile(.1))-1):+.1f}% / "
             f"{100*(math.exp(allni.quantile(.9))-1):+.1f}% shares).")
    px, rets = monthly_returns(prices)
    port = form_portfolios(scores, px, rets)
    if port.empty:
        return "\n".join(L + ["", "Too few stocks with prices."])
    spy_m = spy.groupby(pd.to_datetime(spy.index).to_period("M")).last().pct_change() if spy is not None else None
    port["SPY"] = spy_m.reindex(port.index) if spy_m is not None else np.nan
    # buybacks ∩ quality ≥ median
    combo_sel = {}
    for y, s in scores.items():
        q = qual.get(y)
        if q is None:
            continue
        top_bb = s[s >= s.quantile(0.8)]
        good = set(q[q >= q.median()].index)
        names = [t for t in top_bb.index if t in good]
        if len(names) >= 10:
            combo_sel[y] = names
    combo = selected_portfolio(combo_sel, px, rets) if combo_sel else pd.Series(dtype=float)

    L.append(f"Portfolios {port.index[0]} → {port.index[-1]} ({len(port)} months), annual rebalance end of June.")
    L.append("")
    L.append("### A — Quintiles (Q5 = largest buybacks, Q1 = largest issuance), equal-weight")
    L.append("| Portfolio | CAGR | vol | max DD | Sharpe | vs universe p.a. (t) |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for c in ["Q1", "Q2", "Q3", "Q4", "Q5", "universe", "SPY"]:
        r = port[c]
        pf, ms = perf(r), mstat(r)
        rel = mstat(r - port["universe"]) if c != "universe" else {"ann": np.nan, "t": np.nan}
        L.append(f"| {c} | {_p(pf['cagr'])} | {100*pf['vol']:.1f}% | {_p(pf['maxdd'], 0)} | {ms['sharpe']:.2f} | "
                 f"{_p(rel['ann'])} ({rel['t']:.2f}) |")
    if not combo.empty:
        r = combo.reindex(port.index)
        pf, ms, rel = perf(r), mstat(r), mstat(r - port["universe"])
        L.append(f"| Buybacks ∩ quality ≥ median | {_p(pf['cagr'])} | {100*pf['vol']:.1f}% | {_p(pf['maxdd'], 0)} | "
                 f"{ms['sharpe']:.2f} | {_p(rel['ann'])} ({rel['t']:.2f}) |")
    L.append("")
    crit = 0.05 / n_trials
    ex, sp = port["Q5"] - port["universe"], port["Q5"] - port["Q1"]
    iss_short = port["Q1"] - port["universe"]
    rng = np.random.default_rng(50)
    plc = []
    for _ in range(n_placebo):
        pp = form_portfolios(scores, px, rets, rng=rng)
        if not pp.empty:
            plc.append(mstat(pp["Q5"] - pp["universe"])["ann"])
    plc = np.array([v for v in plc if np.isfinite(v)])
    s_ex, s_sp, s_is = mstat(ex), mstat(sp), mstat(iss_short)
    p_plc = max(float((plc >= s_ex["ann"]).mean()), 1 / (len(plc) + 1)) if len(plc) else float("nan")
    p_ex = math.erfc(abs(s_ex["t"]) / math.sqrt(2)) / 2 if np.isfinite(s_ex["t"]) else float("nan")
    cut = pd.Period("2015-12", "M")
    pre, post = mstat(ex[ex.index <= cut]), mstat(ex[ex.index > cut])
    L.append("### B — Significance")
    L.append(f"- **Buybacks (Q5) − universe: {_p(s_ex['ann'])} p.a., t={s_ex['t']:.2f}, one-sided p={p_ex:.4f} "
             f"{'✅' if p_ex < crit and s_ex['ann'] > 0 else '❌'} (α/{n_trials}); placebo p={p_plc:.3f}**")
    L.append(f"- Issuance (Q1) − universe (avoid-signal): {_p(s_is['ann'])} p.a., t={s_is['t']:.2f}")
    L.append(f"- Q5 − Q1: {_p(s_sp['ann'])} p.a., t={s_sp['t']:.2f}")
    L.append(f"- Q5 − universe ≤2015: {_p(pre['ann'])} (t {pre['t']:.2f}); >2015: {_p(post['ann'])} (t {post['t']:.2f})")
    yrs = sorted(set(ex.index.year))
    L.append(f"- Q5 beat the universe in {100*(ex > 0).mean():.0f}% of months, "
             f"{sum((1 + ex[ex.index.year == y]).prod() > 1 for y in yrs)}/{len(yrs)} calendar years")
    L.append("")
    L.append("### C — Crises and market regime (#47)")
    rows = {"Q5 buybacks": port["Q5"], "Q1 issuance": port["Q1"], "Universe": port["universe"], "SPY": port["SPY"]}
    if market_w is not None and cash_m is not None:
        w = market_w.shift(1).reindex(port.index).fillna(1.0)
        c = cash_m.reindex(port.index).fillna(0.0)
        rows["Q5 + market regime"] = w * port["Q5"] + (1 - w) * c
    crises = (("2011", "2011-05", "2011-09"), ("2015–16", "2015-06", "2016-02"), ("2018 Q4", "2018-10", "2018-12"),
              ("2020", "2020-02", "2020-03"), ("2022", "2022-01", "2022-09"))
    L.append("| Portfolio | CAGR | max DD | Sharpe | " + " | ".join(c[0] for c in crises) + " |")
    L.append("|---|--:|--:|--:|" + "--:|" * len(crises))
    for k, r in rows.items():
        pf, ms = perf(r), mstat(r)
        cr = []
        for _, a, b in crises:
            seg = r[(r.index >= pd.Period(a, "M")) & (r.index <= pd.Period(b, "M"))].dropna()
            cr.append(_p(float((1 + seg).prod() - 1), 0) if len(seg) else "—")
        L.append(f"| {k} | {_p(pf['cagr'])} | {_p(pf['maxdd'], 0)} | {ms['sharpe']:.2f} | " + " | ".join(cr) + " |")
    L.append("")
    L.append(f"**Summary:** buybacks − universe {_p(s_ex['ann'])} p.a. (t {s_ex['t']:.2f}, placebo p {p_plc:.3f}); "
             f"issuance − universe {_p(s_is['ann'])} (t {s_is['t']:.2f}); post-2015 {_p(post['ann'])}. "
             f"Survivorship: only current tickers have prices (heavy issuers that failed are missing → issuance "
             f"quintile looks too good).")
    return "\n".join(L)
