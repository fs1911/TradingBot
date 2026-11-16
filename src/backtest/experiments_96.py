"""
Experiment #96 — ALL big 13F filers, not 20 hand-picked ones: do the stocks that many managers
newly buy beat the stocks they sell? (requested 16.11.2026; #51 tested 20 famous managers → no edge.)
Literature: Chen, Hong & Stein (2002) "Breadth of ownership and stock returns" — a rise in the
number of institutions holding a stock predicted higher returns (1979–1998).

Pre-registered:
  Data     every SEC 13F data set (2013 →), original 13F-HR only (no amendments), options excluded,
           filings counted only if filed ≤ 50 days after quarter end (no late-filer look-ahead).
           Value in $1000 before 2023 filings, in $ after (SEC change of 3 Jan 2023).
  Managers A 'hedge-fund proxy': total ≥ $1bn and ≤ 150 positions (concentrated portfolios; index
           funds, banks and pensions hold thousands). B all filers ≥ $1bn (secondary).
           Only managers that filed in BOTH quarters count for changes.
  Signals  per stock and quarter: Δbreadth = (holders now − holders last quarter) / managers;
           universe = held by ≥ 5 managers of the group last quarter.
           C conviction buys: ≥ 3 managers opened a NEW position of ≥ 1 % of their portfolio.
  Timing   formed at the end of the month that contains quarter end + 50 days (e.g. Q1 → end of May),
           held 3 months, equal weight, price ≥ 5 $.
  Tests    (group A, Holm over 3): Q5 − Q1 Δbreadth spread; Q1 (most sold) vs universe;
           C vs universe. Quarterly non-overlapping t. Net of 0.50 %/side (≈ Yuh). Halves ≤ 2017 / 2018 →.
Caveats: survivorship (Yahoo only has listed tickers), CUSIP→ticker coverage, 13F shows long US
positions only.
Pure, injected for CI (network helpers are thin wrappers).
"""
from __future__ import annotations
import math
import re
import zipfile
import numpy as np
import pandas as pd

from .experiments_51 import _read, _date

GROUPS = ("A hedge-fund proxy (≤ 150 positions)", "B all filers ≥ $1bn")
MIN_TOTAL = 1e9
MAX_POS = 150
MIN_HOLDERS = 5
CONV_W, CONV_N = 0.01, 3
FILED_MAX_DAYS = 50


_B36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cusip_to_int(c: str) -> int:
    """9-character CUSIP → int64 (base 36); -1 if malformed. Deterministic, so caches stay valid."""
    c = (c or "").strip().upper()
    if len(c) != 9:
        return -1
    v = 0
    for ch in c:
        k = _B36.find(ch)
        if k < 0:
            return -1
        v = v * 36 + k
    return v


def int_to_cusip(v: int) -> str:
    out = []
    for _ in range(9):
        v, k = divmod(int(v), 36)
        out.append(_B36[k])
    return "".join(reversed(out))


