"""
Experiments #88 – #90 (requested 9.11.2026): data types never tested before.

#88 Analyst rating changes (Benzinga headlines via Alpaca news, 2016 →, US stocks)
    Headline classes (pre-registered regexes): UPGRADE, DOWNGRADE, PT_RAISE (price target raised),
    PT_CUT (price target lowered); headlines containing both directions are dropped.
    Entry: close of the first trading day AFTER the news day (New York date). Outcome: excess vs SPY
    after 1 / 5 / 20 / 60 trading days, plus the move already made. Cool-down 5 trading days per
    stock and class. Random-date bootstrap, Holm over all cells.

#89 Crypto: fear & greed index and on-chain data (BTC, ETH, XRP)
    Fear & Greed (alternative.me, daily since 2018-02): events 'extreme fear' (≤ 20) and 'extreme
    greed' (≥ 80), first day after ≥ 30 days outside; next 7 / 30 / 90 days vs any day.
    Month-end signals → next 30-day return (non-overlapping months): F&G level; CoinMetrics
    community metrics where available: 30-day growth of active addresses, of transactions, and
    MVRV (market / realised value). Rank correlation (Spearman) and top-minus-bottom tercile;
    p from a permutation test (5000 shuffles); Holm over all.

#90 Google search interest (Google Trends, weekly, last 5 years)
    Abnormal search interest ASVI = log(SVI_t) − log(median SVI of the previous 8 weeks)
    (Da, Engelberg & Gao 2011). Stocks: each week long the top 20 % ASVI, short the bottom 20 %,
    hold one week (and 4 weeks), excess vs SPY, gross and net of 10 bp per side. Events: ASVI ≥
    log 2 (search interest doubled) → next 1 / 4 weeks. Crypto: same per coin.
Pure, injected for CI.
"""
from __future__ import annotations
import json
import math
import re
import urllib.parse
import numpy as np
import pandas as pd

# ── shared ───────────────────────────────────────────────────────────────────

def holm(p: dict) -> dict:
    items = sorted((v, k) for k, v in p.items() if np.isfinite(v))
    m, out, run = len(items), {}, 0.0
    for i, (v, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v)); out[k] = run
    return out


def boot_p(base: np.ndarray, n: int, observed: float, reps: int = 4000, seed: int = 88) -> float:
    base = base[np.isfinite(base)]
    if n < 10 or len(base) < n:
        return float("nan")
    rng = np.random.default_rng(seed)
    m = base[rng.integers(0, len(base), size=(reps, n))].mean(axis=1)
    c = m.mean()
    return float((np.abs(m - c) >= abs(observed - c)).mean())


def fwd_excess(px: pd.Series, bench: pd.Series | None, n: int) -> np.ndarray:
    v = px.to_numpy(dtype=float)
    r = np.full(len(v), np.nan)
    if len(v) > n:
        r[:-n] = v[n:] / v[:-n] - 1
    if bench is not None:
        b = bench.reindex(px.index).ffill().to_numpy(dtype=float)
        rb = np.full(len(v), np.nan)
        if len(v) > n:
            rb[:-n] = b[n:] / b[:-n] - 1
        r = r - rb
    return r


def back_excess(px: pd.Series, bench: pd.Series | None, n: int = 2) -> np.ndarray:
    v = px.to_numpy(dtype=float)
    r = np.full(len(v), np.nan)
    r[n:] = v[n:] / v[:-n] - 1
    if bench is not None:
        b = bench.reindex(px.index).ffill().to_numpy(dtype=float)
        rb = np.full(len(v), np.nan); rb[n:] = b[n:] / b[:-n] - 1
        r = r - rb
    return r


def entry_indices(news_days, px_index: pd.DatetimeIndex, cooldown: int = 5) -> list:
    out, last = [], -10 ** 9
    for d in sorted(news_days):
        k = px_index.searchsorted(pd.Timestamp(d), side="right")
        if k >= len(px_index):
            break
        if k - last >= cooldown:
            out.append(k); last = k
    return out


# ── #88 analyst rating changes ───────────────────────────────────────────────

_UP = re.compile(r"\bupgrade[sd]?\b", re.I)
_DOWN = re.compile(r"\bdowngrade[sd]?\b", re.I)
_PT = re.compile(r"\b(price target|pt)\b", re.I)
_RAISE = re.compile(r"\b(raise[sd]?|boost[sd]?|lift[sd]?|increase[sd]?|bump[sd]?)\b", re.I)
_CUT = re.compile(r"\b(lower[sd]?|cut[s]?|reduce[sd]?|trim[sd]?|slash(es|ed)?)\b", re.I)


