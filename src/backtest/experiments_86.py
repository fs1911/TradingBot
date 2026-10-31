"""
Experiment #86 — base rates after events ("what happened next?").

Not a trading rule: a table of realistic expectations. For pre-registered event types, the
distribution of what S&P 500, SMI, gold and Bitcoin did 1 / 3 / 6 / 12 months later
(median, mean, share positive, 10 % worst case, and the interim low within 12 months),
compared with the same numbers for ANY trading day.

Pre-registered events (fixed before looking at outcomes):
  VIX first close > 30 / > 40 (after ≥ 120 trading days below the level)
  S&P 500 down −10 / −20 / −30 % from its high (first crossing; re-armed at a new high)
  Fed: first cut / first hike after ≥ 6 months without a move in that direction (BIS policy
       rate, monthly → event date = that month's last trading day)
  Yield curve: 10 y − 3 m first < 0 (after ≥ 120 trading days ≥ 0)
  US presidential elections (1928 →)
  Fixed list of geopolitical / crisis shocks (SHOCKS below — not extended afterwards)
  Bitcoin halvings (3 within Yahoo data — descriptive only, no p-value)
Test: random-date bootstrap — draw as many random days as there are events, 5000 times;
two-sided p for the mean forward return; Holm across all cells with ≥ 8 events.
Caveats: price index (no dividends) on both sides, so the comparison is fair; events cluster
in time (overlapping outcomes), so effective n is smaller than the count.
Pure, injected for CI.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

HORIZONS = {"1 M": 21, "3 M": 63, "6 M": 126, "12 M": 252}
SHOCKS = {
    "WW2 begins": "1939-09-01", "Pearl Harbor": "1941-12-08", "Korea war": "1950-06-26",
    "Cuba crisis": "1962-10-22", "JFK shot": "1963-11-22", "Yom Kippur / oil": "1973-10-08",
    "Afghanistan invasion": "1979-12-27", "Kuwait invasion": "1990-08-02", "9/11": "2001-09-17",
    "Iraq war": "2003-03-20", "Lehman": "2008-09-15", "US downgrade": "2011-08-08",
    "Crimea": "2014-03-03", "Brexit vote": "2016-06-24", "Covid crash begins": "2020-02-24",
    "Ukraine invasion": "2022-02-24", "Hamas attack": "2023-10-09", "US tariffs": "2025-04-03",
}
HALVINGS = ["2016-07-09", "2020-05-11", "2024-04-20"]


def _clean(s: pd.Series) -> pd.Series:
    s = pd.Series(s).dropna().astype(float)
    idx = pd.to_datetime(s.index)
    s.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s > 0] if len(s) else s


def on_or_after(index: pd.DatetimeIndex, dates) -> list:
    out = []
    for d in dates:
        i = index.searchsorted(pd.Timestamp(d))
        if i < len(index):
            out.append(index[i])
    return out


def first_cross_above(x: pd.Series, level: float, quiet: int = 120) -> list:
    """Days x closes > level after ≥ `quiet` consecutive days ≤ level."""
    v, out, below = x.to_numpy(), [], quiet
    for i, val in enumerate(v):
        if val > level:
            if below >= quiet:
                out.append(x.index[i])
            below = 0
        else:
            below += 1
    return out


def first_cross_below(x: pd.Series, level: float, quiet: int = 120) -> list:
    return first_cross_above(-x, -level, quiet)


def drawdown_events(px: pd.Series, dd: float) -> list:
    """First day px is ≥ dd below its running high; re-armed once a new high is made."""
    v, out, hi, armed = px.to_numpy(), [], -np.inf, True
    for i, p in enumerate(v):
        if p > hi:
            hi, armed = p, True
        elif armed and p <= hi * (1 - dd):
            out.append(px.index[i]); armed = False
    return out


def policy_events(rate_m: pd.Series, direction: int, pause_months: int = 6) -> list:
    """Month ends of the first move in `direction` (+1 hike, −1 cut) after ≥ pause_months
    without a move in that direction. rate_m: monthly Series (Period or Timestamp index)."""
    r = pd.Series(rate_m).dropna().astype(float)
    if isinstance(r.index, pd.PeriodIndex):
        r.index = r.index.to_timestamp(how="end").normalize()
    d = r.diff()
    out, since = [], pause_months
    for t, x in d.iloc[1:].items():
        if direction * x > 1e-9:
            if since >= pause_months:
                out.append(t)
            since = 0
        else:
            since += 1
    return out


def us_elections(first: int = 1928, last: int = 2024) -> list:
    out = []
    for y in range(first, last + 1, 4):
        nov1 = pd.Timestamp(y, 11, 1)
        monday = nov1 + pd.Timedelta(days=(0 - nov1.weekday()) % 7)
        out.append(monday + pd.Timedelta(days=1))
    return out


def outcomes(px: pd.Series, dates) -> pd.DataFrame:
    """Forward returns per horizon + interim low within 12 months, from the close of each date
    (first trading day on or after it)."""
    idx, v, rows = px.index, px.to_numpy(), []
    for d in dates:
        i = idx.searchsorted(pd.Timestamp(d))
        if i >= len(idx) or (idx[i] - pd.Timestamp(d)).days > 7:
            continue
        row = {"date": idx[i]}
        for h, n in HORIZONS.items():
            row[h] = v[i + n] / v[i] - 1 if i + n < len(v) else np.nan
        row["low 12 M"] = v[i:i + 253].min() / v[i] - 1 if i + 252 < len(v) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def all_days(px: pd.Series) -> pd.DataFrame:
    v = px.to_numpy()
    out = {h: pd.Series(v).shift(-n).to_numpy() / v - 1 for h, n in HORIZONS.items()}
    return pd.DataFrame(out, index=px.index)


def boot_p(base: np.ndarray, n: int, observed: float, reps: int = 5000, seed: int = 86) -> float:
    base = base[np.isfinite(base)]
    if n < 1 or len(base) < n:
        return float("nan")
    rng = np.random.default_rng(seed)
    m = base[rng.integers(0, len(base), size=(reps, n))].mean(axis=1)
    c = m.mean()
    return float((np.abs(m - c) >= abs(observed - c)).mean())


def holm(p: dict) -> dict:
    items = sorted((v, k) for k, v in p.items() if np.isfinite(v))
    m, out, run = len(items), {}, 0.0
    for i, (v, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    return out


def build_events(gspc, vix=None, tnx=None, irx=None, us_rate=None) -> dict:
    ev = {}
    if vix is not None and len(vix):
        ev["VIX > 30 (first)"] = first_cross_above(vix, 30)
        ev["VIX > 40 (first)"] = first_cross_above(vix, 40)
    for dd in (0.10, 0.20, 0.30):
        ev[f"S&P −{int(dd*100)} % from high"] = drawdown_events(gspc, dd)
    if us_rate is not None and len(us_rate):
        ev["Fed first cut"] = policy_events(us_rate, -1)
        ev["Fed first hike"] = policy_events(us_rate, +1)
    if tnx is not None and irx is not None and len(tnx) and len(irx):
        sp = (tnx - irx).dropna()
        ev["Yield curve inverts"] = first_cross_below(sp, 0.0)
    ev["US election"] = us_elections()
    ev["Geopolitical shock (list)"] = [pd.Timestamp(d) for d in SHOCKS.values()]
    return ev


def run_experiment86_report(assets: dict, events: dict, btc: pd.Series = None) -> str:
    from datetime import datetime, timezone
    assets = {k: _clean(v) for k, v in assets.items() if v is not None and len(v) > 300}
    L = [f"# Experiment #86 — base rates after events ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("Price index returns from the event-day close. 'any day' = all trading days of the same asset "
             "(base rate). p = random-date bootstrap (two-sided, mean); Holm across all cells with ≥ 8 events.")
    L.append("Data: " + ", ".join(f"{k} {v.index[0]:%Y}–{v.index[-1]:%Y}" for k, v in assets.items()))
    L.append("")
    cells, pv = [], {}
    for an, px in assets.items():
        base = all_days(px)
        for en, dates in events.items():
            o = outcomes(px, [d for d in dates if d >= px.index[0]])
            if o.empty:
                continue
            for h in HORIZONS:
                x = o[h].dropna().to_numpy()
                if len(x) == 0:
                    continue
                key = (an, en, h)
                p = boot_p(base[h].to_numpy(), len(x), float(x.mean())) if len(x) >= 8 else float("nan")
                if np.isfinite(p):
                    pv[key] = p
                cells.append((key, x, o["low 12 M"].dropna().to_numpy()))
    adj = holm(pv)
    for an, px in assets.items():
        base = all_days(px)
        L.append(f"## {an}")
        L.append("| event | horizon | n | median | mean | positive | worst 10 % | any day: median / positive | p | Holm |")
        L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|")
        for h in HORIZONS:
            b = base[h].dropna()
            L.append(f"| *any day* | {h} | {len(b):,} | {100*b.median():+.1f} % | {100*b.mean():+.1f} % | "
                     f"{100*(b > 0).mean():.0f} % | {100*b.quantile(0.1):+.1f} % | | | |")
        for (a, en, h), x, lows in cells:
            if a != an:
                continue
            b = base[h].dropna()
            p, q = pv.get((a, en, h), float("nan")), adj.get((a, en, h), float("nan"))
            L.append(f"| {en} | {h} | {len(x)} | {100*np.median(x):+.1f} % | {100*x.mean():+.1f} % | "
                     f"{100*(x > 0).mean():.0f} % | {100*np.quantile(x, 0.1):+.1f} % | "
                     f"{100*b.median():+.1f} % / {100*(b > 0).mean():.0f} % | "
                     + (f"{p:.3f} | {q:.3f} |" if np.isfinite(p) else "— | — |"))
        L.append("")
        L.append("Interim low within 12 months after the event (median / worst):")
        seen = set()
        for (a, en, h), x, lows in cells:
            if a == an and en not in seen and len(lows):
                seen.add(en)
                L.append(f"- {en}: median {100*np.median(lows):+.1f} %, worst {100*lows.min():+.1f} % (n {len(lows)})")
        L.append("")
    if btc is not None and len(btc) > 300:
        b = _clean(btc)
        o = outcomes(b, HALVINGS)
        L.append("## Bitcoin halvings (descriptive only — 3 cases)")
        for _, r in o.iterrows():
            L.append(f"- {r['date']:%Y-%m-%d}: " + ", ".join(
                f"{h} {100*r[h]:+.0f} %" for h in HORIZONS if np.isfinite(r[h])))
        L.append("")
    sig = [k for k, v in adj.items() if v < 0.05]
    L.append(f"Cells tested: {len(pv)}; significant after Holm (< 0.05): {len(sig)}"
             + (" — " + "; ".join(f"{a} / {e} / {h}" for a, e, h in sig) if sig else "") + ".")
    L.append("Events cluster in time (e.g. several crises in 2008), so the effective sample is smaller "
             "than n; the bootstrap treats events as independent and is therefore optimistic.")
    return "\n".join(L)
