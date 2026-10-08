"""
Experiment #48 — insider purchases as a buy signal for single stocks.

Literature (Lakonishok & Lee 2001; Cohen, Malloy & Pomorski 2012; Alldredge & Blank
2019): open-market PURCHASES by company insiders, especially several insiders at once,
are followed by above-market returns. Data: SEC "Insider Transactions Data Sets"
(Form 3/4/5, quarterly since 2006), free.

Pre-registered signals (event date = FILING date that makes the signal public):
  A Cluster buy: ≥3 distinct insiders buy on the open market (code P) within 30
    calendar days, together ≥ $100k, price ≥ $5
  B Large buy:   a single insider purchase ≥ $500k, price ≥ $5
Measured: market-adjusted returns (stock − SPY) 1/3/6/12 months after the first close
after the event; vs CONTROL dates (random dates of the same stocks); calendar-time
portfolio (each month hold all stocks with an event in the previous 6 months,
equal-weight, minus SPY) → mean, t-stat, Sharpe, before/after 2016; hit rate.
Caveat: tickers that no longer trade are usually missing on Yahoo (survivorship →
results biased UPWARD); coverage is reported.
Pure, injected for CI.
"""
from __future__ import annotations
import io
import math
import zipfile
import numpy as np
import pandas as pd

SEC_URL = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{y}q{q}_form345.zip"
HORIZONS = {"1M": 21, "3M": 63, "6M": 126, "12M": 252}


def _read_tsv(z: zipfile.ZipFile, name: str, usecols: list) -> pd.DataFrame:
    member = next((n for n in z.namelist() if n.upper().endswith(name.upper())), None)
    if member is None:
        return pd.DataFrame()
    with z.open(member) as f:
        df = pd.read_csv(f, sep="\t", dtype=str, quoting=3, on_bad_lines="skip",
                         usecols=lambda c: c.upper() in usecols, low_memory=False)
    df.columns = [c.upper() for c in df.columns]
    return df


def parse_quarter_zip(raw: bytes) -> pd.DataFrame:
    """One SEC quarterly zip → open-market purchases:
    [ticker, filing_date, trans_date, owner, value, price]."""
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        sub = _read_tsv(z, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL",
                                              "DOCUMENT_TYPE"])
        tr = _read_tsv(z, "NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE",
                                                 "TRANS_SHARES", "TRANS_PRICEPERSHARE",
                                                 "TRANS_ACQUIRED_DISP_CD"])
        own = _read_tsv(z, "REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK"])
    if sub.empty or tr.empty:
        return pd.DataFrame()
    tr = tr[(tr["TRANS_CODE"].str.strip() == "P")]
    if "TRANS_ACQUIRED_DISP_CD" in tr:
        tr = tr[tr["TRANS_ACQUIRED_DISP_CD"].fillna("A").str.strip() == "A"]
    tr = tr.assign(shares=pd.to_numeric(tr["TRANS_SHARES"], errors="coerce"),
                   price=pd.to_numeric(tr["TRANS_PRICEPERSHARE"], errors="coerce"))
    tr = tr.dropna(subset=["shares", "price"])
    tr = tr[(tr["shares"] > 0) & (tr["price"] > 0)]
    if tr.empty:
        return pd.DataFrame()
    df = tr.merge(sub, on="ACCESSION_NUMBER", how="inner")
    if not own.empty:
        own1 = own.drop_duplicates("ACCESSION_NUMBER")
        df = df.merge(own1, on="ACCESSION_NUMBER", how="left")
    else:
        df["RPTOWNERCIK"] = df["ACCESSION_NUMBER"]
    for src, dst in (("FILING_DATE", "filing_date"), ("TRANS_DATE", "trans_date")):
        d = pd.to_datetime(df[src], format="%d-%b-%Y", errors="coerce")
        miss = d.isna() & df[src].notna()
        if miss.any():   # other formats only where the SEC format did not parse
            d[miss] = pd.to_datetime(df.loc[miss, src], format="mixed", errors="coerce")
        df[dst] = d
    out = pd.DataFrame({
        "ticker": df["ISSUERTRADINGSYMBOL"].fillna("").str.strip().str.upper(),
        "filing_date": df["filing_date"], "trans_date": df["trans_date"],
        "owner": df["RPTOWNERCIK"].fillna(df["ACCESSION_NUMBER"]),
        "value": df["shares"] * df["price"], "price": df["price"]})
    out = out[(out["ticker"].str.len() > 0) & (out["ticker"].str.len() <= 6) &
              (~out["ticker"].isin(["NONE", "N/A", "NA"])) & out["filing_date"].notna()]
    return out.reset_index(drop=True)