def classify_rating(headline: str) -> str | None:
    h = headline or ""
    up, down = bool(_UP.search(h)), bool(_DOWN.search(h))
    if up != down:
        return "UPGRADE" if up else "DOWNGRADE"
    if up and down:
        return None
    if _PT.search(h):
        r, c = bool(_RAISE.search(h)), bool(_CUT.search(h))
        if r != c:
            return "PT_RAISE" if r else "PT_CUT"
    return None


H88 = {"1 d": 1, "5 d": 5, "20 d": 20, "60 d": 60}
CLASSES = ("UPGRADE", "DOWNGRADE", "PT_RAISE", "PT_CUT")


def run_experiment88_report(events: dict, px: dict, spy: pd.Series, diag: list) -> str:
    """events: {sym: DataFrame[ts, tone=class]}."""
    from datetime import datetime, timezone
    L = [f"# Experiment #88 — analyst rating changes ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L += [" ".join(diag), "",
          "Entry = close of the first trading day AFTER the news day (New York date). 'already' = move over the two "
          "closes before entry. Excess vs SPY. p = random-date bootstrap (two-sided); Holm over all cells.", ""]
    syms = [s for s in events if s in px]
    ex = {s: {h: fwd_excess(px[s], spy, n) for h, n in H88.items()} for s in syms}
    pre = {s: back_excess(px[s], spy) for s in syms}
    base = {h: np.concatenate([ex[s][h] for s in syms]) if syms else np.array([]) for h in H88}
    pv, rows = {}, []
    for cls in CLASSES:
        idx = {}
        for s in syms:
            e = events[s]
            if e.empty:
                continue
            d = e.loc[e["tone"] == cls, "ts"].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
            idx[s] = entry_indices(d.unique(), px[s].index)
        n = sum(len(v) for v in idx.values())
        row = {"cls": cls, "n": n}
        al = np.concatenate([pre[s][v] for s, v in idx.items() if v]) if n else np.array([])
        row["already"] = float(np.nanmean(al)) if len(al) else np.nan
        for h in H88:
            vals = np.concatenate([ex[s][h][v] for s, v in idx.items() if v]) if n else np.array([])
            vals = vals[np.isfinite(vals)]
            row[h] = (float(vals.mean()) if len(vals) else np.nan, float((vals > 0).mean()) if len(vals) else np.nan)
            if len(vals) >= 10:
                pv[(cls, h)] = boot_p(base[h], len(vals), float(vals.mean()))
        rows.append(row)
    adj = holm(pv)
    L.append("| class | events | already moved | " + " | ".join(f"{h} mean / >0 (p, Holm)" for h in H88) + " |")
    L.append("|---|--:|--:|" + "--:|" * len(H88))
    L.append("| *any day* | | | " + " | ".join(f"{100*np.nanmean(base[h]):+.2f} %" if len(base[h]) else "—" for h in H88) + " |")
    for r in rows:
        cells = []
        for h in H88:
            m, pos = r[h]
            p, q = pv.get((r["cls"], h), np.nan), adj.get((r["cls"], h), np.nan)
            cells.append(f"{100*m:+.2f} % / {100*pos:.0f} % ({p:.3f}, {q:.3f})" if np.isfinite(m) else "—")
        L.append(f"| {r['cls']} | {r['n']:,} | {100*r['already']:+.2f} % | " + " | ".join(cells) + " |")
    sig = [k for k, v in adj.items() if v < 0.05]
    L.append("")
    L.append(f"Cells tested: {len(pv)}; significant after Holm: {len(sig)}" + (" — " + "; ".join(f"{a} {b}" for a, b in sig) if sig else "") + ".")
    L.append("Caveats: only rating changes that Benzinga reported in a headline; the same change by several brokers "
             "on one day counts once (cool-down); large US companies only.")
    return "\n".join(L)


# ── #89 crypto: fear & greed, on-chain ──────────────────────────────────────

FNG_URL = "https://api.alternative.me/fng/?limit=0&format=json"
CM_URL = ("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={a}&metrics={m}"
          "&frequency=1d&start_time=2016-01-01&page_size=10000")
CM_METRICS = ("AdrActCnt", "TxCnt", "CapMVRVCur")


