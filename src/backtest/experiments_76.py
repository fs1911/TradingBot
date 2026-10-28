"""
Experiment #76 — insider SALES as a warning sign (the mirror image of #48).

SEC insider transactions data sets (Form 4, 2006 →), open-market sales (code S,
disposition D), price ≥ $5, single sales ≥ $100k (smaller ones are mostly routine).
Pre-registered events (public date = filing date, as in #48):
  A cluster sale   ≥ 3 different insiders sell within 30 days, together ≥ $1m
  B very large sale  one sale ≥ $10m
Outcome: return minus SPY after 1 / 3 / 6 / 12 months, vs CONTROL dates of the same stocks
(random filing-free dates, seeded), and a calendar-time portfolio (6 months) with t-stat.
Caveat: many sales are pre-planned (10b5-1 plans, taxes, diversification) — that is
exactly why the literature finds sales far less informative than purchases.
Pure, injected for CI.
"""
from __future__ import annotations
import io
import zipfile
import numpy as np
import pandas as pd

from .experiments_48 import SEC_URL, HORIZONS, _read_tsv, event_returns, calendar_portfolio


def parse_sales_zip(raw: bytes, min_value: float = 100_000) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        sub = _read_tsv(z, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL"])
        tr = _read_tsv(z, "NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE", "TRANS_SHARES",
                                                 "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"])
        own = _read_tsv(z, "REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK"])
    if sub.empty or tr.empty:
        return pd.DataFrame()
    tr = tr[tr["TRANS_CODE"].str.strip() == "S"]
    if "TRANS_ACQUIRED_DISP_CD" in tr:
        tr = tr[tr["TRANS_ACQUIRED_DISP_CD"].fillna("D").str.strip() == "D"]
    tr = tr.assign(shares=pd.to_numeric(tr["TRANS_SHARES"], errors="coerce"),
                   price=pd.to_numeric(tr["TRANS_PRICEPERSHARE"], errors="coerce")).dropna(subset=["shares", "price"])
    tr = tr[(tr["shares"] > 0) & (tr["price"] >= 5)]
    tr = tr[tr["shares"] * tr["price"] >= min_value]
    if tr.empty:
        return pd.DataFrame()
    df = tr.merge(sub, on="ACCESSION_NUMBER")
    df = df.merge(own.drop_duplicates("ACCESSION_NUMBER"), on="ACCESSION_NUMBER", how="left") if not own.empty \
        else df.assign(RPTOWNERCIK=df["ACCESSION_NUMBER"])
    for src, dst in (("FILING_DATE", "filing_date"), ("TRANS_DATE", "trans_date")):
        d = pd.to_datetime(df[src], format="%d-%b-%Y", errors="coerce")
        miss = d.isna() & df[src].notna()
        if miss.any():
            d[miss] = pd.to_datetime(df.loc[miss, src], format="mixed", errors="coerce")
        df[dst] = d
    out = pd.DataFrame({"ticker": df["ISSUERTRADINGSYMBOL"].fillna("").str.strip().str.upper(),
                        "filing_date": df["filing_date"], "trans_date": df["trans_date"],
                        "owner": df["RPTOWNERCIK"].fillna(df["ACCESSION_NUMBER"]),
                        "value": df["shares"] * df["price"]})
    return out[(out["ticker"].str.len().between(1, 6)) & out["filing_date"].notna()].reset_index(drop=True)


