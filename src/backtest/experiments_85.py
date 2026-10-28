"""
Experiment #85 — the 'fair value' and 'health score' approach (as used by apps such as
foliologic.app): do stocks that look cheap against their sector, or that score as
'healthy', beat the market?

Data: SEC XBRL frames (all US filers), fiscal year Y, used from the end of June Y+1
(point-in-time), firms with assets ≥ $1bn and price ≥ $5, sector = 2-digit SIC (SEC
submissions), equal-weight, held 12 months, measured against the equal-weight universe.

Fair value (pre-registered, sector-relative, like the app's multiples methods):
  earnings   FV = net income × sector-median P/E
  cash flow  FV = (operating cash flow − capex) × sector-median P/FCF
  EV/EBITDA  FV = EBITDA × sector-median EV/EBITDA − net debt
  composite  = median of the available methods; upside = composite / market cap − 1;
  dispersion = (max − min) / median of the methods ('robust' if < 15 %).
  Portfolios: upside quintiles; 'undervalued' = upside > 0; 'robust & undervalued'.
  App sell rule approximated: drop a stock after two consecutive years overvalued.
Health score (six dimensions, sector percentile → green ≥ 2/3, gold ≥ 1/3, red; score =
mean × 50, missing dimension → no score): profitability (net margin, ROE, gross margin),
growth (revenue growth), moat (return on capital, gross margin), balance sheet (low debt/
equity, current ratio), cash (FCF margin), valuation (earnings yield). Quintiles.
Pure, injected for CI.
"""
from __future__ import annotations
import json
import math
import numpy as np
import pandas as pd

FRAME = "https://data.sec.gov/api/xbrl/frames/{tax}/{tag}/{unit}/{period}.json"
DURATION = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "GrossProfit", "CostOfRevenue",
            "NetIncomeLoss", "OperatingIncomeLoss", "DepreciationDepletionAndAmortization",
            "DepreciationAndAmortization", "NetCashProvidedByUsedInOperatingActivities",
            "PaymentsToAcquirePropertyPlantAndEquipment"]
INSTANT = ["Assets", "StockholdersEquity", "Liabilities", "LongTermDebt", "LongTermDebtNoncurrent",
           "CashAndCashEquivalentsAtCarryingValue", "AssetsCurrent", "LiabilitiesCurrent"]
SHARES = ("dei", "EntityCommonStockSharesOutstanding", "shares")


def parse_frame(js: dict) -> pd.Series:
    try:
        d = {int(x["cik"]): float(x["val"]) for x in js["data"]}
        return pd.Series(d, dtype=float)
    except (KeyError, TypeError, ValueError):
        return pd.Series(dtype=float)


def fetch_year(get, y: int) -> pd.DataFrame:
    """All tags for fiscal (calendar) year y → DataFrame cik × tag."""
    cols = {}
    for t in DURATION:
        try:
            cols[t] = parse_frame(json.loads(get(FRAME.format(tax="us-gaap", tag=t, unit="USD", period=f"CY{y}"))))
        except Exception:
            cols[t] = pd.Series(dtype=float)
    for t in INSTANT:
        try:
            cols[t] = parse_frame(json.loads(get(FRAME.format(tax="us-gaap", tag=t, unit="USD", period=f"CY{y}Q4I"))))
        except Exception:
            cols[t] = pd.Series(dtype=float)
    try:
        tax, tag, unit = SHARES
        cols["shares"] = parse_frame(json.loads(get(FRAME.format(tax=tax, tag=tag, unit=unit, period=f"CY{y}Q4I"))))
    except Exception:
        cols["shares"] = pd.Series(dtype=float)
    return pd.DataFrame(cols)


def fundamentals(df: pd.DataFrame, prev: pd.DataFrame | None) -> pd.DataFrame:
    g = lambda c: df[c] if c in df else pd.Series(np.nan, index=df.index)
    rev = g("Revenues").combine_first(g("RevenueFromContractWithCustomerExcludingAssessedTax"))
    gp = g("GrossProfit").combine_first(rev - g("CostOfRevenue"))
    da = g("DepreciationDepletionAndAmortization").combine_first(g("DepreciationAndAmortization"))
    debt = g("LongTermDebt").combine_first(g("LongTermDebtNoncurrent")).fillna(0.0)
    eq = g("StockholdersEquity")
    out = pd.DataFrame({
        "assets": g("Assets"), "rev": rev, "ni": g("NetIncomeLoss"),
        "fcf": g("NetCashProvidedByUsedInOperatingActivities") - g("PaymentsToAcquirePropertyPlantAndEquipment").fillna(0),
        "ebitda": g("OperatingIncomeLoss") + da, "net_debt": debt - g("CashAndCashEquivalentsAtCarryingValue").fillna(0),
        "equity": eq, "gross_margin": gp / rev, "net_margin": g("NetIncomeLoss") / rev,
        "roe": g("NetIncomeLoss") / eq.where(eq > 0), "roc": g("OperatingIncomeLoss") / (eq.where(eq > 0) + debt),
        "debt_equity": debt / eq.where(eq > 0), "current_ratio": g("AssetsCurrent") / g("LiabilitiesCurrent"),
        "shares": g("shares")})
    if prev is not None and not prev.empty:
        pr = prev["Revenues"].combine_first(prev.get("RevenueFromContractWithCustomerExcludingAssessedTax",
                                                     pd.Series(dtype=float)))
        out["growth"] = rev / pr.reindex(out.index) - 1
    else:
        out["growth"] = np.nan
    out["fcf_margin"] = out["fcf"] / out["rev"]
    return out.replace([np.inf, -np.inf], np.nan)


