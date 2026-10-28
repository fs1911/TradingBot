"""
Experiment #63 — how good are professional forecasters? (public survey data)

  A Recessions: Survey of Professional Forecasters (Philadelphia Fed, since 1968),
    mean probability that real GDP falls in the NEXT quarter ("anxious index", RECESS2)
    and four quarters ahead (RECESS5) — what did the professionals say right before each
    US recession (NBER dates)? Hit rate, false alarms, separation (AUC).
  B Unemployment: SPF median forecast 4 quarters ahead (UNEMP6) vs the naive forecast
    "stays where it is" (last known value) — error size, and did they see the big rises?
  C Stocks: Livingston Survey S&P forecasts (6 / 12 months, 1952–1990, discontinued series)
    vs what happened (Yahoo ^GSPC), if the series is in the published workbook; SPF
    anxious index as a stock signal (next-12-month S&P return by anxiety quintile).
  D Private investors: AAII bull–bear sentiment (if the legacy file is still reachable).
Data are discovered at run time: the landing pages are scanned for workbook links and
every workbook's sheets/columns are listed in the report, so missing series are visible.
Workbooks are read with a minimal built-in .xlsx reader (no extra packages on the server).
Pure, injected for CI.
"""
from __future__ import annotations
import io
import math
import re
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

PAGES = [
    "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/median-forecasts",
    "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/mean-forecasts",
    "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/anxious-index",
    "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/probability-variables",
    "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters",
    "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/livingston-historical-data",
    "https://www.richmondfed.org/research/national_economy/cfo_survey/data_and_results",
]
DIRECT = ["https://www.aaii.com/files/surveys/sentiment.xls"]
KEYWORDS = ("median", "mean", "recess", "prob", "anxious", "livingston", "level", "unemp", "cfo", "survey", "sentiment")

# NBER US recessions as quarters of contraction (peak quarter excluded, trough included)
NBER_RECESSIONS = [("1970Q1", "1970Q4"), ("1974Q1", "1975Q1"), ("1980Q2", "1980Q3"), ("1981Q4", "1982Q4"),
                   ("1990Q4", "1991Q1"), ("2001Q2", "2001Q4"), ("2008Q1", "2009Q2"), ("2020Q1", "2020Q2")]


# ── minimal .xlsx reader ──────────────────────────────────────────────────────

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(data: bytes) -> dict:
    """{sheet name: DataFrame with the first non-empty row as header}."""
    z = zipfile.ZipFile(io.BytesIO(data))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", _NS):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    out = {}
    for sh in wb.find("m:sheets", _NS):
        name = sh.get("name")
        rid = sh.get(f"{{{_NS['r']}}}id")
        path = target.get(rid, "")
        path = path.lstrip("/")
        path = path if path.startswith("xl/") else "xl/" + path
        if path not in z.namelist():
            continue
        root = ET.fromstring(z.read(path))
        rows = []
        for row in root.iter(f"{{{_NS['m']}}}row"):
            vals = {}
            for c in row.findall("m:c", _NS):
                ref, t = c.get("r"), c.get("t")
                v = c.find("m:v", _NS)
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(f"{{{_NS['m']}}}t"))
                elif v is not None and v.text is not None:
                    try:
                        val = float(v.text)
                    except ValueError:
                        val = v.text
                else:
                    val = None
                if ref:
                    vals[_col_index(ref)] = val
            if vals:
                rows.append(vals)
        if not rows:
            continue
        width = max(max(r) for r in rows) + 1
        grid = [[r.get(i) for i in range(width)] for r in rows]
        header = [str(h).strip() if h is not None else f"col{i}" for i, h in enumerate(grid[0])]
        out[name] = pd.DataFrame(grid[1:], columns=header)
    return out


def read_workbook(data: bytes, url: str = "") -> dict:
    if data[:2] == b"PK":
        return read_xlsx(data)
    try:  # legacy .xls / csv if pandas has an engine for it
        if url.lower().endswith(".csv"):
            return {"csv": pd.read_csv(io.BytesIO(data))}
        return pd.read_excel(io.BytesIO(data), sheet_name=None)
    except Exception:
        return {}


# ── discovery ─────────────────────────────────────────────────────────────────

def find_links(html: str, base: str) -> list:
    from urllib.parse import urljoin
    links = re.findall(r'href="([^"]+\.(?:xlsx|xls|csv))(?:\?[^"]*)?"', html, flags=re.I)
    out = []
    for l in links:
        u = urljoin(base, l)
        if any(k in u.lower() for k in KEYWORDS) and u not in out:
            out.append(u)
    return out


def fetch(url: str, timeout: int = 60, max_bytes: int = 40_000_000) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; TradingBot)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(max_bytes)


