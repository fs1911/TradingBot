"""
Experiment #64 — does the buyback / dilution signal (#50, #50b) also work for Swiss and
European stocks?

The "Mein Depot" app is meant to show the signal for CH/EU stocks, but it was tested only
on US data (SEC). Here: ~190 large and mid caps from Switzerland (SMI + mid caps), Germany
(DAX), France (CAC 40) and the Netherlands (AEX). Share counts from Yahoo's fundamentals
time series (annual diluted average shares, fallback basic average / ordinary shares),
split-adjusted with Yahoo's split events.

Pre-registered, same app rule as #50b:
  change = shares(last fiscal year) / shares(year before) − 1
  buyback ≤ −2 %, dilution ≥ +5 %, else neutral.
Point-in-time: a fiscal year ending ≤ end of February Y is used at the end of June Y
(≥ 4 months for the annual report). Hold July Y – June Y+1, equal-weight, local-currency
total returns (Yahoo adjusted closes), measured AGAINST THE EQUAL-WEIGHT UNIVERSE OF THE
SAME COUNTRY (so currency and country effects cancel), then pooled across countries.
Caveats: survivorship (today's index members), Yahoo history is short (a few fiscal years),
so statistical power is low (#59) — the report states the years and stocks covered.
Pure, injected for CI.
"""
from __future__ import annotations
import json
import math
import numpy as np
import pandas as pd

TICKERS = {
    "CH": "ABBN ALC CFR GEBN GIVN HOLN KNIN LOGN LONN NESN NOVN PGHN ROG SCMN SGSN SIKA SLHN SOON SREN UBSG "
          "ZURN SDZ ADEN AMS BAER BALN BARN BCVN CLN DKSH EMSN FHZN GALE HELN LISN SPSN STMN SUN TECN TEMN "
          "UHR VACN BEAN BKW DOKA FORN IDIA PSPN SIGN ARYN BANB LAND SQN MOBN ALLN BUCN IFCN DAE OERL SCHP "
          "SFSN SRAIL VZN YPSN ZEHN COTN MBTN GURN KUD LEON",
    "DE": "ADS AIR ALV BAS BAYN BEI BMW BNR CBK CON 1COV DB1 DBK DHL DTE DTG ENR EOAN FRE G1A HEI HEN3 HNR1 "
          "IFX MBG MRK MTX MUV2 P911 PAH3 QIA RHM RWE SAP SHL SIE SRT3 SY1 VNA VOW3 ZAL",
    "FR": "AI AIR ALO BN BNP CA CAP CS DG DSY EL EN ENGI ERF GLE HO KER LR MC ML OR ORA PUB RI RMS RNO SAF "
          "SAN SGO SU TTE URW VIE VIV ACA AC STMPA",
    "NL": "ADYEN AGN AD AKZA ASM ASML ASRNL BESI DSFIR HEIA IMCD INGA KPN NN PHIA PRX RAND REN SHELL UNA WKL ABN",
}
SUFFIX = {"CH": ".SW", "DE": ".DE", "FR": ".PA", "NL": ".AS"}
SHARE_TYPES = ("annualDilutedAverageShares", "annualBasicAverageShares", "annualOrdinarySharesNumber")


def symbols() -> dict:
    """{yahoo symbol: country}"""
    return {t + SUFFIX[c]: c for c, s in TICKERS.items() for t in s.split()}


def parse_timeseries(text: str) -> dict:
    """Yahoo fundamentals-timeseries JSON → {type: Series(asOfDate → value)}."""
    out = {}
    try:
        res = json.loads(text)["timeseries"]["result"]
    except (KeyError, TypeError, ValueError):
        return out
    for item in res:
        types = item.get("meta", {}).get("type", [])
        for t in types:
            vals = item.get(t) or []
            pts = {}
            for v in vals:
                if not v:
                    continue
                d, rv = v.get("asOfDate"), (v.get("reportedValue") or {}).get("raw")
                if d and rv:
                    pts[pd.Timestamp(d)] = float(rv)
            if pts:
                out[t] = pd.Series(pts).sort_index()
    return out


def parse_splits(text: str) -> pd.Series:
    """Yahoo chart JSON (events=splits) → Series(date → factor numerator/denominator)."""
    try:
        ev = json.loads(text)["chart"]["result"][0].get("events", {}).get("splits", {})
    except (KeyError, IndexError, TypeError, ValueError):
        return pd.Series(dtype=float)
    pts = {pd.to_datetime(int(v["date"]), unit="s"): float(v["numerator"]) / float(v["denominator"])
           for v in ev.values() if float(v.get("denominator", 0) or 0) > 0}
    return pd.Series(pts, dtype=float).sort_index()


def fetch_shares(sym: str, timeout: int = 20) -> tuple:
    import time as _t
    import urllib.request
    p1, p2 = int(pd.Timestamp("2005-01-01").timestamp()), int(_t.time())
    hdr = {"User-Agent": "Mozilla/5.0 (research)"}
    url = (f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{sym}"
           f"?symbol={sym}&type={','.join(SHARE_TYPES)}&period1={p1}&period2={p2}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=timeout) as r:
            ts = parse_timeseries(r.read().decode("utf-8", "replace"))
    except Exception:
        ts = {}
    url2 = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}"
            f"&interval=1mo&events=splits")
    try:
        with urllib.request.urlopen(urllib.request.Request(url2, headers=hdr), timeout=timeout) as r:
            sp = parse_splits(r.read().decode("utf-8", "replace"))
    except Exception:
        sp = pd.Series(dtype=float)
    return ts, sp