def fair_value(f: pd.DataFrame, mcap: pd.Series, sector: pd.Series, min_sector: int = 10) -> pd.DataFrame:
    """Sector-relative multiples → per-method fair values, composite upside and dispersion."""
    d = f.copy()
    d["mcap"] = mcap.reindex(d.index)
    d["sector"] = sector.reindex(d.index).fillna("other")
    d["ev"] = d["mcap"] + d["net_debt"].fillna(0)
    mult = {"pe": ("ni", "mcap"), "pfcf": ("fcf", "mcap"), "evebitda": ("ebitda", "ev")}
    for k, (num, den) in mult.items():
        ratio = (d[den] / d[num]).where((d[num] > 0) & (d[den] > 0))
        sec_med = ratio.groupby(d["sector"]).transform(lambda x: x.median() if x.notna().sum() >= min_sector else np.nan)
        d[k + "_med"] = sec_med.fillna(ratio.median())
    d["fv_e"] = (d["ni"] * d["pe_med"]).where(d["ni"] > 0)
    d["fv_c"] = (d["fcf"] * d["pfcf_med"]).where(d["fcf"] > 0)
    d["fv_x"] = (d["ebitda"] * d["evebitda_med"] - d["net_debt"].fillna(0)).where(d["ebitda"] > 0)
    fv = d[["fv_e", "fv_c", "fv_x"]].where(lambda x: x > 0)
    d["fv"] = fv.median(axis=1)
    d["n_methods"] = fv.notna().sum(axis=1)
    d["dispersion"] = (fv.max(axis=1) - fv.min(axis=1)) / d["fv"]
    d["upside"] = d["fv"] / d["mcap"] - 1
    return d


def health_score(f: pd.DataFrame, sector: pd.Series, earnings_yield: pd.Series) -> pd.Series:
    d = f.copy()
    d["sector"] = sector.reindex(d.index).fillna("other")
    d["ey"] = earnings_yield.reindex(d.index)
    dims = {"profit": ["net_margin", "roe", "gross_margin"], "growth": ["growth"], "moat": ["roc", "gross_margin"],
            "balance": ["-debt_equity", "current_ratio"], "cash": ["fcf_margin"], "value": ["ey"]}
    pts = {}
    for dim, cols in dims.items():
        ranks = []
        for c in cols:
            neg = c.startswith("-")
            col = c.lstrip("-")
            x = -d[col] if neg else d[col]
            ranks.append(x.groupby(d["sector"]).rank(pct=True))
        r = pd.concat(ranks, axis=1).mean(axis=1)
        pts[dim] = np.where(r >= 2 / 3, 2.0, np.where(r >= 1 / 3, 1.0, 0.0))
        pts[dim] = pd.Series(pts[dim], index=d.index).where(r.notna())
    P = pd.DataFrame(pts)
    return (P.mean(axis=1) * 50).where(P.notna().all(axis=1))       # any grey dimension → no score


def two_strike_portfolio(upside_by_year: dict) -> dict:
    """App-like rule: hold what was undervalued; drop after two consecutive overvalued years."""
    held, strikes, out = set(), {}, {}
    for y in sorted(upside_by_year):
        u = upside_by_year[y].dropna()
        for t in list(held):
            if t not in u.index:
                held.discard(t); strikes.pop(t, None); continue
            strikes[t] = strikes.get(t, 0) + 1 if u[t] < 0 else 0
            if strikes[t] >= 2:
                held.discard(t); strikes.pop(t, None)
        held |= set(u.index[u > 0])
        if held:
            out[y] = sorted(held)
    return out