def discover(log=None, max_per_page: int = 25) -> tuple:
    """→ ({url: {sheet: DataFrame}}, diagnostics lines)."""
    books, diag = {}, []
    urls = []
    for p in PAGES:
        try:
            html = fetch(p, timeout=40).decode("utf-8", "replace")
            ls = find_links(html, p)[:max_per_page]
            diag.append(f"{p} → {len(ls)} workbook links")
            urls += [u for u in ls if u not in urls]
        except Exception as e:
            diag.append(f"{p} → ERROR {repr(e)[:80]}")
    for u in urls + DIRECT:
        try:
            data = fetch(u)
            wb = read_workbook(data, u)
            books[u] = wb
            if log:
                log(f"#63 {u}: {len(wb)} sheets")
        except Exception as e:
            diag.append(f"{u} → ERROR {repr(e)[:80]}")
    return books, diag


# ── helpers ───────────────────────────────────────────────────────────────────

def find_columns(books: dict, pattern: str) -> list:
    """[(url, sheet, DataFrame)] whose columns match regex `pattern` (case-insensitive)."""
    rx = re.compile(pattern, re.I)
    hits = []
    for u, wb in books.items():
        for sh, df in wb.items():
            if any(rx.search(str(c)) for c in df.columns):
                hits.append((u, sh, df))
    return hits


def quarterly(df: pd.DataFrame) -> pd.DataFrame:
    """SPF sheet with YEAR, QUARTER columns → PeriodIndex (Q)."""
    cols = {c.upper(): c for c in df.columns}
    if "YEAR" not in cols or "QUARTER" not in cols:
        return pd.DataFrame()
    d = df.copy()
    d["_y"] = pd.to_numeric(d[cols["YEAR"]], errors="coerce")
    d["_q"] = pd.to_numeric(d[cols["QUARTER"]], errors="coerce")
    d = d.dropna(subset=["_y", "_q"])
    d.index = pd.PeriodIndex([pd.Period(f"{int(y)}Q{int(q)}", "Q") for y, q in zip(d["_y"], d["_q"])])
    d.columns = [str(c).upper() for c in d.columns]
    return d[~d.index.duplicated(keep="last")].sort_index()


def recession_quarters() -> set:
    out = set()
    for a, b in NBER_RECESSIONS:
        out |= set(pd.period_range(a, b, freq="Q"))
    return out


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    pos, neg = scores[labels == 1], scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float(np.mean([(p > neg).mean() + 0.5 * (p == neg).mean() for p in pos]))


# ── analyses ──────────────────────────────────────────────────────────────────

def recession_analysis(rec: pd.DataFrame) -> list:
    L = []
    rq = recession_quarters()
    starts = [pd.Period(a, "Q") for a, _ in NBER_RECESSIONS]
    p2 = pd.to_numeric(rec.get("RECESS2"), errors="coerce")
    p5 = pd.to_numeric(rec.get("RECESS5"), errors="coerce") if "RECESS5" in rec else None
    scale = 100.0 if p2.max() > 1.5 else 1.0
    p2 = p2 / scale
    if p5 is not None:
        p5 = p5 / scale
    L.append("| recession starts | P(decline next quarter) said the quarter before | P(decline in 4 quarters) said a year before |")
    L.append("|---|--:|--:|")
    for s in starts:
        a = p2.get(s - 1, np.nan)
        b = p5.get(s - 4, np.nan) if p5 is not None else np.nan
        L.append(f"| {s} | {'—' if not np.isfinite(a) else f'{100*a:.0f} %'} | {'—' if not np.isfinite(b) else f'{100*b:.0f} %'} |")
    target = pd.Series([1 if (q + 1) in rq else 0 for q in p2.index], index=p2.index)
    ok = p2.notna()
    sc, lb = p2[ok].to_numpy(), target[ok].to_numpy()
    first_hits = sum(1 for s in starts if np.isfinite(p2.get(s - 1, np.nan)) and p2.get(s - 1) >= 0.5)
    alarms = int(((p2 >= 0.5) & (target == 0)).sum())
    covered = sum(1 for s in starts if np.isfinite(p2.get(s - 1, np.nan)))
    L.append("")
    L.append(f"Surveys {p2.index[0]}–{p2.index[-1]}: average P(decline next quarter) before a recession quarter "
             f"{100*sc[lb == 1].mean():.0f} % vs other quarters {100*sc[lb == 0].mean():.0f} % (AUC {auc(sc, lb):.2f}; "
             f"0.5 = no skill, 1 = perfect). Recession STARTS flagged with ≥ 50 % the quarter before: "
             f"**{first_hits} of {covered}**; false alarms (≥ 50 %, no recession next quarter): {alarms}.")
    return L


