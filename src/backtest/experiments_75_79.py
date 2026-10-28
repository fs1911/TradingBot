"""
Experiments #75 and #79 (US stocks, SEC + Yahoo).

#75 Post-earnings drift: standardised unexpected earnings SUE = (EPS_q − EPS_{q−4}) /
    std of the previous 8 such changes (seasonal random walk, Foster/Olsen/Shevlin 1984),
    from 10-Q diluted EPS (SEC companyconcept). Event date = 10-Q FILING date (public;
    usually days after the earnings release, so this tests the LATE part of the drift).
    Return minus SPY over the next 60 trading days, by SUE decile; top − bottom decile per
    calendar quarter with t; before / after 2016.
#79 Dividends (Yahoo dividend events): at the end of June each year, groups by the last
    12 months of dividends vs the 12 months before — initiators, raisers (≥ +5 %), steady,
    cutters (≤ −20 % or stopped), non-payers, and 'growers' (raised in each of the last 5
    years, aristocrat-like). Next-12-month return vs the equal-weight universe.
Pure, injected for CI.
"""
from __future__ import annotations
import json
import math
import numpy as np
import pandas as pd

EPS_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/EarningsPerShareDiluted.json"


def fetch_px_divs(sym: str, start: str = "2005-01-01", timeout: int = 20) -> tuple:
    """Yahoo chart API → (adjusted close Series, dividends Series)."""
    import time as _t
    import urllib.parse
    import urllib.request
    p1 = int(pd.Timestamp(start).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={p1}"
           f"&period2={int(_t.time())}&interval=1d&events=div")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"}),
                                    timeout=timeout) as r:
            return parse_px_divs(r.read().decode("utf-8", "replace"))
    except Exception:
        return pd.Series(dtype=float), pd.Series(dtype=float)


def parse_px_divs(text: str) -> tuple:
    try:
        res = json.loads(text)["chart"]["result"][0]
        ts = pd.to_datetime(res["timestamp"], unit="s").normalize()
        ind = res["indicators"]
        close = (ind.get("adjclose") or [{}])[0].get("adjclose") or ind["quote"][0]["close"]
        px = pd.Series(close, index=ts, dtype=float).dropna()
        px = px[~px.index.duplicated(keep="last")].sort_index()
        dv = res.get("events", {}).get("dividends", {})
        divs = pd.Series({pd.to_datetime(int(v["date"]), unit="s").normalize(): float(v["amount"]) for v in dv.values()},
                         dtype=float).sort_index()
        return px, divs
    except (KeyError, IndexError, TypeError, ValueError):
        return pd.Series(dtype=float), pd.Series(dtype=float)


# ── #75 ──────────────────────────────────────────────────────────────────────

def parse_eps(js: dict) -> pd.DataFrame:
    """10-Q quarterly diluted EPS: [end, filed, eps] (3-month periods, first filing)."""
    try:
        facts = js["units"]["USD/shares"]
    except (KeyError, TypeError):
        return pd.DataFrame()
    rows = []
    for f in facts:
        if f.get("form") != "10-Q" or "start" not in f:
            continue
        s, e = pd.Timestamp(f["start"]), pd.Timestamp(f["end"])
        if 80 <= (e - s).days <= 100:
            rows.append((e, pd.Timestamp(f["filed"]), float(f["val"])))
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows, columns=["end", "filed", "eps"]).sort_values("filed").drop_duplicates("end", keep="first")
    return d.sort_values("end").reset_index(drop=True)


def sue(d: pd.DataFrame) -> pd.DataFrame:
    """SUE with the seasonal random walk (same quarter last year, 350–380 days earlier)."""
    if d.empty:
        return d
    d = d.copy()
    chg = []
    for i, r in d.iterrows():
        prev = d[(d["end"] <= r["end"] - pd.Timedelta(days=350)) & (d["end"] >= r["end"] - pd.Timedelta(days=380))]
        chg.append(r["eps"] - prev["eps"].iloc[-1] if len(prev) else np.nan)
    d["chg"] = chg
    d["sd"] = d["chg"].shift(1).rolling(8, min_periods=4).std()
    d["sue"] = d["chg"] / d["sd"].where(d["sd"] > 0)
    return d.dropna(subset=["sue"])


def drift(px: pd.Series, spy: pd.Series, date: pd.Timestamp, start: int = 1, days: int = 60) -> float:
    after = px.index[px.index > date]
    if len(after) < start + days + 1:
        return float("nan")
    d0, d1 = after[start - 1], after[start - 1 + days]
    s0, s1 = spy.asof(d0), spy.asof(d1)
    if not (np.isfinite(s0) and np.isfinite(s1)) or s0 <= 0:
        return float("nan")
    return float(px[d1] / px[d0] - 1 - (s1 / s0 - 1))


def pead_events(eps: dict, tmap: dict, prices: dict, spy: pd.Series) -> pd.DataFrame:
    rows = []
    for cik, d in eps.items():
        t = tmap.get(int(cik))
        px = prices.get(t)
        if not t or px is None or len(px) < 300:
            continue
        for _, r in sue(d).iterrows():
            rows.append((t, r["filed"], float(r["sue"]), drift(px, spy, r["filed"])))
    ev = pd.DataFrame(rows, columns=["ticker", "filed", "sue", "drift"]).dropna()
    if len(ev):
        ev["q"] = ev["filed"].dt.to_period("Q")
        ev["dec"] = ev.groupby("q")["sue"].transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False) + 1
                                                    if len(x) >= 50 else np.nan)
    return ev