def parse_fng(body: str) -> pd.Series:
    js = json.loads(body)
    d = js.get("data") or []
    s = pd.Series({pd.to_datetime(int(x["timestamp"]), unit="s").normalize(): float(x["value"]) for x in d})
    return s.sort_index()


def parse_coinmetrics(body: str) -> pd.DataFrame:
    js = json.loads(body)
    d = js.get("data") or []
    if not d:
        return pd.DataFrame()
    df = pd.DataFrame(d)
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None).dt.normalize()
    df = df.set_index("time").drop(columns=[c for c in ("asset",) if c in df.columns])
    return df.apply(pd.to_numeric, errors="coerce")


def fetch_coinmetrics(get, asset: str) -> tuple:
    """Try all metrics together, then one by one (the community tier may refuse some)."""
    errs = []
    try:
        df = parse_coinmetrics(get(CM_URL.format(a=asset, m=",".join(CM_METRICS))))
        if not df.empty:
            return df, errs
    except Exception as e:
        errs.append(f"{asset} all: {repr(e)[:80]}")
    parts = []
    for m in CM_METRICS:
        try:
            p = parse_coinmetrics(get(CM_URL.format(a=asset, m=m)))
            if not p.empty:
                parts.append(p)
        except Exception as e:
            errs.append(f"{asset} {m}: {repr(e)[:80]}")
    return (pd.concat(parts, axis=1) if parts else pd.DataFrame()), errs


def first_cross(x: pd.Series, cond, quiet: int = 30) -> list:
    out, gap = [], quiet
    for d, v in x.items():
        if cond(v):
            if gap >= quiet:
                out.append(d)
            gap = 0
        else:
            gap += 1
    return out


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra, rb = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy()
    if np.std(ra) == 0 or np.std(rb) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def perm_p(a: np.ndarray, b: np.ndarray, reps: int = 5000, seed: int = 89) -> float:
    obs = spearman(a, b)
    if not np.isfinite(obs):
        return float("nan")
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(reps):
        if abs(spearman(a, rng.permutation(b))) >= abs(obs):
            cnt += 1
    return (cnt + 1) / (reps + 1)


def monthly_ic(signal: pd.Series, px: pd.Series, horizon: int = 30) -> dict:
    """Month-end signal vs next `horizon` calendar-day return (non-overlapping)."""
    s = signal.dropna()
    if len(s) < 200:
        return {}
    me = s.resample("ME").last().dropna()
    rows = []
    for d, v in me.items():
        a, b = px.asof(d), px.asof(d + pd.Timedelta(days=horizon))
        if d + pd.Timedelta(days=horizon) > px.index[-1] or not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
            continue
        rows.append((v, b / a - 1))
    if len(rows) < 24:
        return {}
    x, y = np.array([r[0] for r in rows]), np.array([r[1] for r in rows])
    q1, q2 = np.quantile(x, [1 / 3, 2 / 3])
    return {"n": len(rows), "ic": spearman(x, y), "p": perm_p(x, y),
            "top": float(y[x >= q2].mean()), "bottom": float(y[x <= q1].mean())}