def unemployment_analysis(u: pd.DataFrame) -> list:
    L = []
    if not {"UNEMP1", "UNEMP6"} <= set(u.columns):
        return ["UNEMP1/UNEMP6 not found."]
    f = pd.to_numeric(u["UNEMP6"], errors="coerce")        # forecast for quarter q+4
    last = pd.to_numeric(u["UNEMP1"], errors="coerce")     # last known (quarter q−1)
    actual_by_q = last.copy()
    actual_by_q.index = actual_by_q.index - 1              # survey q reports quarter q−1
    rows = []
    for q in f.index:
        tgt = q + 4
        a = actual_by_q.get(tgt, np.nan)
        if np.isfinite(a) and np.isfinite(f[q]) and np.isfinite(last[q]):
            rows.append((q, f[q], last[q], a))
    if len(rows) < 20:
        return ["Too few matched unemployment forecasts."]
    d = pd.DataFrame(rows, columns=["q", "f", "naive", "a"]).set_index("q")
    rmse = lambda e: float(np.sqrt((e ** 2).mean()))
    rise = d["a"] - d["naive"] >= 1.0
    seen = (d["f"] - d["naive"] >= 0.5) & rise
    L.append(f"{len(d)} forecasts {d.index[0]}–{d.index[-1]}: error (RMSE) SPF {rmse(d['f'] - d['a']):.2f} pt vs naive "
             f"'no change' {rmse(d['naive'] - d['a']):.2f} pt. Big rises (≥ 1 pt within ~5 quarters): {int(rise.sum())}; "
             f"of those the professionals forecast a rise of ≥ 0.5 pt: **{int(seen.sum())}**.")
    return L


