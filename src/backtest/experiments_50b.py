"""
Experiment #50b — hardening the buyback/issuance result of #50.

#50: buyback quintile +2.6%/yr vs universe (t 3.0), issuance quintile −2.7% (t −2.4), US
companies with ≥ $1bn assets, 2010–2026, equal-weight, annual formation end of June. Before
it goes into the app it is attacked the way #41 attacked #40. Pre-registered variants:

  1 Cut-offs: decile / quintile / tercile of net issuance
  2 Absolute app rule: buyback = shares −2 % or more, dilution = shares +5 % or more
  3 Value-weighted (market cap = shares × price at formation) instead of equal-weight
  4 Size: assets $1–10bn vs ≥ $10bn (Q5 vs the size group's own universe)
  5 Staleness: the same signal one year older (held July Y+2 … June Y+3)
  6 Freshness: quarterly signal from 10-Qs (current vs same quarter a year earlier, same
    filing → split-safe), formed every quarter end with filings filed by then, held 3 months
  7 Buybacks ∩ quality (≥ median, #49)
Each reports excess p.a. vs the matching universe, t, before/after 2016, years won.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_49 import components, quality_score, monthly_returns, mstat, _p
from .experiments_50 import CONCEPT, SHARE_TAGS


def _pairs(facts: list, form: str, dmin: int, dmax: int) -> dict:
    """Same-filing (cur, prior-year) pairs: {accn: (cur_end, cur_val, prior_val, filed)}."""
    by_accn = {}
    for f in facts:
        if f.get("form") != form or not f.get("start") or not f.get("end"):
            continue
        try:
            start, end, val = pd.Timestamp(f["start"]), pd.Timestamp(f["end"]), float(f["val"])
        except (ValueError, TypeError):
            continue
        if not (dmin <= (end - start).days <= dmax) or val <= 0:
            continue
        by_accn.setdefault(f.get("accn"), set()).add((end, val, f.get("filed")))
    out = {}
    for accn, rows in by_accn.items():
        rows = sorted(rows, key=lambda r: r[0])
        cur = rows[-1]
        prior = [r for r in rows[:-1] if 330 <= (cur[0] - r[0]).days <= 400]
        if prior and cur[2]:
            out[accn] = (cur[0], cur[1], prior[-1][1], pd.Timestamp(cur[2]))
    return out


def parse_concept_full(js: dict) -> tuple:
    """→ (annual {fy: (ni, filed, shares)}, quarterly [(period_end, ni, filed, shares)])."""
    try:
        facts = js["units"]["shares"]
    except (KeyError, TypeError):
        return {}, []
    annual = {}
    for cur_end, cur, prior, filed in _pairs(facts, "10-K", 330, 400).values():
        fy = cur_end.year if cur_end.month >= 6 else cur_end.year - 1
        if fy not in annual or filed < annual[fy][1]:
            annual[fy] = (math.log(cur / prior), filed, cur)
    quarterly = [(e, math.log(c / p), filed, c) for e, c, p, filed in _pairs(facts, "10-Q", 80, 100).values()]
    return annual, sorted(quarterly, key=lambda q: q[2])


def fetch_concepts(ciks: list, ua: str, timeout: int = 30, log=None) -> tuple:
    import json
    import time as _t
    import urllib.request
    out, fails = {}, 0
    for i, cik in enumerate(ciks):
        got = ({}, [])
        for tag in SHARE_TAGS:
            try:
                req = urllib.request.Request(CONCEPT.format(cik=int(cik), tag=tag),
                                             headers={"User-Agent": ua, "Accept-Encoding": "identity"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    got = parse_concept_full(json.loads(r.read().decode("utf-8")))
            except Exception:
                got = ({}, [])
            _t.sleep(0.13)
            if got[0] or got[1]:
                break
        if got[0] or got[1]:
            out[int(cik)] = got
        else:
            fails += 1
        if log and i % 250 == 0:
            log(f"SEC companyconcept {i}/{len(ciks)}")
    return out, fails


def hold(selections: dict, rets: pd.DataFrame, hold_len: int) -> pd.Series:
    """selections: {formation Period: weights Series (sum 1)} → monthly returns held for
    hold_len months after formation (missing returns: weights renormalised)."""
    out = {}
    for form, w in sorted(selections.items()):
        if w is None or w.empty:
            continue
        for m in pd.period_range(form + 1, form + hold_len, freq="M"):
            if m not in rets.index:
                continue
            r = rets.loc[m].reindex(w.index)
            ok = r.notna()
            if ok.sum() == 0:
                continue
            out[m] = float((r[ok] * w[ok]).sum() / w[ok].sum())
    return pd.Series(out, dtype=float)


def _ew(names) -> pd.Series:
    names = list(names)
    return pd.Series(1.0 / len(names), index=names) if names else pd.Series(dtype=float)


def _vw(names, caps: pd.Series) -> pd.Series:
    c = caps.reindex(list(names)).dropna()
    c = c[c > 0]
    return c / c.sum() if len(c) else pd.Series(dtype=float)


def _row(lbl: str, sel_r: pd.Series, uni_r: pd.Series) -> str:
    d = (sel_r - uni_r.reindex(sel_r.index)).dropna()
    if len(d) < 24:
        return f"| {lbl} | — | — | — | — | — |"
    s, cut = mstat(d), pd.Period("2015-12", "M")
    pre, post = mstat(d[d.index <= cut]), mstat(d[d.index > cut])
    yrs = sorted(set(d.index.year))
    won = sum((1 + d[d.index.year == y]).prod() > 1 for y in yrs)
    return (f"| {lbl} | {_p(s['ann'])} | {s['t']:.2f} | {_p(pre['ann'])} ({pre['t']:.1f}) | "
            f"{_p(post['ann'])} ({post['t']:.1f}) | {won}/{len(yrs)} |")


def run_experiment50b_report(frames: dict, concepts: dict, fails: int, ticker_map: dict, prices: dict,
                             min_assets: float = 1e9, n_trials: int = 240) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #50b — hardening buybacks vs issuance "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    px, rets = monthly_returns(prices)
    assets, qual, uni = {}, {}, {}
    for y, df in frames.items():
        if df is None or df.empty:
            continue
        comp = components(df)
        comp = comp[comp["assets"] >= min_assets]
        comp.index = [ticker_map.get(int(c)) for c in comp.index]
        comp = comp[comp.index.notna()]
        comp = comp[~comp.index.duplicated()]
        assets[y], qual[y], uni[y] = comp["assets"], quality_score(comp), set(comp.index)
    t2c = {t: c for c, t in ticker_map.items()}
    annual = {ticker_map[c]: a for c, (a, q) in concepts.items() if c in ticker_map and a}
    quarterly = {ticker_map[c]: q for c, (a, q) in concepts.items() if c in ticker_map and q}
    L.append(f"Companies with share data: {len(concepts):,} (none: {fails:,}); annual {len(annual):,}, "
             f"quarterly {len(quarterly):,}; tickers with prices {px.shape[1]:,}.")
    L.append("")

    def annual_signal(y: int, lag_years: int = 0) -> pd.Series:
        """−NI for fiscal year y (filed by end of June y+1), formation end of June y+1+lag."""
        cutoff = pd.Timestamp(f"{y + 1}-06-30")
        vals = {}
        for t, d in annual.items():
            if t in uni.get(y, set()) and y in d:
                ni, filed, _ = d[y]
                if filed <= cutoff and abs(ni) <= 1.5:
                    vals[t] = -ni
        return pd.Series(vals, dtype=float)

    def eligible(names, form):
        if form not in px.index:
            return []
        p0 = px.loc[form]
        return [t for t in names if t in px.columns and p0.get(t, np.nan) >= 5]

    years = sorted(uni)
    sels = {k: {} for k in ("dec", "q", "ter", "abs_bb", "abs_dil", "vw_q", "small_q", "large_q", "stale_q",
                            "combo", "q1")}
    unis = {k: {} for k in ("ew", "vw", "small", "large", "stale")}
    for y in years:
        sig = annual_signal(y)
        form = pd.Period(f"{y + 1}-06", "M")
        el = eligible(sig.index, form)
        sig = sig.reindex(el).dropna()
        if len(sig) < 50:
            continue
        caps = pd.Series({t: annual[t][y][2] * px.loc[form, t] for t in sig.index}, dtype=float)
        unis["ew"][form], unis["vw"][form] = _ew(sig.index), _vw(sig.index, caps)
        rk = sig.rank(pct=True)
        sels["dec"][form] = _ew(rk.index[rk > 0.9])
        sels["q"][form] = _ew(rk.index[rk > 0.8])
        sels["q1"][form] = _ew(rk.index[rk <= 0.2])
        sels["ter"][form] = _ew(rk.index[rk > 2 / 3])
        sels["abs_bb"][form] = _ew(sig.index[sig >= -math.log(0.98)])     # shares −2 % or more
        sels["abs_dil"][form] = _ew(sig.index[sig <= -math.log(1.05)])    # shares +5 % or more
        sels["vw_q"][form] = _vw(rk.index[rk > 0.8], caps)
        a = assets[y].reindex(sig.index)
        for grp, mask in (("small", a < 1e10), ("large", a >= 1e10)):
            g = sig[mask.to_numpy()]
            if len(g) >= 30:
                unis[grp][form] = _ew(g.index)
                rg = g.rank(pct=True)
                sels[f"{grp}_q"][form] = _ew(rg.index[rg > 0.8])
        q = qual.get(y)
        if q is not None:
            good = set(q[q >= q.median()].index)
            sels["combo"][form] = _ew([t for t in rk.index[rk > 0.8] if t in good])
        # staleness: same fiscal-year signal formed a year later
        form2 = form + 12
        el2 = eligible(sig.index, form2)
        if len(el2) >= 50:
            s2 = sig.reindex(el2)
            r2 = s2.rank(pct=True)
            unis["stale"][form2] = _ew(s2.index)
            sels["stale_q"][form2] = _ew(r2.index[r2 > 0.8])

    R = {k: hold(v, rets, 12) for k, v in sels.items()}
    U = {k: hold(v, rets, 12) for k, v in unis.items()}

    # quarterly fresh signal
    q_sel, q_uni, q_q1 = {}, {}, {}
    start, last = pd.Period("2010-06", "M"), rets.index.max()
    for form in [start + 3 * k for k in range(0, 400) if start + 3 * k <= last]:
        cutoff = form.to_timestamp(how="end")
        y = form.year - 1
        universe = uni.get(y, set()) | uni.get(y - 1, set())
        vals = {}
        for t, qs in quarterly.items():
            if t not in universe:
                continue
            live = [x for x in qs if x[2] <= cutoff and (cutoff - x[0]).days <= 200]
            if live:
                ni = live[-1][1]
                if abs(ni) <= 1.5:
                    vals[t] = -ni
        s = pd.Series(vals, dtype=float).reindex(eligible(vals.keys(), form)).dropna()
        if len(s) >= 50:
            rk = s.rank(pct=True)
            q_uni[form], q_sel[form], q_q1[form] = _ew(s.index), _ew(rk.index[rk > 0.8]), _ew(rk.index[rk <= 0.2])
    RQ, UQ, RQ1 = hold(q_sel, rets, 3), hold(q_uni, rets, 3), hold(q_q1, rets, 3)

    L.append("Excess return vs the matching universe (equal-weight unless stated). Pre-registered; "
             f"Bonferroni over the project α/{n_trials} = {0.05/n_trials:.5f} (|t| ≳ 3.5).")
    L.append("")
    L.append("| Variant | excess p.a. | t | ≤2015 (t) | >2015 (t) | years won |")
    L.append("|---|--:|--:|--:|--:|--:|")
    rows = [("Baseline #50: top quintile buybacks", R["q"], U["ew"]),
            ("Issuance quintile (avoid)", R["q1"], U["ew"]),
            ("1a Top decile", R["dec"], U["ew"]),
            ("1b Top tercile", R["ter"], U["ew"]),
            ("2a App rule: shares −2 % or more", R["abs_bb"], U["ew"]),
            ("2b App rule: shares +5 % or more (dilution)", R["abs_dil"], U["ew"]),
            ("3 Value-weighted top quintile vs VW universe", R["vw_q"], U["vw"]),
            ("4a Assets $1–10bn: top quintile", R["small_q"], U["small"]),
            ("4b Assets ≥ $10bn: top quintile", R["large_q"], U["large"]),
            ("5 Stale: same signal one year later", R["stale_q"], U["stale"]),
            ("6a Fresh quarterly (10-Q), 3-month hold", RQ, UQ),
            ("6b Fresh quarterly issuance quintile (avoid)", RQ1, UQ),
            ("7 Buybacks ∩ quality ≥ median", R["combo"], U["ew"])]
    for lbl, r, u in rows:
        L.append(_row(lbl, r, u))
    L.append("")
    n_bb = [len(v) for v in sels["abs_bb"].values()]
    n_dil = [len(v) for v in sels["abs_dil"].values()]
    L.append(f"App-rule group sizes per year: buyback ≥2 %: {min(n_bb) if n_bb else 0}–{max(n_bb) if n_bb else 0} "
             f"companies; dilution ≥5 %: {min(n_dil) if n_dil else 0}–{max(n_dil) if n_dil else 0}.")
    L.append("")
    base = mstat((R["q"] - U["ew"].reindex(R["q"].index)).dropna())
    L.append(f"**Summary:** baseline {_p(base['ann'])} (t {base['t']:.2f}). Read the table for robustness: same sign "
             f"across cut-offs, weighting, size, staleness and quarterly freshness = robust; sign flips or collapse "
             f"under value-weighting / large caps = small-cap or construction artefact.")
    return "\n".join(L)