def fetch_purchases(years: range, user_agent: str, timeout: int = 60, log=None) -> tuple:
    """Download all quarterly zips; returns (purchases DataFrame, list of failures)."""
    import urllib.request
    import time as _t
    parts, fails = [], []
    for y in years:
        for q in (1, 2, 3, 4):
            url = SEC_URL.format(y=y, q=q)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": user_agent,
                                                           "Accept-Encoding": "identity"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    raw = r.read()
                p = parse_quarter_zip(raw)
                parts.append(p)
                if log:
                    log(f"SEC {y}q{q}: {len(p)} purchases")
            except Exception as e:
                fails.append(f"{y}q{q}: {repr(e)[:80]}")
            _t.sleep(0.3)   # well below SEC's 10 requests/second
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    return df, fails


def signals(purch: pd.DataFrame, min_price: float = 5.0) -> dict:
    """{'A cluster': DataFrame[ticker, date], 'B large': ...}; date = public date."""
    if purch.empty:
        return {"A cluster": pd.DataFrame(columns=["ticker", "date"]),
                "B large": pd.DataFrame(columns=["ticker", "date"])}
    p = purch[purch["price"] >= min_price].copy()
    p["tdate"] = p["trans_date"].fillna(p["filing_date"])
    big = p[p["value"] >= 500_000].groupby(["ticker", "filing_date"]).size().reset_index()[["ticker", "filing_date"]]
    big = big.rename(columns={"filing_date": "date"})
    clusters = []
    for t, g in p.sort_values("tdate").groupby("ticker"):
        g = g.reset_index(drop=True)
        last_event = None
        for i in range(len(g)):
            start = g.loc[i, "tdate"]
            win = g[(g["tdate"] >= start) & (g["tdate"] <= start + pd.Timedelta(days=30))]
            if win["owner"].nunique() >= 3 and win["value"].sum() >= 100_000:
                # public when the filing of the 3rd distinct insider is out
                firsts = win.drop_duplicates("owner").sort_values("filing_date")
                date = firsts["filing_date"].iloc[2]
                if last_event is None or date > last_event + pd.Timedelta(days=90):
                    clusters.append((t, date))
                    last_event = date
    cl = pd.DataFrame(clusters, columns=["ticker", "date"])
    # one large-buy event per ticker per 90 days
    big = big.sort_values(["ticker", "date"])
    keep, last = [], {}
    for t, d in zip(big["ticker"], big["date"]):
        if t not in last or d > last[t] + pd.Timedelta(days=90):
            keep.append((t, d))
            last[t] = d
    return {"A cluster": cl, "B large": pd.DataFrame(keep, columns=["ticker", "date"])}


def event_returns(px: pd.Series, spy: pd.Series, date: pd.Timestamp) -> dict | None:
    """Market-adjusted returns from the first close after `date`."""
    px = px.dropna()
    after = px.index[px.index > date]
    if len(after) < 22:
        return None
    i0 = px.index.get_loc(after[0])
    out = {}
    for k, h in HORIZONS.items():
        if i0 + h >= len(px):
            continue
        d0, d1 = px.index[i0], px.index[i0 + h]
        r = px.iloc[i0 + h] / px.iloc[i0] - 1
        s0, s1 = spy.asof(d0), spy.asof(d1)
        if not (np.isfinite(s0) and np.isfinite(s1)) or s0 <= 0:
            continue
        out[k] = r - (s1 / s0 - 1)
    return out or None


def calendar_portfolio(events: pd.DataFrame, prices: dict, spy: pd.Series, hold_months: int = 6) -> pd.Series:
    """Monthly excess return (EW over stocks with an event in the last `hold_months`
    months, minus SPY)."""
    if events.empty:
        return pd.Series(dtype=float)
    mret = {}
    for t, s in prices.items():
        if s is not None and len(s):
            m = s.groupby(s.index.to_period("M")).last()
            mret[t] = m.pct_change()
    spm = spy.groupby(spy.index.to_period("M")).last().pct_change()
    ev = events.assign(per=events["date"].dt.to_period("M"))
    months = pd.period_range(ev["per"].min() + 1, spm.index.max(), freq="M")
    out = {}
    for m in months:
        live = ev[(ev["per"] < m) & (ev["per"] >= m - hold_months)]["ticker"].unique()
        rs = [mret[t].get(m) for t in live if t in mret]
        rs = [r for r in rs if r is not None and np.isfinite(r)]
        if rs and m in spm.index and np.isfinite(spm.get(m, np.nan)):
            out[m] = float(np.mean(rs)) - float(spm[m])
    return pd.Series(out, dtype=float)