def share_changes(ts: dict, splits: pd.Series) -> pd.Series:
    """{fiscal year-end → change vs the year before}, split-safe."""
    s = next((ts[t] for t in SHARE_TYPES if t in ts and len(ts[t]) >= 2), None)
    if s is None:
        return pd.Series(dtype=float)
    out = {}
    for d1, v1 in s.items():
        prior = s[(s.index <= d1 - pd.Timedelta(days=330)) & (s.index >= d1 - pd.Timedelta(days=400))]
        if prior.empty or v1 <= 0 or prior.iloc[-1] <= 0:
            continue
        d0, v0 = prior.index[-1], prior.iloc[-1]
        raw = v1 / v0 - 1
        f = float(splits[(splits.index > d0) & (splits.index <= d1 + pd.Timedelta(days=120))].prod()) if len(splits) else 1.0
        adj = v1 / (v0 * f) - 1
        # a split between the two reports may or may not already be restated: take the plausible one
        ch = adj if abs(math.log1p(adj)) < abs(math.log1p(raw)) else raw
        if abs(math.log1p(ch)) < 0.4:
            out[d1] = ch
    return pd.Series(out, dtype=float).sort_index()


def classify(ch: float) -> str:
    return "buyback" if ch <= -0.02 else ("dilution" if ch >= 0.05 else "neutral")


def build_groups(changes: dict, country: dict, years) -> dict:
    """{formation year Y: {symbol: (country, group, change)}} using fiscal years ending ≤ Feb Y."""
    out = {}
    for y in years:
        cut = pd.Timestamp(f"{y}-02-28")
        sel = {}
        for sym, ch in changes.items():
            c = ch[(ch.index <= cut) & (ch.index > cut - pd.Timedelta(days=400))]
            if len(c):
                sel[sym] = (country[sym], classify(float(c.iloc[-1])), float(c.iloc[-1]))
        if sel:
            out[y] = sel
    return out


def group_excess(groups: dict, rets: pd.DataFrame) -> pd.DataFrame:
    """Monthly pooled excess returns of each group vs its country's EW universe."""
    rows = []
    for y, sel in sorted(groups.items()):
        for m in pd.period_range(pd.Period(f"{y}-07", "M"), pd.Period(f"{y + 1}-06", "M"), freq="M"):
            if m not in rets.index:
                continue
            r = rets.loc[m]
            row = {"month": m}
            for g in ("buyback", "dilution", "neutral"):
                exs = []
                for c in sorted({v[0] for v in sel.values()}):
                    uni = [s for s, v in sel.items() if v[0] == c and np.isfinite(r.get(s, np.nan))]
                    grp = [s for s in uni if sel[s][1] == g]
                    if len(uni) >= 8 and len(grp) >= 2:
                        exs.append(float(r[grp].mean() - r[uni].mean()))
                row[g] = float(np.mean(exs)) if exs else np.nan
            rows.append(row)
    return pd.DataFrame(rows).set_index("month") if rows else pd.DataFrame()


def run_experiment64_report(changes: dict, country: dict, prices: dict, n_trials: int = 300) -> str:
    from datetime import datetime, timezone
    from .experiments_49 import monthly_returns, mstat
    L = [f"# Experiment #64 — buyback/dilution signal for Swiss & European stocks "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    n_sym = len(country)
    with_data = {s: c for s, c in changes.items() if len(c)}
    L.append(f"Symbols: {n_sym}; with usable share history: {len(with_data)}; with prices: {len(prices)}. "
             f"Same app rule as #50b (buyback ≤ −2 %, dilution ≥ +5 %), excess vs the equal-weight universe of the "
             f"same country, pooled. Bonferroni α/{n_trials}.")
    if not with_data:
        return "\n".join(L + ["", "No share data from Yahoo — test not possible."])
    fy = sorted({d.year for c in with_data.values() for d in c.index})
    L.append(f"Fiscal years with share changes: {fy[0]}–{fy[-1]}.")
    _, rets = monthly_returns(prices)
    years = range(fy[0] + 1, pd.Timestamp.today().year + 1)
    groups = build_groups(with_data, country, years)
    L.append("")
    L.append("| formation (June) | stocks | buyback | dilution | neutral | per country |")
    L.append("|---|--:|--:|--:|--:|---|")
    for y, sel in groups.items():
        cnt = pd.Series([v[1] for v in sel.values()]).value_counts()
        pc = pd.Series([v[0] for v in sel.values()]).value_counts()
        L.append(f"| {y} | {len(sel)} | {cnt.get('buyback', 0)} | {cnt.get('dilution', 0)} | {cnt.get('neutral', 0)} | "
                 + ", ".join(f"{k} {v}" for k, v in pc.items()) + " |")
    ex = group_excess(groups, rets)
    L.append("")
    if ex.empty:
        return "\n".join(L + ["Too few priced stocks per country."])
    L.append("| group | months | excess vs country universe p.a. | t | years positive |")
    L.append("|---|--:|--:|--:|--:|")
    for g in ("buyback", "dilution", "neutral"):
        x = ex[g].dropna()
        st = mstat(x)
        yr = x.groupby(x.index.year).sum()
        L.append(f"| {g} | {len(x)} | {100*st['ann']:+.1f} % | {st['t']:+.2f} | {int((yr > 0).sum())}/{len(yr)} |")
    d = (ex["buyback"] - ex["dilution"]).dropna()
    st = mstat(d)
    L.append(f"| buyback − dilution | {len(d)} | {100*st['ann']:+.1f} % | {st['t']:+.2f} | — |")
    L.append("")
    L.append("US reference (#50b, 2009–2025): buyback +2.1 %/yr (t 2.8), dilution −3.0 %/yr (t −2.5). "
             "Same sign here = consistent; with few years a non-significant result is expected even if the effect "
             "is real (#59: ~7–9 years needed at this tracking error).")
    return "\n".join(L)