def stock_anxiety(rec: pd.DataFrame, gspc_m: pd.Series) -> list:
    p2 = pd.to_numeric(rec.get("RECESS2"), errors="coerce")
    p2 = p2 / (100.0 if p2.max() > 1.5 else 1.0)
    if gspc_m is None or gspc_m.empty:
        return ["No S&P data."]
    q_end = gspc_m.groupby(gspc_m.index.asfreq("Q")).last()
    fwd = q_end.shift(-4) / q_end - 1
    d = pd.concat([p2.rename("p"), fwd.rename("r")], axis=1).dropna()
    if len(d) < 40:
        return ["Too few observations."]
    d["bucket"] = pd.qcut(d["p"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    g = d.groupby("bucket", observed=True)["r"].agg(["mean", "count"])
    L = ["| professionals' recession worry (quintile) | S&P next 12 months | n |", "|---|--:|--:|"]
    for b, r in g.iterrows():
        lbl = {1: "1 (calmest)", 5: "5 (most worried)"}.get(int(b), str(b))
        L.append(f"| {lbl} | {100*r['mean']:+.1f} % | {int(r['count'])} |")
    L.append(f"Correlation worry → next-12-month return: {d['p'].corr(d['r']):+.2f} (price only).")
    return L


def livingston_stocks(books: dict, gspc_m: pd.Series) -> list:
    hits = find_columns(books, r"SPIF|STOCK|S&P|SP500")
    if not hits:
        return ["No stock-price series found in the Livingston workbooks (the Fed marks them discontinued)."]
    u, sh, df = hits[0]
    cols = [c for c in df.columns if re.search(r"SPIF|STOCK|S&P|SP500", str(c), re.I)]
    L = [f"Found in `{u.rsplit('/', 1)[-1]}` sheet `{sh}`: columns {', '.join(map(str, cols[:8]))}."]
    date_col = next((c for c in df.columns if re.search(r"date|survey", str(c), re.I)), df.columns[0])
    dates = pd.to_datetime(df[date_col], errors="coerce")
    if dates.isna().all():
        num = pd.to_numeric(df[date_col], errors="coerce")
        dates = pd.to_datetime("1899-12-30") + pd.to_timedelta(num, unit="D")
    base = next((c for c in cols if re.search(r"BP|BASE|_?0$|ACT", str(c), re.I)), None)
    f12 = next((c for c in cols if re.search(r"12", str(c))), None)
    if base is None or f12 is None or gspc_m is None or gspc_m.empty:
        return L + ["Could not identify base/12-month columns — listed for manual mapping."]
    d = pd.DataFrame({"date": dates, "base": pd.to_numeric(df[base], errors="coerce"),
                      "f12": pd.to_numeric(df[f12], errors="coerce")}).dropna()
    d["m"] = d["date"].dt.to_period("M")
    d["exp"] = d["f12"] / d["base"] - 1
    act = gspc_m.shift(-12) / gspc_m - 1
    d["act"] = d["m"].map(act)
    d = d.dropna()
    if len(d) < 20:
        return L + ["Too few matched stock forecasts."]
    hit = ((d["exp"] > 0) == (d["act"] > 0)).mean()
    up_share = (d["act"] > 0).mean()
    L.append(f"{len(d)} half-yearly surveys {d['m'].iloc[0]}–{d['m'].iloc[-1]}: forecast 12-month change "
             f"avg {100*d['exp'].mean():+.1f} %, actual avg {100*d['act'].mean():+.1f} %; direction right "
             f"**{100*hit:.0f} %** (always guessing 'up' would have been right {100*up_share:.0f} %); "
             f"correlation forecast → actual {d['exp'].corr(d['act']):+.2f}.")
    return L


def aaii_analysis(books: dict, gspc_m: pd.Series) -> list:
    hits = find_columns(books, r"bull")
    if not hits:
        return ["AAII data not reachable (full history now members-only)."]
    u, sh, df = hits[0]
    cols = {str(c).lower(): c for c in df.columns}
    bull = next((cols[c] for c in cols if "bull" in c and "bear" not in c), None)
    bear = next((cols[c] for c in cols if "bear" in c and "bull" not in c), None)
    dcol = next((cols[c] for c in cols if "date" in c), df.columns[0])
    if bull is None or bear is None or gspc_m is None or gspc_m.empty:
        return [f"AAII sheet found ({sh}) but columns unclear: {list(df.columns)[:8]}"]
    d = pd.DataFrame({"date": pd.to_datetime(df[dcol], errors="coerce"),
                      "s": pd.to_numeric(df[bull], errors="coerce") - pd.to_numeric(df[bear], errors="coerce")}).dropna()
    d = d.groupby(d["date"].dt.to_period("M"))["s"].mean()
    fwd = (gspc_m.shift(-6) / gspc_m - 1).rename("r")
    x = pd.concat([d.rename("s"), fwd], axis=1).dropna()
    if len(x) < 60:
        return ["Too few AAII observations."]
    x["b"] = pd.qcut(x["s"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    g = x.groupby("b", observed=True)["r"].mean()
    return [f"AAII bull−bear spread {x.index[0]}–{x.index[-1]}: next-6-month S&P by sentiment quintile "
            + ", ".join(f"Q{int(k)} {100*v:+.1f} %" for k, v in g.items())
            + f" (Q1 = most bearish); correlation {x['s'].corr(x['r']):+.2f}."]


def run_experiment63_report(books: dict, diag: list, gspc: pd.Series | None) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #63 — how good are professional forecasters? ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    gspc_m = None
    if gspc is not None and len(gspc):
        s = pd.Series(gspc).dropna()
        idx = pd.to_datetime(s.index)
        s.index = (idx.tz_localize(None) if idx.tz is not None else idx).to_period("M")
        gspc_m = s.groupby(level=0).last()
    rec_hits = [h for h in find_columns(books, r"^RECESS2$")]
    rec = quarterly(rec_hits[0][2]) if rec_hits else pd.DataFrame()
    L.append("## A Did the professionals see recessions coming? (SPF anxious index)")
    L += recession_analysis(rec) if not rec.empty and "RECESS2" in rec else ["RECESS2 series not found."]
    L.append("")
    L.append("## B Unemployment 4 quarters ahead: professionals vs 'no change'")
    un_hits = [h for h in find_columns(books, r"^UNEMP6$")]
    un = quarterly(un_hits[0][2]) if un_hits else pd.DataFrame()
    L += unemployment_analysis(un) if not un.empty else ["UNEMP series not found."]
    L.append("")
    L.append("## C Stocks")
    L.append("### Livingston Survey S&P forecasts")
    L += livingston_stocks(books, gspc_m)
    L.append("")
    L.append("### Professionals' recession worry as a stock signal")
    L += stock_anxiety(rec, gspc_m) if not rec.empty and "RECESS2" in rec else ["RECESS2 series not found."]
    L.append("")
    L.append("## D Private investors' mood (AAII)")
    L += aaii_analysis(books, gspc_m)
    L.append("")
    L.append("## Data discovery (what was found)")
    L += [f"- {x}" for x in diag]
    for u, wb in books.items():
        L.append(f"- `{u.rsplit('/', 1)[-1]}`: " + "; ".join(
            f"{sh} [{', '.join(map(str, list(df.columns)[:10]))}{' …' if df.shape[1] > 10 else ''}] ({len(df)} rows)"
            for sh, df in list(wb.items())[:6]) + (f"; … {len(wb)} sheets" if len(wb) > 6 else ""))
    return "\n".join(L)
