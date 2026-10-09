"""
Experiment #49 — a quality score for single stocks from SEC fundamentals.

#43 (French data): profitability/quality was the most persistent factor, also after
publication and internationally. The user wants a usable signal for SINGLE stocks:
WHICH stock (selection), combined with the market regime from #47 (WHEN).

Data: SEC XBRL "frames" API — one value per company for a tag and calendar period,
for ALL filers (incl. companies that later disappeared), free.

Pre-registered score (per fiscal year Y, percentile ranks within the universe, mean of
≥3 available components):
  1 gross profitability  GP / Assets          (Novy-Marx 2013)
  2 return on equity     NI / Equity (Equity > 0)
  3 low accruals         −(NI − CFO) / Assets  (earnings backed by cash)
  4 low leverage         −Liabilities / Assets
Point-in-time: FY Y data are used only from the end of June Y+1 (10-Ks are due within
60–90 days; 6 months is conservative). Portfolios formed end of June, held 12 months,
equal-weight, universe = companies with Assets ≥ $1bn, price ≥ $5 and Yahoo prices.
Measured: quintile returns, Q5 (best) vs EW universe vs SPY, Q5−Q1, t-stats, before/after
2016, crises, placebo (random scores), and Q5 combined with the market regime (#47).
Survivorship: prices only for tickers that still exist → low-quality failures missing →
bias AGAINST the quality spread; long-only comparisons are biased equally.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

FRAMES = "https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/{period}.json"
TICKERS = "https://www.sec.gov/files/company_tickers.json"
DURATION_TAGS = ("GrossProfit", "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                 "SalesRevenueNet", "CostOfRevenue", "CostOfGoodsAndServicesSold", "NetIncomeLoss",
                 "NetCashProvidedByUsedInOperatingActivities")
INSTANT_TAGS = ("Assets", "StockholdersEquity", "Liabilities")
COMPONENTS = ("gross_profitability", "roe", "low_accruals", "low_leverage")


def parse_frame(js: dict) -> pd.Series:
    """Frames JSON → Series cik → value (last per cik)."""
    try:
        rows = js["data"]
    except (KeyError, TypeError):
        return pd.Series(dtype=float)
    s = pd.Series({int(r["cik"]): float(r["val"]) for r in rows if "cik" in r and "val" in r})
    return s[np.isfinite(s)]


def fetch_frames(years: range, ua: str, timeout: int = 60, log=None) -> tuple:
    """{year: DataFrame(cik × tag)} and failures."""
    import json
    import time as _t
    import urllib.request
    out, fails = {}, []
    for y in years:
        cols = {}
        for tag, period in [(t, f"CY{y}") for t in DURATION_TAGS] + [(t, f"CY{y}Q4I") for t in INSTANT_TAGS]:
            try:
                req = urllib.request.Request(FRAMES.format(tag=tag, period=period),
                                             headers={"User-Agent": ua, "Accept-Encoding": "identity"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    cols[tag] = parse_frame(json.loads(r.read().decode("utf-8")))
            except Exception as e:
                fails.append(f"{tag} {period}: {repr(e)[:60]}")
            _t.sleep(0.15)
        out[y] = pd.DataFrame(cols)
        if log:
            log(f"SEC frames {y}: {len(out[y])} companies")
    return out, fails


def fetch_ticker_map(ua: str, timeout: int = 60) -> dict:
    """cik → ticker (current tickers only)."""
    import json
    import urllib.request
    req = urllib.request.Request(TICKERS, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        js = json.loads(r.read().decode("utf-8"))
    m = {}
    for v in js.values():
        m.setdefault(int(v["cik_str"]), str(v["ticker"]).upper())
    return m


def components(df: pd.DataFrame) -> pd.DataFrame:
    g = lambda c: df[c] if c in df else pd.Series(np.nan, index=df.index)
    rev = g("Revenues").combine_first(g("RevenueFromContractWithCustomerExcludingAssessedTax")) \
        .combine_first(g("SalesRevenueNet"))
    cost = g("CostOfRevenue").combine_first(g("CostOfGoodsAndServicesSold"))
    gp = g("GrossProfit").combine_first(rev - cost)
    a = g("Assets").where(g("Assets") > 0)
    eq = g("StockholdersEquity").where(g("StockholdersEquity") > 0)
    ni, cfo, liab = g("NetIncomeLoss"), g("NetCashProvidedByUsedInOperatingActivities"), g("Liabilities")
    out = pd.DataFrame({"gross_profitability": gp / a, "roe": ni / eq,
                        "low_accruals": -(ni - cfo) / a, "low_leverage": -liab / a, "assets": a})
    # winsorise extreme ratios (tiny denominators)
    for c in COMPONENTS:
        lo, hi = out[c].quantile(0.01), out[c].quantile(0.99)
        out[c] = out[c].clip(lo, hi)
    return out


def quality_score(comp: pd.DataFrame, min_components: int = 3) -> pd.Series:
    ranks = comp[list(COMPONENTS)].rank(pct=True)
    n = ranks.notna().sum(axis=1)
    return ranks.mean(axis=1).where(n >= min_components)


def monthly_returns(prices: dict) -> pd.DataFrame:
    cols = {}
    for t, s in prices.items():
        if s is None or len(s) < 60:
            continue
        s = pd.Series(s).dropna()
        idx = pd.to_datetime(s.index)
        s.index = (idx.tz_localize(None) if idx.tz is not None else idx).to_period("M")
        m = s.groupby(level=0).last()
        cols[t] = m
    px = pd.DataFrame(cols).sort_index()
    return px, px.pct_change(fill_method=None)


def form_portfolios(scores: dict, px: pd.DataFrame, rets: pd.DataFrame, n_q: int = 5,
                    min_price: float = 5.0, rng=None) -> pd.DataFrame:
    """scores: {fiscal year: Series ticker → score}. Formation end of June Y+1, hold
    July Y+1 … June Y+2. Returns monthly EW returns of Q1..Qn and the universe."""
    rows = []
    for y, sc in sorted(scores.items()):
        form = pd.Period(f"{y + 1}-06", "M")
        if form not in px.index:
            continue
        p0 = px.loc[form]
        elig = sc[sc.index.isin(px.columns)].dropna()
        elig = elig[(p0.reindex(elig.index) >= min_price).to_numpy()]
        if len(elig) < 10 * n_q:
            continue
        if rng is not None:
            elig = pd.Series(rng.permutation(elig.to_numpy()), index=elig.index)
        q = pd.qcut(elig.rank(method="first"), n_q, labels=False) + 1
        for m in pd.period_range(form + 1, form + 12, freq="M"):
            if m not in rets.index:
                continue
            r = rets.loc[m]
            row = {"month": m, "universe": float(r.reindex(elig.index).mean())}
            for k in range(1, n_q + 1):
                row[f"Q{k}"] = float(r.reindex(q.index[q == k]).mean())
            rows.append(row)
    return pd.DataFrame(rows).set_index("month") if rows else pd.DataFrame()


def mstat(x: pd.Series) -> dict:
    x = x.dropna()
    if len(x) < 24 or x.std() == 0:
        return {"ann": float("nan"), "t": float("nan"), "sharpe": float("nan")}
    return {"ann": float(x.mean() * 12), "t": float(x.mean() / x.std() * math.sqrt(len(x))),
            "sharpe": float(x.mean() / x.std() * math.sqrt(12))}


def perf(r: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    return {"cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1) if len(r) else float("nan"),
            "vol": float(r.std() * math.sqrt(12)), "maxdd": float((eq / eq.cummax() - 1).min()) if len(r) else float("nan")}


def _p(x, d=1):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:+.{d}f}%"


def run_experiment49_report(frames: dict, fails: list, ticker_map: dict, prices: dict, spy: pd.Series,
                            market_w: pd.Series | None = None, cash_m: pd.Series | None = None,
                            min_assets: float = 1e9, n_trials: int = 230, n_placebo: int = 200) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #49 — quality score for single stocks (SEC fundamentals) "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"SEC frames years: {len(frames)}; failed requests: {len(fails)}" +
             (f" (e.g. {fails[0]})" if fails else "") + f"; ticker map: {len(ticker_map):,} CIKs.")
    scores, comps_by_year, n_univ = {}, {}, []
    for y, df in frames.items():
        if df is None or df.empty:
            continue
        comp = components(df)
        comp = comp[comp["assets"] >= min_assets]
        comp.index = [ticker_map.get(int(c)) for c in comp.index]
        comp = comp[comp.index.notna()]
        comp = comp[~comp.index.duplicated()]
        sc = quality_score(comp)
        scores[y], comps_by_year[y] = sc, comp
        n_univ.append(int(sc.notna().sum()))
    if not scores:
        return "\n".join(L + ["", "No fundamentals — SEC download failed."])
    px, rets = monthly_returns(prices)
    L.append(f"Universe (Assets ≥ ${min_assets/1e9:.0f}bn, scored, mapped to a current ticker): "
             f"{min(n_univ)}–{max(n_univ)} companies per year; with Yahoo prices: {px.shape[1]:,} tickers.")
    port = form_portfolios(scores, px, rets)
    if port.empty:
        return "\n".join(L + ["", "Too few stocks with prices to form portfolios."])
    spy_m = spy.groupby(pd.to_datetime(spy.index).to_period("M")).last().pct_change() if spy is not None else None
    port["SPY"] = spy_m.reindex(port.index) if spy_m is not None else np.nan
    L.append(f"Portfolios {port.index[0]} → {port.index[-1]} ({len(port)} months), annual rebalance end of June.")
    L.append("")
    L.append("### A — Quintiles (Q5 = highest quality), equal-weight")
    L.append("| Portfolio | CAGR | vol | max DD | Sharpe (raw) | vs universe p.a. (t) |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for c in ["Q1", "Q2", "Q3", "Q4", "Q5", "universe", "SPY"]:
        r = port[c]
        pf, ms = perf(r), mstat(r)
        rel = mstat(r - port["universe"]) if c not in ("universe",) else {"ann": np.nan, "t": np.nan}
        L.append(f"| {c} | {_p(pf['cagr'])} | {100*pf['vol']:.1f}% | {_p(pf['maxdd'], 0)} | {ms['sharpe']:.2f} | "
                 f"{_p(rel['ann'])} ({rel['t']:.2f}) |")
    L.append("")
    crit = 0.05 / n_trials
    spread = port["Q5"] - port["Q1"]
    excess = port["Q5"] - port["universe"]
    rng = np.random.default_rng(49)
    plc = []
    for _ in range(n_placebo):
        pp = form_portfolios(scores, px, rets, rng=rng)
        if not pp.empty:
            plc.append(mstat(pp["Q5"] - pp["universe"])["ann"])
    plc = np.array([v for v in plc if np.isfinite(v)])
    p_plc = max(float((plc >= mstat(excess)["ann"]).mean()), 1 / (len(plc) + 1)) if len(plc) else float("nan")
    s_sp, s_ex = mstat(spread), mstat(excess)
    p_ex = math.erfc(abs(s_ex["t"]) / math.sqrt(2)) / 2 if np.isfinite(s_ex["t"]) else float("nan")
    L.append("### B — Significance")
    L.append(f"- Q5 − Q1 (long-short, descriptive): {_p(s_sp['ann'])} p.a., t={s_sp['t']:.2f}")
    L.append(f"- **Q5 − universe (long-only, what you can buy): {_p(s_ex['ann'])} p.a., t={s_ex['t']:.2f}, one-sided "
             f"p={p_ex:.4f} {'✅' if p_ex < crit and s_ex['ann'] > 0 else '❌'} (α/{n_trials})**; placebo (random scores, "
             f"{len(plc)} runs): p={p_plc:.3f}")
    cut = pd.Period("2015-12", "M")
    pre, post = mstat(excess[excess.index <= cut]), mstat(excess[excess.index > cut])
    L.append(f"- Q5 − universe ≤2015: {_p(pre['ann'])} (t {pre['t']:.2f}); >2015: {_p(post['ann'])} (t {post['t']:.2f})")
    L.append(f"- Hit rate: Q5 beat the universe in {100*(excess > 0).mean():.0f}% of months; "
             f"in {sum((1+excess[excess.index.year == yr]).prod() > 1 for yr in sorted(set(excess.index.year)))}"
             f"/{len(set(excess.index.year))} calendar years")
    L.append("")
    L.append("### C — Single components (Q5 − universe of a 1-component sort, p.a. (t))")
    for c in COMPONENTS:
        sc1 = {y: cp[c].rank(pct=True) for y, cp in comps_by_year.items()}
        p1 = form_portfolios(sc1, px, rets)
        if not p1.empty:
            m1 = mstat(p1["Q5"] - p1["universe"])
            L.append(f"- {c}: {_p(m1['ann'])} ({m1['t']:.2f})")
    L.append("")
    L.append("### D — Crises and combination with the market regime (#47: S&P trend + macro stress)")
    rows = {"Q5 quality": port["Q5"], "Universe": port["universe"], "SPY": port["SPY"]}
    if market_w is not None and cash_m is not None:
        w = market_w.shift(1).reindex(port.index).fillna(1.0)
        c = cash_m.reindex(port.index).fillna(0.0)
        rows["Q5 + market regime"] = w * port["Q5"] + (1 - w) * c
        rows["Universe + market regime"] = w * port["universe"] + (1 - w) * c
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
    L.append(f"**Summary:** Q5 − universe {_p(s_ex['ann'])} p.a. (t {s_ex['t']:.2f}, placebo p {p_plc:.3f}); "
             f"Q5 − Q1 {_p(s_sp['ann'])} (t {s_sp['t']:.2f}). Survivorship (current tickers only) biases against the "
             f"low-quality quintile's true losses.")
    return "\n".join(L)