def parse_all_zip(fileobj, min_total: float = MIN_TOTAL) -> pd.DataFrame:
    """13F data-set zip → [cik, period, filed, cusip, value($)] for every 13F-HR filer ≥ min_total."""
    with zipfile.ZipFile(fileobj) as z:
        sub = _read(z, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "PERIODOFREPORT", "CIK"])
        cov = _read(z, "COVERPAGE.tsv", ["ACCESSION_NUMBER", "ISAMENDMENT"])
        if sub is None:
            return pd.DataFrame()
        sub.columns = [c.upper() for c in sub.columns]
        sub = sub[sub["SUBMISSIONTYPE"].fillna("").str.strip().str.upper() == "13F-HR"]
        if cov is not None:
            cov.columns = [c.upper() for c in cov.columns]
            am = set(cov.loc[cov["ISAMENDMENT"].fillna("N").str.upper().str[:1] == "Y", "ACCESSION_NUMBER"])
            sub = sub[~sub["ACCESSION_NUMBER"].isin(am)]
        if sub.empty:
            return pd.DataFrame()
        accs = set(sub["ACCESSION_NUMBER"])
        reader = _read(z, "INFOTABLE.tsv", ["ACCESSION_NUMBER", "CUSIP", "VALUE", "PUTCALL"], chunksize=300_000)
        if reader is None:
            return pd.DataFrame()
        parts, acc_id, cus = [], {a: i for i, a in enumerate(sorted(accs))}, {}
        for ch in reader:
            ch.columns = [c.upper() for c in ch.columns]
            ch = ch[ch["ACCESSION_NUMBER"].isin(accs)]
            if "PUTCALL" in ch:
                ch = ch[ch["PUTCALL"].isna() | (ch["PUTCALL"].str.strip() == "")]
            if not len(ch):
                continue
            v = pd.to_numeric(ch["VALUE"], errors="coerce")
            cc = np.fromiter((cus[x] if x in cus else cus.setdefault(x, cusip_to_int(x)) for x in ch["CUSIP"].astype(str)),
                             dtype=np.int64, count=len(ch))
            g = pd.DataFrame({"a": ch["ACCESSION_NUMBER"].map(acc_id).to_numpy(dtype=np.int32), "c": cc,
                              "v": v.to_numpy()}).dropna()
            g = g[g["c"] >= 0]
            parts.append(g.groupby(["a", "c"], sort=False)["v"].sum())
    if not parts:
        return pd.DataFrame()
    h = pd.concat(parts).groupby(level=[0, 1]).sum().reset_index()
    h.columns = ["acc", "cusip", "value"]
    meta = pd.DataFrame({"acc": sub["ACCESSION_NUMBER"].map(acc_id).to_numpy(),
                         "cik": pd.to_numeric(sub["CIK"], errors="coerce").to_numpy(),
                         "filed": _date(sub["FILING_DATE"]).to_numpy(),
                         "period": _date(sub["PERIODOFREPORT"]).to_numpy()}).dropna()
    meta["scale"] = np.where(meta["filed"] >= pd.Timestamp("2023-01-01"), 1.0, 1000.0)
    h = h.merge(meta, on="acc")
    h["value"] = (h["value"] * h["scale"]).astype("float64")
    tot = h.groupby("acc")["value"].transform("sum")
    h = h[tot >= min_total]
    out = pd.DataFrame({"cik": h["cik"].astype("int64").to_numpy(), "period": h["period"].to_numpy(),
                        "filed": h["filed"].to_numpy(), "cusip": h["cusip"].astype("int64").to_numpy(),
                        "value": h["value"].astype("float32").to_numpy()})
    return out


def clean_period(df: pd.DataFrame, period_end: pd.Timestamp) -> pd.DataFrame:
    """Filings in time (≤ 50 days), latest filing per manager → [cik, cusip, value]."""
    df = df[(df["period"] == period_end) & (df["filed"] <= period_end + pd.Timedelta(days=FILED_MAX_DAYS))]
    if df.empty:
        return df[["cik", "cusip", "value"]]
    last = df.groupby("cik")["filed"].transform("max")
    df = df[df["filed"] == last]
    return df.groupby(["cik", "cusip"], as_index=False)["value"].sum()