# ── #79 ──────────────────────────────────────────────────────────────────────

def dividend_group(divs: pd.Series, form: pd.Timestamp) -> str:
    if divs is None or len(divs) == 0:
        return "non-payer"
    d = divs[divs.index <= form]
    last12 = d[d.index > form - pd.DateOffset(years=1)].sum()
    prev12 = d[(d.index > form - pd.DateOffset(years=2)) & (d.index <= form - pd.DateOffset(years=1))].sum()
    before = d[d.index <= form - pd.DateOffset(years=1)]
    if last12 == 0 and prev12 == 0:
        return "non-payer"
    if last12 > 0 and before[before.index > form - pd.DateOffset(years=4)].sum() == 0:
        return "initiator"
    if prev12 > 0 and (last12 == 0 or last12 <= 0.8 * prev12):
        return "cutter"
    yearly = [d[(d.index > form - pd.DateOffset(years=k + 1)) & (d.index <= form - pd.DateOffset(years=k))].sum()
              for k in range(6)]
    if all(yearly[k] > yearly[k + 1] * 1.0 > 0 for k in range(5)):
        return "grower (5 y)"
    if last12 >= 1.05 * prev12:
        return "raiser"
    return "steady"


def run_experiments75_79_report(eps: dict, tmap: dict, prices: dict, divs: dict, spy: pd.Series) -> str:
    from datetime import datetime, timezone
    from .experiments_49 import monthly_returns, mstat
    L = [f"# Experiments #75 / #79 — post-earnings drift, dividends ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("## #75 Post-earnings drift (SUE from 10-Q EPS, from the filing date, next 60 trading days vs SPY)")
    ev = pead_events(eps, tmap, prices, spy)
    if ev.empty or ev["dec"].isna().all():
        L.append("Too few events.")
    else:
        L.append(f"{len(ev):,} quarterly events, {ev['ticker'].nunique():,} stocks, {ev['q'].min()}–{ev['q'].max()}.")
        L.append("| SUE decile | events | 60-day return vs SPY |")
        L.append("|---|--:|--:|")
        for dcl, g in ev.dropna(subset=["dec"]).groupby("dec"):
            L.append(f"| {int(dcl)}{' (worst surprise)' if dcl == 1 else ' (best surprise)' if dcl == 10 else ''} | {len(g):,} | {100*g['drift'].mean():+.2f} % |")
        qs = ev.dropna(subset=["dec"]).groupby(["q", "dec"])["drift"].mean().unstack()
        if 1 in qs and 10 in qs:
            spread = (qs[10] - qs[1]).dropna()
            for lbl, s in (("all", spread), ("≤ 2015", spread[spread.index.year <= 2015]), ("2016 →", spread[spread.index.year >= 2016])):
                t = s.mean() / s.std() * math.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else float("nan")
                L.append(f"- top − bottom decile, {lbl}: {100*s.mean():+.2f} % per 60 days ({len(s)} quarters, t {t:+.2f}); "
                         f"≈ {100*((1+s.mean())**4-1):+.1f} %/yr before costs if traded every quarter")
    L.append("")
    L.append("## #79 Dividends (groups at the end of June, next 12 months vs equal-weight universe)")
    _, rets = monthly_returns(prices)
    rows = []
    for y in range(2008, pd.Timestamp.today().year):
        form = pd.Timestamp(f"{y}-06-30")
        m0 = pd.Period(f"{y}-06", "M")
        if m0 not in rets.index:
            continue
        fwd_m = [m for m in pd.period_range(m0 + 1, m0 + 12, freq="M") if m in rets.index]
        if len(fwd_m) < 12:
            continue
        fwd = (1 + rets.loc[fwd_m].fillna(0)).prod() - 1
        for t, dv in divs.items():
            if t in fwd.index and np.isfinite(fwd[t]) and t in prices and pd.Series(prices[t]).index[0] < form - pd.DateOffset(years=6):
                rows.append((y, t, dividend_group(dv, form), float(fwd[t])))
    d = pd.DataFrame(rows, columns=["year", "ticker", "group", "fwd"])
    if d.empty:
        L.append("No dividend data.")
        return "\n".join(L)
    d["excess"] = d["fwd"] - d.groupby("year")["fwd"].transform("mean")
    L.append(f"{len(d):,} stock-years, {d['year'].min()}–{d['year'].max()} (stocks with ≥ 6 years of history).")
    L.append("| group | stock-years | avg per year | excess vs universe p.a. | t (across years) | years positive |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for g in ("grower (5 y)", "raiser", "steady", "initiator", "cutter", "non-payer"):
        x = d[d["group"] == g]
        if x.empty:
            continue
        yr = x.groupby("year")["excess"].mean()
        t = yr.mean() / yr.std() * math.sqrt(len(yr)) if len(yr) > 2 and yr.std() > 0 else float("nan")
        L.append(f"| {g} | {len(x):,} | {len(x)/x['year'].nunique():.0f} | {100*yr.mean():+.1f} % | {t:+.2f} | "
                 f"{int((yr > 0).sum())}/{len(yr)} |")
    L.append("")
    L.append("Survivorship: Yahoo only has currently listed tickers — dividend cutters that later went bankrupt are "
             "missing (biases the 'cutter' group upwards).")
    return "\n".join(L)
