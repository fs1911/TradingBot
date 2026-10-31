"""
Experiments #77, #78, #80 (public data, data access checked at run time).

#78 IPOs: a company is an IPO if its SEC filing history contains an S-1/F-1 and a final
    prospectus 424B4, AND its Yahoo price history starts within 30 days after that 424B4
    (first trading). Returns 1 and 3 years after the first close vs SPY and vs the
    equal-weight average of all priced stocks; by IPO year. Strong survivorship: failed IPOs
    that were delisted have no Yahoo prices → results biased UPWARDS.
#80 S&P 500 index additions/removals (Wikipedia 'Selected changes'): excess return vs SPY in
    the 20 trading days before the effective date (run-up) and 0…+250 days after.
#77 Short interest (FINRA): reachability check of the public API; analysis only if data.
Pure, injected for CI.
"""
from __future__ import annotations
import html as _html
import json
import re
import numpy as np
import pandas as pd


# ── SEC submissions (shared with #85: SIC) ───────────────────────────────────

def parse_submissions(js: dict) -> dict:
    rec = js.get("filings", {}).get("recent", {})
    forms, dates = rec.get("form", []), rec.get("filingDate", [])
    d = pd.DataFrame({"form": forms, "date": pd.to_datetime(dates, errors="coerce")}).dropna()
    reg = d[d["form"].isin(["S-1", "F-1", "S-1/A", "F-1/A"])]
    pro = d[d["form"] == "424B4"].sort_values("date")
    ipo = None
    if len(reg) and len(pro):
        later = pro[pro["date"] >= reg["date"].min()]
        if len(later):
            ipo = later["date"].iloc[0]
    sic = str(js.get("sic") or "")
    return {"sic2": sic[:2] if len(sic) >= 2 else None, "ipo_prospectus": ipo}