def _t(x: pd.Series) -> tuple:
    x = x.dropna()
    if len(x) < 24 or x.std() == 0:
        return float("nan"), float("nan"), float("nan")
    return float(x.mean() * 12), float(x.mean() / x.std() * math.sqrt(len(x))), float(x.mean() / x.std() * math.sqrt(12))


def run_experiment48_report(purch: pd.DataFrame, fails: list, prices: dict, spy: pd.Series,
                            n_trials: int = 224, n_controls: int = 5, seed: int = 48) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #48 — insider purchases as a buy signal "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"SEC purchases parsed: {len(purch):,}" +
             (f" ({purch['filing_date'].min():%Y-%m} → {purch['filing_date'].max():%Y-%m})" if len(purch) else "") +
             f"; quarters failed: {len(fails)}" + (f" (e.g. {fails[0]})" if fails else "") + ".")
    if purch.empty:
        return "\n".join(L + ["", "No data — SEC download failed."])
    sig = signals(purch)
    crit = 0.05 / n_trials
    rng = np.random.default_rng(seed)
    for name, ev in sig.items():
        L.append("")
        L.append(f"## Signal {name}")
        cov = ev[ev["ticker"].isin([t for t, s in prices.items() if s is not None and len(s) > 300])]
        L.append(f"Events: {len(ev):,}; with price data: {len(cov):,} ({100*len(cov)/max(len(ev),1):.0f}% — "
                 f"missing tickers are mostly delisted → survivorship bias upward).")
        rows, ctrl = [], []
        for t, d in zip(cov["ticker"], cov["date"]):
            px = prices[t]
            r = event_returns(px, spy, d)
            if r:
                rows.append({"date": d, **r})
            idx = px.index[(px.index > px.index[0] + pd.Timedelta(days=30)) &
                           (px.index < px.index[-1] - pd.Timedelta(days=380))]
            if len(idx):
                for cd in rng.choice(idx, size=min(n_controls, len(idx)), replace=False):
                    c = event_returns(px, spy, pd.Timestamp(cd))
                    if c:
                        ctrl.append(c)
        if not rows:
            L.append("No usable events.")
            continue
        er, cr = pd.DataFrame(rows), pd.DataFrame(ctrl)
        L.append("")
        L.append("| Horizon | n | mean excess vs SPY | median | hit rate (>SPY) | control mean (same stocks, random dates) | "
                 "event − control [95% CI] |")
        L.append("|---|--:|--:|--:|--:|--:|--:|")
        for k in HORIZONS:
            if k not in er:
                continue
            e = er[k].dropna().clip(-1, 3)
            c = cr[k].dropna().clip(-1, 3) if k in cr else pd.Series(dtype=float)
            boots = [rng.choice(e.to_numpy(), len(e)).mean() - (rng.choice(c.to_numpy(), len(c)).mean() if len(c) else 0)
                     for _ in range(1000)]
            L.append(f"| {k} | {len(e):,} | {100*e.mean():+.2f}% | {100*e.median():+.2f}% | {100*(e > 0).mean():.0f}% | "
                     f"{100*c.mean():+.2f}% | {100*(e.mean()-c.mean()):+.2f}% "
                     f"[{100*np.percentile(boots, 2.5):+.2f}, {100*np.percentile(boots, 97.5):+.2f}] |")
        cp = calendar_portfolio(cov, prices, spy, 6)
        m, t, sh = _t(cp)
        pre, post = _t(cp[cp.index <= pd.Period("2015-12", "M")]), _t(cp[cp.index > pd.Period("2015-12", "M")])
        p = math.erfc(abs(t) / math.sqrt(2)) / 2 if np.isfinite(t) else float("nan")
        L.append("")
        L.append(f"Calendar-time portfolio (hold 6 months, EW, minus SPY): {100*m:+.1f}% p.a., t={t:.2f}, "
                 f"Sharpe {sh:.2f}, one-sided p={p:.5f} {'✅' if p < crit and m > 0 else '❌'} (α/{n_trials}); "
                 f"≤2015 {100*pre[0]:+.1f}% (t {pre[1]:.1f}), >2015 {100*post[0]:+.1f}% (t {post[1]:.1f}); "
                 f"months {len(cp)}.")
    return "\n".join(L)