def run_experiment89_report(fng: pd.Series, onchain: dict, px: dict, diag: list) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #89 — crypto: fear & greed, on-chain ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L += [" ".join(diag), ""]
    pv = {}
    # events
    if len(fng):
        L.append(f"## Fear & Greed events ({fng.index.min():%Y-%m}–{fng.index.max():%Y-%m}); next 7 / 30 / 90 days vs any day")
        L.append("| coin | event | n | 7 d | 30 d | 90 d | any day 7 / 30 / 90 |")
        L.append("|---|---|--:|--:|--:|--:|--:|")
        ev = {"extreme fear (≤ 20)": first_cross(fng, lambda v: v <= 20),
              "extreme greed (≥ 80)": first_cross(fng, lambda v: v >= 80)}
        for coin, p in px.items():
            p = p[p.index >= fng.index.min()]
            fw = {h: fwd_excess(p, None, n) for h, n in (("7 d", 7), ("30 d", 30), ("90 d", 90))}
            for en, dates in ev.items():
                idx = entry_indices(dates, p.index, cooldown=1)
                cells = []
                for h in fw:
                    vals = fw[h][idx]; vals = vals[np.isfinite(vals)]
                    cells.append(f"{100*vals.mean():+.1f} % ({100*(vals > 0).mean():.0f} % >0)" if len(vals) else "—")
                    if len(vals) >= 8:
                        pv[(coin, en, h)] = boot_p(fw[h], len(vals), float(vals.mean()))
                L.append(f"| {coin} | {en} | {len(idx)} | " + " | ".join(cells) + " | " +
                         " / ".join(f"{100*np.nanmean(fw[h]):+.1f} %" for h in fw) + " |")
        L.append("")
    # monthly ICs
    L.append("## Month-end signal → next 30 days (non-overlapping months)")
    L.append("| coin | signal | months | rank corr. | top third | bottom third | p (perm.) |")
    L.append("|---|---|--:|--:|--:|--:|--:|")
    for coin, p in px.items():
        sigs = {}
        if len(fng):
            sigs["Fear & Greed level"] = fng
        oc = onchain.get(coin, pd.DataFrame())
        if not oc.empty:
            for col, name in (("AdrActCnt", "active addresses, 30-day growth"), ("TxCnt", "transactions, 30-day growth")):
                if col in oc:
                    x = oc[col].rolling(7).mean()
                    sigs[name] = np.log(x / x.shift(30))
            if "CapMVRVCur" in oc:
                sigs["MVRV (market / realised value)"] = oc["CapMVRVCur"]
        for name, s in sigs.items():
            r = monthly_ic(s.replace([np.inf, -np.inf], np.nan), p)
            if not r:
                L.append(f"| {coin} | {name} | — | — | — | — | — |"); continue
            pv[(coin, name, "IC")] = r["p"]
            L.append(f"| {coin} | {name} | {r['n']} | {r['ic']:+.2f} | {100*r['top']:+.1f} % | {100*r['bottom']:+.1f} % | {r['p']:.3f} |")
    adj = holm(pv)
    sig = [k for k, v in adj.items() if v < 0.05]
    L.append("")
    L.append(f"Cells tested: {len(pv)}; significant after Holm: {len(sig)}" + (" — " + "; ".join(" / ".join(k) for k in sig) if sig else "") + ".")
    L.append("Caveats: few independent months (≈ 100 for BTC); crypto returns are extremely noisy; overlapping "
             "90-day windows in the event table.")
    return "\n".join(L)


# ── #90 Google Trends ───────────────────────────────────────────────────────

TRENDS_EXPLORE = "https://trends.google.com/trends/api/explore?hl=en-US&tz=0&req={req}"
TRENDS_MULTILINE = "https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=0&req={req}&token={tok}"


def _strip_xssi(body: str) -> dict:
    i = body.find("{")
    return json.loads(body[i:]) if i >= 0 else {}


def fetch_trends(get, keyword: str, timeframe: str = "today 5-y") -> pd.Series:
    """Weekly search interest (0–100) via the public Trends endpoints. get(url) → str."""
    req = json.dumps({"comparisonItem": [{"keyword": keyword, "geo": "", "time": timeframe}], "category": 0, "property": ""})
    ex = _strip_xssi(get(TRENDS_EXPLORE.format(req=urllib.parse.quote(req))))
    w = next((x for x in ex.get("widgets", []) if x.get("id") == "TIMESERIES"), None)
    if not w:
        return pd.Series(dtype=float)
    body = get(TRENDS_MULTILINE.format(req=urllib.parse.quote(json.dumps(w["request"])), tok=urllib.parse.quote(w["token"])))
    js = _strip_xssi(body)
    pts = js.get("default", {}).get("timelineData", [])
    s = pd.Series({pd.to_datetime(int(p["time"]), unit="s").normalize(): float((p.get("value") or [np.nan])[0]) for p in pts})
    return s.sort_index()


def asvi(svi: pd.Series) -> pd.Series:
    x = np.log(svi.clip(lower=1))
    return x - x.shift(1).rolling(8, min_periods=6).median()