def run_experiment85_report(years_data: dict, sector: pd.Series, tmap: dict, px: pd.DataFrame, rets: pd.DataFrame,
                            min_assets: float = 1e9, n_trials: int = 320) -> str:
    """years_data: {fiscal year: raw frames DataFrame (cik × tag)}; sector: cik → SIC 2-digit."""
    from datetime import datetime, timezone
    from .experiments_49 import form_portfolios, mstat
    from .experiments_50 import selected_portfolio
    L = [f"# Experiment #85 — 'fair value' & 'health score' (app approach) ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    ups, hs, rob, und, stats_rows = {}, {}, {}, {}, []
    for y in sorted(years_data):
        f = fundamentals(years_data[y], years_data.get(y - 1))
        f = f[f["assets"] >= min_assets]
        tick = pd.Series({c: tmap.get(int(c)) for c in f.index}).dropna()
        f = f.loc[tick.index]
        form = pd.Period(f"{y + 1}-06", "M")
        if form not in px.index:
            continue
        price = px.loc[form].reindex(tick.to_numpy())
        price.index = tick.index
        mcap = price * f["shares"]
        sec = sector.reindex(f.index)
        fv = fair_value(f, mcap, sec)
        fv = fv[(price >= 5) & fv["mcap"].notna()]
        fv.index = tick.reindex(fv.index).to_numpy()
        fv = fv[~fv.index.duplicated()]
        hsc = health_score(f, sec, f["ni"] / mcap)
        hsc.index = tick.reindex(hsc.index).to_numpy()
        hsc = hsc[~hsc.index.duplicated()].reindex(fv.index)
        u = fv["upside"].where(fv["n_methods"] >= 1)
        ups[y], hs[y] = u.dropna(), hsc.dropna()
        und[y] = list(u.index[u > 0])
        rob[y] = list(u.index[(u > 0) & (fv["dispersion"] < 0.15) & (fv["n_methods"] >= 2)])
        stats_rows.append((y, len(fv), int(u.notna().sum()), float(fv["dispersion"].lt(0.15).mean()),
                           int((u > 0).sum()), len(rob[y]), int(hsc.notna().sum())))
    if not ups:
        return "\n".join(L + ["No data."])
    L.append("| fiscal year | firms | with fair value | methods agree (< 15 %) | undervalued | robust & undervalued | with health score |")
    L.append("|---|--:|--:|--:|--:|--:|--:|")
    for y, n, nv, agr, nu, nr, nh in stats_rows:
        L.append(f"| {y} | {n} | {nv} | {100*agr:.0f} % | {nu} | {nr} | {nh} |")
    L.append("")

    def line(name, port_r, uni_r):
        ex = (port_r - uni_r).dropna()
        st = mstat(ex)
        yr = ex.groupby(ex.index.year).sum()
        return f"| {name} | {len(ex)} | {100*st['ann']:+.1f} % | {st['t']:+.2f} | {int((yr > 0).sum())}/{len(yr)} |"

    L.append("## Fair value: excess return vs the equal-weight universe (12-month holds)")
    L.append("| portfolio | months | excess p.a. | t | years positive |")
    L.append("|---|--:|--:|--:|--:|")
    pq = form_portfolios(ups, px, rets)
    if not pq.empty:
        for q in range(1, 6):
            lbl = {1: "upside Q1 (most 'overvalued')", 5: "upside Q5 (most 'undervalued')"}.get(q, f"upside Q{q}")
            L.append(line(lbl, pq[f"Q{q}"], pq["universe"]))
        L.append(line("Q5 − Q1", pq["Q5"] - pq["Q1"] + pq["universe"], pq["universe"]))
        for nm, sel in (("all 'undervalued' (upside > 0)", und), ("robust & undervalued (dispersion < 15 %)", rob),
                        ("app rule: hold undervalued, sell after 2× overvalued", two_strike_portfolio(ups))):
            r = selected_portfolio(sel, px, rets)
            L.append(line(nm, r, pq["universe"].reindex(r.index)))
    L.append("")
    L.append("## Health score (six dimensions) quintiles")
    L.append("| portfolio | months | excess p.a. | t | years positive |")
    L.append("|---|--:|--:|--:|--:|")
    ph = form_portfolios(hs, px, rets)
    if not ph.empty:
        for q in range(1, 6):
            L.append(line(f"health Q{q}" + (" (best)" if q == 5 else " (worst)" if q == 1 else ""), ph[f"Q{q}"], ph["universe"]))
    L.append("")
    L.append(f"Bonferroni α/{n_trials} → |t| ≳ 3.7. Survivorship: only currently listed tickers have prices (biased "
             f"upwards for all groups alike). The fair value here is a faithful re-implementation of the published "
             f"method, not the app's own numbers.")
    return "\n".join(L)


def fetch_sic(ciks: list, ua: str, timeout: int = 30, log=None) -> pd.Series:
    """cik → 2-digit SIC code (sector) from the SEC submissions API (≈ 8 requests/second)."""
    import time as _t
    import urllib.request
    out = {}
    for i, c in enumerate(ciks):
        try:
            req = urllib.request.Request(f"https://data.sec.gov/submissions/CIK{int(c):010d}.json",
                                         headers={"User-Agent": ua, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                sic = str(json.loads(r.read().decode("utf-8")).get("sic") or "")
            if len(sic) >= 2:
                out[int(c)] = sic[:2]
        except Exception:
            pass
        _t.sleep(0.13)
        if log and i % 500 == 0:
            log(f"#85 SIC {i}/{len(ciks)}")
    return pd.Series(out, dtype=object)
