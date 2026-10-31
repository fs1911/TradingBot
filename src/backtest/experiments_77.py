"""
Experiment #77 — short interest as a warning sign (FINRA consolidated short interest).

FINRA publishes short positions twice a month (settlement mid-month and month-end), with
about 7–8 business days delay. Signal: days to cover = short position / average daily volume
(Hong, Li, Ni, Scheinkman, Xiong 2016: a cleaner measure than short interest alone).
Pre-registered test:
  universe   large caps (SEC assets ≥ $1bn, as #75), price ≥ $5 at formation
  formation  the mid-month settlement of each month; signal usable 10 business days later
  outcome    next 21 trading days (1 M) and 63 (3 M) vs SPY, by days-to-cover decile
  main test  decile 10 (most shorted) minus decile 1, monthly series, t-stat; halves
  warning    share of 'disasters' (≤ −20 % vs SPY within 3 M) in decile 10 vs the rest
Pure, injected for CI (`post` is a callable(url, body_bytes) → str).
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

FINRA_URL = "https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest"
FIELDS = ["symbolCode", "settlementDate", "currentShortPositionQuantity", "averageDailyVolumeQuantity"]


def parse_rows(body: str) -> pd.DataFrame:
    js = json.loads(body) if body and body.strip() else []
    if not isinstance(js, list) or not js:
        return pd.DataFrame(columns=["symbol", "date", "short", "adv"])
    d = pd.DataFrame(js)
    if "symbolCode" not in d:
        return pd.DataFrame(columns=["symbol", "date", "short", "adv"])
    out = pd.DataFrame({"symbol": d["symbolCode"].astype(str).str.strip().str.upper(),
                        "date": pd.to_datetime(d.get("settlementDate"), errors="coerce"),
                        "short": pd.to_numeric(d.get("currentShortPositionQuantity"), errors="coerce"),
                        "adv": pd.to_numeric(d.get("averageDailyVolumeQuantity"), errors="coerce")})
    return out.dropna(subset=["date", "short"])


def fetch_month(post, month: pd.Period, symbols: set, limit: int = 5000, max_pages: int = 12) -> tuple:
    """All rows of one month (paginated), filtered to `symbols` right away. → (DataFrame, error)."""
    parts = []
    for page in range(max_pages):
        body = json.dumps({"limit": limit, "offset": page * limit, "fields": FIELDS,
                           "dateRangeFilters": [{"fieldName": "settlementDate",
                                                 "startDate": f"{month.start_time:%Y-%m-%d}",
                                                 "endDate": f"{month.end_time:%Y-%m-%d}"}]}).encode()
        try:
            rows = parse_rows(post(FINRA_URL, body))
        except Exception as e:
            return (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()), repr(e)[:120]
        if rows.empty:
            break
        parts.append(rows[rows["symbol"].isin(symbols)])
        if len(rows) < limit:
            break
    return (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()), None


def fetch_short_interest(post, months, symbols: set, log=None, sleep: float = 0.4) -> tuple:
    import time as _t
    parts, errors = [], []
    for m in months:
        df, err = fetch_month(post, m, symbols)
        if err:
            errors.append(f"{m}: {err}")
        if len(df):
            parts.append(df)
        if log:
            log(f"#77 {m}: {len(df)} rows" + (f" ({err})" if err else ""))
        _t.sleep(sleep)
    return (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()), errors


def mid_month(si: pd.DataFrame) -> pd.DataFrame:
    """Keep, per month, the settlement date closest to the 15th."""
    if si.empty:
        return si
    dates = pd.Series(sorted(si["date"].unique()))
    keep = dates.groupby(dates.dt.to_period("M")).apply(lambda s: s.iloc[(s.dt.day - 15).abs().argmin()])
    return si[si["date"].isin(set(keep))]


def panel(si: pd.DataFrame, prices: dict, spy: pd.Series, lag: int = 10) -> pd.DataFrame:
    """One row per (formation date, stock): days to cover, decile, excess 1 M / 3 M, 3-M disaster."""
    rows = []
    si = mid_month(si)
    si = si[(si["adv"] > 0)]
    for d, g in si.groupby("date"):
        recs = []
        for sym, sh, adv in zip(g["symbol"], g["short"], g["adv"]):
            px = prices.get(sym)
            if px is None:
                continue
            idx = px.index
            k = idx.searchsorted(d) + lag
            if k + 63 >= len(idx):
                continue
            p0 = float(px.iloc[k])
            if not p0 >= 5.0:
                continue
            s0, s1, s3 = spy.asof(idx[k]), spy.asof(idx[k + 21]), spy.asof(idx[k + 63])
            r1 = float(px.iloc[k + 21]) / p0 - 1
            r3 = float(px.iloc[k + 63]) / p0 - 1
            if not (-0.95 < r1 < 3 and -0.95 < r3 < 3):
                continue
            low = float(px.iloc[k:k + 64].min()) / p0 - 1
            recs.append((d, sym, sh / adv, r1 - (s1 / s0 - 1), r3 - (s3 / s0 - 1), low - (s3 / s0 - 1)))
        if len(recs) >= 50:
            f = pd.DataFrame(recs, columns=["date", "symbol", "dtc", "ex1", "ex3", "low3"])
            f["decile"] = pd.qcut(f["dtc"].rank(method="first"), 10, labels=False) + 1
            rows.append(f)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def tstat(x: pd.Series) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else float("nan")


def run_experiment77_report(si: pd.DataFrame, errors: list, prices: dict, spy: pd.Series, n_trials: int = 320) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #77 — short interest as a warning sign ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"FINRA rows kept (universe only): {len(si):,}; months with errors: {len(errors)}"
             + (f" (first: {errors[0]})" if errors else "") + ".")
    p = panel(si, prices, spy) if not si.empty else pd.DataFrame()
    if p.empty:
        L.append("Not enough data for the test.")
        return "\n".join(L)
    L.append(f"{p['date'].nunique()} formation months {p['date'].min():%Y-%m}–{p['date'].max():%Y-%m}, "
             f"{p['symbol'].nunique():,} stocks, {len(p):,} stock-months. Signal used 10 business days after settlement.")
    L.append("")
    L.append("| days-to-cover decile | median days | 1 M vs SPY mean / median | 3 M vs SPY mean | share ≤ −20 % vs SPY within 3 M |")
    L.append("|---|--:|--:|--:|--:|")
    for k, g in p.groupby("decile"):
        L.append(f"| {int(k)}{' (least shorted)' if k == 1 else ' (most shorted)' if k == 10 else ''} | {g['dtc'].median():.1f} | "
                 f"{100*g['ex1'].mean():+.2f} % / {100*g['ex1'].median():+.2f} % | {100*g['ex3'].mean():+.2f} % | "
                 f"{100*(g['low3'] <= -0.20).mean():.1f} % |")
    m = p.groupby(["date", "decile"])["ex1"].mean().unstack()
    ls = (m[10] - m[1]).dropna()
    half = ls.index[len(ls) // 2] if len(ls) else None
    L.append("")
    L.append(f"- decile 10 − decile 1, 1 M: {100*ls.mean():+.2f} % per month (t {tstat(ls):+.2f}, {len(ls)} months) "
             f"≈ {100*((1+ls.mean())**12-1):+.1f} %/yr before costs")
    if half is not None:
        a, b = ls[ls.index < half], ls[ls.index >= half]
        L.append(f"- first half (→ {half:%Y-%m}): {100*a.mean():+.2f} % (t {tstat(a):+.2f}); second half: {100*b.mean():+.2f} % (t {tstat(b):+.2f})")
    top, rest = p[p["decile"] == 10], p[p["decile"] < 10]
    L.append(f"- warning view: 'disaster' (≤ −20 % vs SPY within 3 M) in the most-shorted decile {100*(top['low3'] <= -0.2).mean():.1f} % "
             f"vs {100*(rest['low3'] <= -0.2).mean():.1f} % for the rest")
    L.append("")
    L.append(f"Bonferroni α/{n_trials} → |t| > 3.4. Survivorship: only currently listed tickers have Yahoo prices "
             f"(heavily shorted stocks that later failed are missing → biases AGAINST finding a warning effect).")
    return "\n".join(L)