def fetch_submissions(ciks: list, ua: str, timeout: int = 30, log=None) -> pd.DataFrame:
    import time as _t
    import urllib.request
    rows = {}
    for i, c in enumerate(ciks):
        try:
            req = urllib.request.Request(f"https://data.sec.gov/submissions/CIK{int(c):010d}.json",
                                         headers={"User-Agent": ua, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                rows[int(c)] = parse_submissions(json.loads(r.read().decode("utf-8")))
        except Exception:
            pass
        _t.sleep(0.12)
        if log and i % 1000 == 0:
            log(f"SEC submissions {i}/{len(ciks)}")
    return pd.DataFrame(rows).T


# ── #78 ──────────────────────────────────────────────────────────────────────

def ipo_events(subs: pd.DataFrame, tmap: dict, prices: dict, max_lag_days: int = 30) -> pd.DataFrame:
    rows = []
    for cik, r in subs.iterrows():
        t, d = tmap.get(int(cik)), r.get("ipo_prospectus")
        if t is None or d is None or pd.isna(d) or t not in prices:
            continue
        px = pd.Series(prices[t]).dropna()
        if len(px) < 30:
            continue
        first = px.index[0]
        if pd.Timedelta(days=-5) <= first - d <= pd.Timedelta(days=max_lag_days) and first.year >= 2005:
            rows.append((t, first))
    return pd.DataFrame(rows, columns=["ticker", "first_day"])


def horizon_excess(px: pd.Series, bench: pd.Series, start: pd.Timestamp, days: int) -> float:
    after = px.index[px.index >= start]
    if len(after) <= days:
        return float("nan")
    d0, d1 = after[0], after[days]
    b0, b1 = bench.asof(d0), bench.asof(d1)
    if not (np.isfinite(b0) and np.isfinite(b1)) or b0 <= 0:
        return float("nan")
    return float(px[d1] / px[d0] - 1 - (b1 / b0 - 1))


def ew_index(prices: dict, start: str = "2004-01-01") -> pd.Series:
    rets = {}
    for t, s in prices.items():
        s = pd.Series(s).dropna()
        if len(s) > 250:
            rets[t] = s.pct_change()
    r = pd.DataFrame(rets)
    r = r[r.index >= start].clip(-0.5, 1.0)
    return (1 + r.mean(axis=1).fillna(0)).cumprod()


# ── #80 ──────────────────────────────────────────────────────────────────────

def parse_sp500_changes(page: str) -> pd.DataFrame:
    """Wikipedia 'List of S&P 500 companies' → [date, added, removed]. Handles <tr> with
    attributes and dates spanning several rows (rowspan → carried forward)."""
    m = re.search(r'id="changes".*?</table>', page, flags=re.S)
    if not m:
        return pd.DataFrame(columns=["date", "added", "removed"])
    rows, last = [], None
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), flags=re.S):
        if "<td" not in tr:
            continue
        cells = [_html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if not cells:
            continue
        d = pd.to_datetime(cells[0], errors="coerce") if re.search(r"\d{4}", cells[0]) else pd.NaT
        if pd.notna(d):
            last, rest = d, cells[1:]
        elif last is not None:
            rest = cells
        else:
            continue
        if len(rest) >= 4:
            rows.append((last, rest[0] or None, rest[2] or None))
    return pd.DataFrame(rows, columns=["date", "added", "removed"])


def index_effect(changes: pd.DataFrame, prices: dict, spy: pd.Series) -> dict:
    out = {}
    for col in ("added", "removed"):
        pre, post, post20 = [], [], []
        for d, t in zip(changes["date"], changes[col]):
            if not t or t not in prices:
                continue
            px = pd.Series(prices[t]).dropna()
            idx = px.index
            k = idx.searchsorted(d)
            if k < 21 or k + 250 >= len(idx):
                continue
            s = spy
            def ex(a, b):
                return px.iloc[b] / px.iloc[a] - 1 - (s.asof(idx[b]) / s.asof(idx[a]) - 1)
            pre.append(ex(k - 20, k))
            post20.append(ex(k, k + 20))
            post.append(ex(k, k + 250))
        out[col] = {"n": len(pre), "pre20": np.nanmean(pre) if pre else np.nan,
                    "post20": np.nanmean(post20) if post20 else np.nan, "post250": np.nanmean(post) if post else np.nan,
                    "t_post250": (np.nanmean(post) / (np.nanstd(post) / np.sqrt(len(post)))) if len(post) > 5 else np.nan}
    return out


# ── report ───────────────────────────────────────────────────────────────────

def run_experiments77_78_80_report(subs: pd.DataFrame, tmap: dict, prices: dict, spy: pd.Series,
                                   sp_changes: pd.DataFrame, finra_status: str, sp_status: str = "") -> str:
    from datetime import datetime, timezone
    L = [f"# Experiments #77 / #78 / #80 — short interest, IPOs, index changes ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("## #78 IPOs (2005 →)")
    ev = ipo_events(subs, tmap, prices) if subs is not None and not subs.empty else pd.DataFrame()
    if ev.empty:
        L.append("No IPO events identified.")
    else:
        ew = ew_index(prices)
        rows = []
        for t, d in zip(ev["ticker"], ev["first_day"]):
            px = pd.Series(prices[t]).dropna()
            rows.append((d.year, horizon_excess(px, spy, d, 252), horizon_excess(px, spy, d, 756),
                         horizon_excess(px, ew, d, 252), horizon_excess(px, ew, d, 756),
                         px.iloc[min(len(px) - 1, 756)] / px.iloc[0] - 1 if len(px) > 756 else np.nan))
        r = pd.DataFrame(rows, columns=["year", "y1_spy", "y3_spy", "y1_ew", "y3_ew", "abs3"])
        r["spac_like"] = [9.5 <= float(pd.Series(prices[t]).dropna().iloc[0]) <= 10.5 for t in ev["ticker"]]
        L.append(f"{len(r):,} IPOs identified (S-1/F-1 + 424B4 + Yahoo history starting ≤ 30 days later), "
                 f"{r['year'].min()}–{r['year'].max()}.")
        L.append("| | 1 year vs SPY | 3 years vs SPY | 1 year vs EW market | 3 years vs EW market | share losing money after 3 y |")
        L.append("|---|--:|--:|--:|--:|--:|")
        L.append(f"| mean | {100*r['y1_spy'].mean():+.1f} % | {100*r['y3_spy'].mean():+.1f} % | {100*r['y1_ew'].mean():+.1f} % | "
                 f"{100*r['y3_ew'].mean():+.1f} % | {100*(r['abs3'] < 0).mean():.0f} % |")
        L.append(f"| median | {100*r['y1_spy'].median():+.1f} % | {100*r['y3_spy'].median():+.1f} % | {100*r['y1_ew'].median():+.1f} % | "
                 f"{100*r['y3_ew'].median():+.1f} % | |")
        by = r.groupby(r["year"] // 5 * 5)["y3_spy"].agg(["mean", "median", "count"])
        L.append("")
        L.append("3 years vs SPY by IPO period: " + "; ".join(f"{int(k)}–{int(k)+4}: mean {100*v['mean']:+.0f} %, median "
                                                          f"{100*v['median']:+.0f} % (n {int(v['count'])})" for k, v in by.iterrows()) + ".")
        L.append("")
        L.append("SPACs (blank-check shells) also file S-1 + 424B4 and list at ≈ $10. Split by first close:")
        L.append("| group | n | 1 y vs SPY mean / median | 3 y vs SPY mean / median | losing money after 3 y |")
        L.append("|---|--:|--:|--:|--:|")
        for name, g in (("first close $9.50–10.50 (SPAC-like)", r[r["spac_like"]]), ("all other IPOs", r[~r["spac_like"]])):
            if len(g):
                L.append(f"| {name} | {len(g):,} | {100*g['y1_spy'].mean():+.1f} % / {100*g['y1_spy'].median():+.1f} % | "
                         f"{100*g['y3_spy'].mean():+.1f} % / {100*g['y3_spy'].median():+.1f} % | {100*(g['abs3'].dropna() < 0).mean():.0f} % |")
        g = r[~r["spac_like"]]
        if len(g):
            by2 = g.groupby(g["year"] // 5 * 5)["y3_spy"].agg(["mean", "median", "count"])
            L.append("Other IPOs, 3 years vs SPY by period: " + "; ".join(
                f"{int(k)}–{int(k)+4}: mean {100*v['mean']:+.0f} %, median {100*v['median']:+.0f} % (n {int(v['count'])})"
                for k, v in by2.iterrows() if v["count"] > 0) + ".")
        L.append("Excess = stock return minus benchmark return, in percentage points (−100 = e.g. stock −60 %, SPY +40 %).")
        L.append("Survivorship: delisted IPOs are missing — the true average is worse.")
    L.append("")
    L.append("## #80 S&P 500 additions and removals (effective date)")
    if sp_changes is None or sp_changes.empty:
        L.append(f"Change list not reachable or not parsed ({sp_status}).")
    else:
        eff = index_effect(sp_changes, prices, spy)
        L.append(f"{len(sp_changes)} changes listed ({sp_changes['date'].min():%Y}–{sp_changes['date'].max():%Y}).")
        L.append("| | events with prices | 20 days BEFORE vs SPY | first 20 days after | 0 → +250 days vs SPY (t) |")
        L.append("|---|--:|--:|--:|--:|")
        for k, v in eff.items():
            L.append(f"| {k} | {v['n']} | {100*v['pre20']:+.1f} % | {100*v['post20']:+.1f} % | {100*v['post250']:+.1f} % ({v['t_post250']:+.1f}) |")
        L.append("Removed stocks are often acquired or delisted (no prices) → the 'removed' row covers survivors only.")
    L.append("")
    if finra_status:
        L.append("## #77 Short interest (FINRA)")
        L.append(finra_status)
    return "\n".join(L)