def period_signals(cur: pd.DataFrame, prev: pd.DataFrame, min_holders: int = MIN_HOLDERS) -> pd.DataFrame:
    """cur/prev [cik, cusip, value] of two consecutive quarters → rows per (group, cusip)."""
    both = set(cur["cik"]) & set(prev["cik"])
    c = cur[cur["cik"].isin(both)].copy()
    p = prev[prev["cik"].isin(both)]
    npos = c.groupby("cik").size()
    conc = set(npos[npos <= MAX_POS].index)
    c["w"] = c["value"] / c.groupby("cik")["value"].transform("sum")
    prev_keys = pd.MultiIndex.from_frame(p[["cik", "cusip"]])
    c["is_new"] = ~pd.MultiIndex.from_frame(c[["cik", "cusip"]]).isin(prev_keys)
    out = []
    for grp, mset in zip(GROUPS, (conc, both)):
        if len(mset) < 10:
            continue
        cc, pp = c[c["cik"].isin(mset)], p[p["cik"].isin(mset)]
        hc, hp = cc.groupby("cusip")["cik"].nunique(), pp.groupby("cusip")["cik"].nunique()
        uni = hp[hp >= min_holders].index
        conv = cc[cc["is_new"] & (cc["w"] >= CONV_W)].groupby("cusip")["cik"].nunique()
        idx = uni.union(conv[conv >= 1].index)
        df = pd.DataFrame(index=idx)
        df["in_uni"] = df.index.isin(uni)
        df["dbreadth"] = (hc.reindex(idx).fillna(0) - hp.reindex(idx).fillna(0)) / len(mset)
        df["hold_prev"] = hp.reindex(idx).fillna(0).astype(int)
        df["conv_new"] = conv.reindex(idx).fillna(0).astype(int)
        df["group"], df["n_mgr"] = grp, len(mset)
        out.append(df.reset_index().rename(columns={"index": "cusip"}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def formation_month(period_end: pd.Timestamp) -> pd.Period:
    return pd.Period(period_end + pd.Timedelta(days=FILED_MAX_DAYS), "M")


def evaluate(sig: pd.DataFrame, closes: pd.DataFrame, spy: pd.Series, tick: dict, cost_side: float = 0.005) -> dict:
    """sig: period_signals rows + 'period'. closes: monthly closes (PeriodIndex) per ticker.
    → {group: DataFrame per quarter with ex-returns of Q1..Q5, universe, C, and turnover}."""
    res = {}
    sig = sig.assign(ticker=sig["cusip"].map(tick)).dropna(subset=["ticker"])
    for grp, gs in sig.groupby("group"):
        rows, prev_sets = [], {}
        for per, g in gs.groupby("period"):
            F = formation_month(pd.Timestamp(per))
            if F + 3 not in closes.index or F not in closes.index or F not in spy.index or F + 3 not in spy.index:
                continue
            g = g.drop_duplicates("ticker")
            t = [x for x in g["ticker"] if x in closes]
            c0, c3 = closes.loc[F, t], closes.loc[F + 3, t]
            r = (c3 / c0 - 1)[(c0 >= 5) & np.isfinite(c3 / c0)]
            spy_r = spy[F + 3] / spy[F] - 1
            g = g.set_index("ticker").loc[[x for x in r.index]]
            g["ex"] = r.reindex(g.index) - spy_r
            u = g[g["in_uni"]]
            if len(u) < 50:
                continue
            q = pd.qcut(u["dbreadth"].rank(method="first"), 5, labels=False) + 1
            row = {"period": per, "F": F, "spy": spy_r, "n_uni": len(u), "uni": u["ex"].mean(), "n_mgr": int(g["n_mgr"].iloc[0])}
            sets = {}
            for k in range(1, 6):
                s = u.index[q == k]
                row[f"Q{k}"] = u.loc[s, "ex"].mean()
                sets[f"Q{k}"] = set(s)
            sets["uni"] = set(u.index)
            cs = g.index[g["conv_new"] >= CONV_N]
            row["C"], row["n_C"] = (g.loc[cs, "ex"].mean() if len(cs) else np.nan), len(cs)
            sets["C"] = set(cs)
            for k, s in sets.items():
                ps = prev_sets.get(k)
                row[f"turn_{k}"] = 1.0 if not ps else len(s ^ ps) / max(len(s | ps), 1)
            prev_sets = sets
            rows.append(row)
        res[grp] = pd.DataFrame(rows)
    return res


def _t(x) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std(ddof=1) * math.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def _p_from_t(t: float) -> float:
    return float(math.erfc(abs(t) / math.sqrt(2))) if np.isfinite(t) else float("nan")


def _cagr_q(r: pd.Series) -> float:
    r = r.dropna()
    return float((1 + r).prod() ** (4 / len(r)) - 1) if len(r) >= 4 else float("nan")


def run_experiment96_report(res: dict, diag: list | None = None, cost_side: float = 0.005) -> str:
    from datetime import datetime, timezone
    from .experiments_94 import holm
    L = [f"# Experiment #96 — all big 13F filers: newly bought vs sold stocks ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    pc = lambda x: f"{100*x:+.2f} %" if np.isfinite(x) else "—"
    f = lambda x: f"{x:+.2f}" if np.isfinite(x) else "—"
    for grp in GROUPS:
        d = res.get(grp)
        L.append(f"## {grp}")
        if d is None or d.empty:
            L += ["No data.", ""]
            continue
        L.append(f"{len(d)} quarters {d['period'].min():%Y-%m} → {d['period'].max():%Y-%m}; managers per quarter "
                 f"median {int(d['n_mgr'].median())}; stocks in universe median {int(d['n_uni'].median())}; "
                 f"conviction-buy stocks per quarter median {int(d['n_C'].median())}.")
        L.append("")
        L.append("| portfolio (3 M after formation, vs SPY) | mean per quarter | t | ≤ 2017 | 2018 → | CAGR gross | CAGR net ≈ Yuh |")
        L.append("|---|--:|--:|--:|--:|--:|--:|")
        early = d["period"] <= pd.Timestamp("2017-12-31")
        for k, lab in [("Q1", "Q1 most sold (Δbreadth lowest)"), ("Q2", "Q2"), ("Q3", "Q3"), ("Q4", "Q4"),
                       ("Q5", "Q5 most newly bought"), ("uni", "whole universe"), ("C", f"C conviction buys (≥ {CONV_N} new ≥ 1 % positions)")]:
            x = d[k]
            gross = x + d["spy"]
            net = gross - (2 * cost_side * d[f"turn_{k}"] if f"turn_{k}" in d else 0.0)
            L.append(f"| {lab} | {pc(x.mean())} | {f(_t(x))} | {pc(x[early].mean())} | {pc(x[~early].mean())} | "
                     f"{pc(_cagr_q(gross))} | {pc(_cagr_q(net))} |")
        L.append(f"| SPY | — | — | — | — | {pc(_cagr_q(d['spy']))} | — |")
        sp = d["Q5"] - d["Q1"]
        q1u = d["Q1"] - d["uni"]
        cu = d["C"] - d["uni"]
        tests = [("Q5 − Q1 spread", sp), ("Q1 − universe (sell warning)", q1u), ("C − universe", cu)]
        ps = [_p_from_t(_t(x)) for _, x in tests]
        adj = holm([p if np.isfinite(p) else 1.0 for p in ps])
        L.append("")
        L.append("| test | mean per quarter | t | p | Holm p | ≤ 2017 (t) | 2018 → (t) |")
        L.append("|---|--:|--:|--:|--:|--:|--:|")
        for (nm, x), p, a in zip(tests, ps, adj):
            L.append(f"| {nm} | {pc(x.mean())} | {f(_t(x))} | {f(p)} | {f(a)} | {pc(x[early].mean())} ({f(_t(x[early]))}) | "
                     f"{pc(x[~early].mean())} ({f(_t(x[~early]))}) |")
        L.append("")
    L.append("Reading: group A is the primary test (closest to 'hedge funds'); Holm over its 3 tests. Group B shows "
             "whether it is just the whole institutional market.")
    L.append("Caveats: survivorship (delisted stocks have no Yahoo prices — biases sold stocks upward); "
             "CUSIP→ticker via OpenFIGI; 13F = long US positions only, up to 50 days late.")
    return "\n".join(L)