def run_experiment90_report(svi: dict, px: dict, spy: pd.Series, diag: list, cost_bp: float = 10.0) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #90 — Google search interest ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L += [" ".join(diag), ""]
    a = {k: asvi(v) for k, v in svi.items() if len(v) > 50 and k in px}
    pv = {}
    # events
    L.append("## Search interest doubled (ASVI ≥ log 2) → next 1 / 4 weeks (stocks: vs SPY)")
    L.append("| group | events | 1 week | 4 weeks | any week 1 / 4 |")
    L.append("|---|--:|--:|--:|--:|")
    for grp in ("stocks", "crypto"):
        ev1, ev4, b1, b4 = [], [], [], []
        for k, s in a.items():
            is_c = k.endswith("-USD")
            if (grp == "crypto") != is_c:
                continue
            p = px[k]
            bench = None if is_c else spy
            for d in s.index:
                a0, a1, a4 = p.asof(d), p.asof(d + pd.Timedelta(days=7)), p.asof(d + pd.Timedelta(days=28))
                if d + pd.Timedelta(days=28) > p.index[-1] or not (np.isfinite(a0) and a0 > 0):
                    continue
                r1, r4 = a1 / a0 - 1, a4 / a0 - 1
                if bench is not None:
                    c0 = bench.asof(d)
                    r1 -= bench.asof(d + pd.Timedelta(days=7)) / c0 - 1
                    r4 -= bench.asof(d + pd.Timedelta(days=28)) / c0 - 1
                b1.append(r1); b4.append(r4)
                if s.get(d, np.nan) >= math.log(2):
                    ev1.append(r1); ev4.append(r4)
        if b1:
            for h, e, b in (("1 w", ev1, b1), ("4 w", ev4, b4)):
                if len(e) >= 10:
                    pv[(grp, "doubled", h)] = boot_p(np.array(b), len(e), float(np.mean(e)))
            L.append(f"| {grp} | {len(ev1)} | {100*np.mean(ev1):+.2f} % | {100*np.mean(ev4):+.2f} % | "
                     f"{100*np.mean(b1):+.2f} % / {100*np.mean(b4):+.2f} % |" if ev1 else f"| {grp} | 0 | — | — | — |")
    # weekly long/short, stocks
    L.append("")
    stocks = [k for k in a if not k.endswith("-USD")]
    if len(stocks) >= 15:
        weeks = sorted(set().union(*[set(a[k].dropna().index) for k in stocks]))
        g1, g4 = [], []
        for d in weeks:
            sc = {}
            for k in stocks:
                v = a[k].get(d, np.nan)
                p = px[k]
                if not np.isfinite(v) or d + pd.Timedelta(days=28) > p.index[-1]:
                    continue
                a0 = p.asof(d)
                if not (np.isfinite(a0) and a0 > 0):
                    continue
                c0 = spy.asof(d)
                r1 = p.asof(d + pd.Timedelta(days=7)) / a0 - 1 - (spy.asof(d + pd.Timedelta(days=7)) / c0 - 1)
                r4 = p.asof(d + pd.Timedelta(days=28)) / a0 - 1 - (spy.asof(d + pd.Timedelta(days=28)) / c0 - 1)
                sc[k] = (v, r1, r4)
            if len(sc) < 15:
                continue
            ser = pd.Series({k: x[0] for k, x in sc.items()}).sort_values()
            q = max(1, len(ser) // 5)
            lo, hi = ser.index[:q], ser.index[-q:]
            g1.append(np.mean([sc[k][1] for k in hi]) - np.mean([sc[k][1] for k in lo]))
            g4.append(np.mean([sc[k][2] for k in hi]) - np.mean([sc[k][2] for k in lo]))
        t = lambda x: float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(len(x))) if len(x) > 2 and np.std(x) > 0 else float("nan")
        if g1:
            net = np.array(g1) - 4 * cost_bp / 10_000
            L.append(f"## Weekly long top-20 % / short bottom-20 % ASVI (stocks, {len(g1)} weeks)")
            L.append(f"- 1 week: gross {100*np.mean(g1):+.3f} %/week (t {t(g1):+.2f}); net {100*net.mean():+.3f} %/week (t {t(net):+.2f})")
            L.append(f"- 4 weeks (overlapping, t overstated): {100*np.mean(g4):+.2f} % (t {t(g4):+.2f})")
            pv[("stocks", "long/short", "1 w")] = float(2 * (1 - 0.5 * (1 + math.erf(abs(t(g1)) / math.sqrt(2)))))
    adj = holm(pv)
    sig = [k for k, v in adj.items() if v < 0.05]
    L.append("")
    L.append(f"Cells tested: {len(pv)}; significant after Holm: {len(sig)}" + (" — " + "; ".join(" / ".join(k) for k in sig) if sig else "") + ".")
    L.append("Caveats: Google returns relative, rounded weekly values (0–100) for the last 5 years only; company "
             "names also catch product searches; few names because Google throttles automated requests.")
    return "\n".join(L)
