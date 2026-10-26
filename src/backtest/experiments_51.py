"""
Experiment #51 — "smart money": copying Berkshire Hathaway and well-known hedge funds
from their quarterly 13F filings.

Institutional managers (> $100m) must disclose their US long positions within 45 days
after each quarter (SEC Form 13F). Popular idea: copy the best investors. Literature:
copying Berkshire worked historically even with the delay (Martin & Puthenpurackal 2008);
hedge funds' highest-conviction "best ideas" outperformed (Cohen, Polk & Silli 2010);
13F-copy ETFs have mostly disappointed.

Data: SEC Form 13F data sets (quarterly zips, 2013→), managers selected by name
(pre-registered list), CUSIP → ticker via OpenFIGI, prices from Yahoo.
Point-in-time: a filing is used from the month AFTER its filing date. Monthly rebalance
to each manager's latest filing (max 6 months old). Options (PUT/CALL rows) excluded.

Portfolios (vs SPY):
  A Berkshire clone — Berkshire's positions, weighted by reported value
  B Best ideas      — each listed fund's top 3 positions by value, equal-weight union
  C Consensus       — stocks held by ≥ 3 listed funds, equal-weight
  D All holdings    — union of all listed funds' positions, equal-weight (control)
Pure, injected for CI.
"""
from __future__ import annotations
import io
import math
import re
import zipfile
import numpy as np
import pandas as pd

LISTING = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
MANAGERS = {  # pre-registered: well-known fundamental / "smart money" managers (name substrings)
    "Berkshire Hathaway": "BERKSHIRE HATHAWAY INC",
    "Appaloosa": "APPALOOSA", "Baupost": "BAUPOST", "Pershing Square": "PERSHING SQUARE",
    "Third Point": "THIRD POINT", "Greenlight": "GREENLIGHT CAPITAL", "Lone Pine": "LONE PINE",
    "Viking Global": "VIKING GLOBAL", "Tiger Global": "TIGER GLOBAL", "Coatue": "COATUE",
    "Maverick": "MAVERICK CAPITAL", "Duquesne": "DUQUESNE FAMILY", "Himalaya": "HIMALAYA CAPITAL",
    "Akre": "AKRE CAPITAL", "Fundsmith": "FUNDSMITH", "Gardner Russo": "GARDNER RUSSO",
    "Elliott": "ELLIOTT INVESTMENT", "Soros": "SOROS FUND", "Icahn": "ICAHN", "Glenview": "GLENVIEW CAPITAL",
}


def list_13f_zips(html: str, base: str = "https://www.sec.gov") -> list:
    from urllib.parse import urljoin
    links = sorted(set(re.findall(r'href="([^"]*form13f[^"]*\.zip)"', html, flags=re.I)))
    return [urljoin(base, l) for l in links]


def _read(z: zipfile.ZipFile, name: str, usecols: list, chunksize=None):
    member = next((n for n in z.namelist() if n.upper().endswith(name.upper())), None)
    if member is None:
        return None
    return pd.read_csv(z.open(member), sep="\t", dtype=str, quoting=3, on_bad_lines="skip",
                       usecols=lambda c: c.upper() in usecols, chunksize=chunksize, low_memory=False)


def _date(s: pd.Series) -> pd.Series:
    d = pd.to_datetime(s, format="%d-%b-%Y", errors="coerce")
    miss = d.isna() & s.notna()
    if miss.any():
        d[miss] = pd.to_datetime(s[miss], format="mixed", errors="coerce")
    return d


def parse_13f_zip(fileobj, managers: dict = MANAGERS) -> pd.DataFrame:
    """One 13F data-set zip → holdings of the selected managers:
    [manager, period, filed, cusip, issuer, value]."""
    with zipfile.ZipFile(fileobj) as z:
        sub = _read(z, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "PERIODOFREPORT"])
        cov = _read(z, "COVERPAGE.tsv", ["ACCESSION_NUMBER", "FILINGMANAGER_NAME", "ISAMENDMENT"])
        if sub is None or cov is None:
            return pd.DataFrame()
        sub.columns, cov.columns = [c.upper() for c in sub.columns], [c.upper() for c in cov.columns]
        sub = sub[sub["SUBMISSIONTYPE"].str.strip().str.upper() == "13F-HR"]
        cov = cov[cov.get("ISAMENDMENT", pd.Series("N", index=cov.index)).fillna("N").str.upper().str[0] != "Y"]
        names = cov["FILINGMANAGER_NAME"].fillna("").str.upper()
        pick = {}
        for label, sub_str in managers.items():
            for acc in cov.loc[names.str.contains(re.escape(sub_str)), "ACCESSION_NUMBER"]:
                pick[acc] = label
        meta = sub[sub["ACCESSION_NUMBER"].isin(pick)]
        if meta.empty:
            return pd.DataFrame()
        parts = []
        reader = _read(z, "INFOTABLE.tsv", ["ACCESSION_NUMBER", "NAMEOFISSUER", "CUSIP", "VALUE", "PUTCALL"],
                       chunksize=400_000)
        if reader is None:
            return pd.DataFrame()
        accs = set(meta["ACCESSION_NUMBER"])
        for ch in reader:
            ch.columns = [c.upper() for c in ch.columns]
            ch = ch[ch["ACCESSION_NUMBER"].isin(accs)]
            if "PUTCALL" in ch:
                ch = ch[ch["PUTCALL"].isna() | (ch["PUTCALL"].str.strip() == "")]
            if len(ch):
                parts.append(ch[["ACCESSION_NUMBER", "NAMEOFISSUER", "CUSIP", "VALUE"]])
    if not parts:
        return pd.DataFrame()
    h = pd.concat(parts)
    h["VALUE"] = pd.to_numeric(h["VALUE"], errors="coerce")
    h = h.dropna(subset=["VALUE"])
    h = h.groupby(["ACCESSION_NUMBER", "CUSIP"], as_index=False).agg(value=("VALUE", "sum"),
                                                                    issuer=("NAMEOFISSUER", "first"))
    meta = meta.assign(filed=_date(meta["FILING_DATE"]), period=_date(meta["PERIODOFREPORT"]),
                       manager=meta["ACCESSION_NUMBER"].map(pick))
    out = h.merge(meta[["ACCESSION_NUMBER", "manager", "filed", "period"]], on="ACCESSION_NUMBER")
    out["cusip"] = out["CUSIP"].str.strip().str.upper()
    return out[["manager", "period", "filed", "cusip", "issuer", "value", "ACCESSION_NUMBER"]]