def fetch_sales(years: range, ua: str, timeout: int = 90, log=None) -> tuple:
    import time as _t
    import urllib.request
    parts, fails = [], []
    for y in years:
        for q in (1, 2, 3, 4):
            try:
                req = urllib.request.Request(SEC_URL.format(y=y, q=q), headers={"User-Agent": ua, "Accept-Encoding": "identity"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    parts.append(parse_sales_zip(r.read()))
                if log:
                    log(f"#76 {y}q{q}: {len(parts[-1])} sales")
            except Exception as e:
                fails.append(f"{y}q{q}: {repr(e)[:60]}")
            _t.sleep(0.3)
    return (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()), fails


def sale_events(s: pd.DataFrame) -> dict:
    if s.empty:
        return {"A cluster sale": pd.DataFrame(columns=["ticker", "date"]),
                "B very large sale": pd.DataFrame(columns=["ticker", "date"])}
    s = s.copy()
    s["tdate"] = s["trans_date"].fillna(s["filing_date"])
    cl = []
    for t, g in s.sort_values("tdate").groupby("ticker"):
        tdates, owners, vals, fdates = (g["tdate"].to_numpy(), g["owner"].to_numpy(), g["value"].to_numpy(),
                                        g["filing_date"].to_numpy())
        last, j = None, 0
        for i in range(len(g)):
            while j < len(g) and tdates[j] <= tdates[i] + np.timedelta64(30, "D"):
                j += 1
            win_o = owners[i:j]
            if len(set(win_o)) >= 3 and vals[i:j].sum() >= 1_000_000:
                seen, date = [], None
                for o, fd in sorted(zip(win_o, fdates[i:j]), key=lambda x: x[1]):
                    if o not in seen:
                        seen.append(o)
                        if len(seen) == 3:
                            date = pd.Timestamp(fd)
                            break
                if date is not None and (last is None or date > last + pd.Timedelta(days=90)):
                    cl.append((t, date)); last = date
    big = s[s["value"] >= 10_000_000].sort_values(["ticker", "filing_date"])
    keep, lastd = [], {}
    for t, d in zip(big["ticker"], big["filing_date"]):
        if t not in lastd or d > lastd[t] + pd.Timedelta(days=90):
            keep.append((t, d)); lastd[t] = d
    return {"A cluster sale": pd.DataFrame(cl, columns=["ticker", "date"]),
            "B very large sale": pd.DataFrame(keep, columns=["ticker", "date"])}


def controls(events: pd.DataFrame, prices: dict, seed: int = 76) -> pd.DataFrame:
    """One random control date per event: same stock, ≥ 180 days away from any event of it."""
    rng = np.random.default_rng(seed)
    rows = []
    ev_by = events.groupby("ticker")["date"].apply(list).to_dict()
    for t, d in zip(events["ticker"], events["date"]):
        px = prices.get(t)
        if px is None or len(px) < 600:
            continue
        idx = px.index[(px.index < px.index[-260])]
        if len(idx) == 0:
            continue
        for _ in range(20):
            c = idx[rng.integers(0, len(idx))]
            if all(abs((c - e).days) > 180 for e in ev_by[t]):
                rows.append((t, c)); break
    return pd.DataFrame(rows, columns=["ticker", "date"])


def run_experiment76_report(sales: pd.DataFrame, fails: list, prices: dict, spy: pd.Series, n_trials: int = 320) -> str:
    from datetime import datetime, timezone
    from .experiments_49 import mstat
    L = [f"# Experiment #76 — insider sales as a warning sign ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"Open-market sales ≥ $100k: {len(sales):,} (quarters failed: {len(fails)}). Prices for {len(prices):,} tickers.")
    ev = sale_events(sales)
    L.append("")
    L.append("| event | events (priced) | " + " | ".join(f"{h} vs SPY" for h in HORIZONS) + " | " +
             " | ".join(f"{h} vs control" for h in HORIZONS) + " |")
    L.append("|---|--:|" + "--:|" * (2 * len(HORIZONS)))
    for name, e in ev.items():
        e = e[e["ticker"].isin(prices.keys())]
        res = [event_returns(prices[t], spy, d) for t, d in zip(e["ticker"], e["date"])]
        res = pd.DataFrame([r for r in res if r])
        c = controls(e, prices)
        cres = pd.DataFrame([r for r in (event_returns(prices[t], spy, d) for t, d in zip(c["ticker"], c["date"])) if r])
        cells = [f"{100*res[h].mean():+.1f} %" if h in res else "—" for h in HORIZONS]
        diff = []
        for h in HORIZONS:
            if h in res and h in cres and len(res[h].dropna()) > 30 and len(cres[h].dropna()) > 30:
                a, b = res[h].dropna(), cres[h].dropna()
                se = (a.var() / len(a) + b.var() / len(b)) ** 0.5
                diff.append(f"{100*(a.mean()-b.mean()):+.1f} % (t {(a.mean()-b.mean())/se:+.1f})")
            else:
                diff.append("—")
        L.append(f"| {name} | {len(e):,} ({len(res):,}) | " + " | ".join(cells) + " | " + " | ".join(diff) + " |")
        cp = calendar_portfolio(e, prices, spy, hold_months=6)
        st = mstat(cp)
        L.append(f"| … calendar portfolio 6 M | {len(cp)} months | {100*st['ann']:+.1f} %/yr vs SPY (t {st['t']:+.2f}) | | | | | | | |")
    L.append("")
    L.append(f"Bonferroni α/{n_trials}. Negative = the stocks did worse after insiders sold. Survivorship: delisted "
             f"stocks have no Yahoo prices (biases AGAINST finding a warning effect).")
    return "\n".join(L)