def fetch_holdings(ua: str, timeout: int = 120, log=None) -> tuple:
    """Download every 13F data-set zip (to a temp file each) → (holdings, n_zips, failures)."""
    import tempfile
    import urllib.request
    req = urllib.request.Request(LISTING, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=60) as r:
        zips = list_13f_zips(r.read().decode("utf-8", "replace"))
    parts, fails = [], []
    for url in zips:
        try:
            with tempfile.TemporaryFile() as tmp:
                rq = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
                with urllib.request.urlopen(rq, timeout=timeout) as r:
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            break
                        tmp.write(b)
                tmp.seek(0)
                p = parse_13f_zip(tmp)
            parts.append(p)
            if log:
                log(f"13F {url.rsplit('/', 1)[-1]}: {len(p)} rows")
        except Exception as e:
            fails.append(f"{url.rsplit('/', 1)[-1]}: {repr(e)[:80]}")
    h = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(h):   # the same filing can appear in two overlapping data sets
        h = h.drop_duplicates(["ACCESSION_NUMBER", "cusip"])
    return h, len(zips), fails


def map_cusips(cusips: list, timeout: int = 30, log=None) -> dict:
    """CUSIP → US ticker via OpenFIGI (no key: 10 per request, ~25 requests/minute)."""
    import json
    import time as _t
    import urllib.request
    out = {}
    for i in range(0, len(cusips), 10):
        batch = cusips[i:i + 10]
        body = json.dumps([{"idType": "ID_CUSIP", "idValue": c} for c in batch]).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request("https://api.openfigi.com/v3/mapping", data=body,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    res = json.loads(r.read().decode("utf-8"))
                for c, item in zip(batch, res):
                    data = item.get("data") or []
                    us = [d for d in data if d.get("exchCode") == "US" and d.get("ticker")]
                    pick = (us or [d for d in data if d.get("ticker")] or [None])[0]
                    if pick:
                        out[c] = str(pick["ticker"]).upper()
                break
            except Exception:
                _t.sleep(10 * (attempt + 1))
        _t.sleep(2.6)
        if log and i % 500 == 0:
            log(f"OpenFIGI {i}/{len(cusips)}")
    return out


def build_portfolios(h: pd.DataFrame, months: pd.PeriodIndex, max_age_months: int = 6) -> dict:
    """{portfolio name: {formation month: weights Series(ticker)}}; filings used from the
    month after their filing date; each manager's latest qualifying filing."""
    out = {k: {} for k in ("A Berkshire clone", "B Best ideas (top 3 each)", "C Consensus (≥3 funds)",
                           "D All holdings (EW)")}
    if h.empty:
        return out
    h = h.dropna(subset=["ticker"])
    filings = h.groupby(["manager", "ACCESSION_NUMBER"]).agg(filed=("filed", "first")).reset_index()
    filings["avail"] = filings["filed"].dt.to_period("M") + 1
    for m in months:
        live = filings[(filings["avail"] <= m) & (filings["avail"] > m - max_age_months)]
        latest = live.sort_values("filed").groupby("manager").tail(1)
        if latest.empty:
            continue
        cur = h[h["ACCESSION_NUMBER"].isin(latest["ACCESSION_NUMBER"])]
        pos = cur.groupby(["manager", "ticker"])["value"].sum().reset_index()
        bh = pos[pos["manager"] == "Berkshire Hathaway"]
        if len(bh):
            w = bh.set_index("ticker")["value"]
            out["A Berkshire clone"][m] = w / w.sum()
        hf = pos[pos["manager"] != "Berkshire Hathaway"]
        if len(hf):
            top = hf.sort_values("value", ascending=False).groupby("manager").head(3)["ticker"].unique()
            out["B Best ideas (top 3 each)"][m] = pd.Series(1.0 / len(top), index=top)
            cnt = hf.groupby("ticker")["manager"].nunique()
            cons = cnt[cnt >= 3].index
            if len(cons):
                out["C Consensus (≥3 funds)"][m] = pd.Series(1.0 / len(cons), index=cons)
            allt = hf["ticker"].unique()
            out["D All holdings (EW)"][m] = pd.Series(1.0 / len(allt), index=allt)
    return out


def run_portfolio(sel: dict, rets: pd.DataFrame) -> pd.Series:
    """Weights decided for month m (from filings available by then) earn month m's return."""
    out = {}
    for m, w in sel.items():
        if m not in rets.index:
            continue
        r = rets.loc[m].reindex(w.index)
        ok = r.notna()
        if ok.sum():
            out[m] = float((r[ok] * w[ok]).sum() / w[ok].sum())
    return pd.Series(out, dtype=float).sort_index()


def _ms(x: pd.Series) -> dict:
    x = x.dropna()
    if len(x) < 24 or x.std() == 0:
        return {"ann": float("nan"), "t": float("nan"), "sh": float("nan")}
    return {"ann": float(x.mean() * 12), "t": float(x.mean() / x.std() * math.sqrt(len(x))),
            "sh": float(x.mean() / x.std() * math.sqrt(12))}


def run_experiment51_report(h: pd.DataFrame, n_zips: int, fails: list, prices: dict, spy: pd.Series,
                            n_trials: int = 255) -> str:
    from datetime import datetime, timezone
    from .experiments_49 import monthly_returns, perf
    L = [f"# Experiment #51 — smart money: copying Berkshire and well-known hedge funds (13F) "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"13F data sets: {n_zips}, failed {len(fails)}" + (f" (e.g. {fails[0]})" if fails else "") + ".")
    if h is None or h.empty:
        return "\n".join(L + ["", "No holdings parsed."])
    found = h.groupby("manager")["ACCESSION_NUMBER"].nunique().sort_values(ascending=False)
    L.append("Managers found (filings): " + ", ".join(f"{k} {v}" for k, v in found.items()) + ".")
    mapped = h["ticker"].notna().mean() if "ticker" in h else 0
    L.append(f"Positions mapped to a ticker: {100*mapped:.0f}%; with Yahoo prices: {len(prices):,} tickers.")
    px, rets = monthly_returns(prices)
    spy_m = monthly_returns({"SPY": spy})[1]["SPY"] if spy is not None and len(spy) else None
    months = rets.index[rets.index >= pd.Period("2013-09", "M")]
    ports = build_portfolios(h, months)
    L.append("")
    L.append("| Portfolio | months | CAGR | max DD | Sharpe | vs SPY p.a. (t) | ≤2019 vs SPY | >2019 vs SPY | avg # stocks |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    crit = 0.05 / n_trials
    rows = {}
    for name, sel in ports.items():
        r = run_portfolio(sel, rets)
        if len(r) < 24:
            L.append(f"| {name} | {len(r)} | — | — | — | — | — | — | — |")
            continue
        rows[name] = r
        pf, ms = perf(r), _ms(r)
        ex = (r - spy_m.reindex(r.index)).dropna() if spy_m is not None else pd.Series(dtype=float)
        e, pre, post = _ms(ex), _ms(ex[ex.index <= pd.Period("2019-12", "M")]), _ms(ex[ex.index > pd.Period("2019-12", "M")])
        n = np.mean([len(w) for w in sel.values()]) if sel else 0
        L.append(f"| {name} | {len(r)} | {100*pf['cagr']:+.1f}% | {100*pf['maxdd']:.0f}% | {ms['sh']:.2f} | "
                 f"{100*e['ann']:+.1f}% ({e['t']:.2f}) | {100*pre['ann']:+.1f}% ({pre['t']:.1f}) | "
                 f"{100*post['ann']:+.1f}% ({post['t']:.1f}) | {n:.0f} |")
    if spy_m is not None:
        s = spy_m.reindex(months).dropna()
        pf, ms = perf(s), _ms(s)
        L.append(f"| SPY | {len(s)} | {100*pf['cagr']:+.1f}% | {100*pf['maxdd']:.0f}% | {ms['sh']:.2f} | — | — | — | 500 |")
    L.append("")
    if "B Best ideas (top 3 each)" in rows and "D All holdings (EW)" in rows:
        d = (rows["B Best ideas (top 3 each)"] - rows["D All holdings (EW)"]).dropna()
        e = _ms(d)
        L.append(f"Best ideas − all holdings of the same funds: {100*e['ann']:+.1f}% p.a. (t {e['t']:.2f}) — does "
                 f"conviction add anything beyond the funds' general taste?")
    L.append(f"Bonferroni α/{n_trials} → |t| ≳ 3.6 needed. 13F shows long US positions only, with up to "
             f"~4.5 months delay; shorts, hedges and non-US positions are invisible.")
    return "\n".join(L)
