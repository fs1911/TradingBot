"""
Experiment #87 — do news predict prices? (news tone and attention, GDELT 2017 →)

Data (first attempt): GDELT DOC 2.0 API — throttled to ~1 name/hour, so the run uses Alpaca/Benzinga
(symbol-tagged, 2015 →, US stocks + crypto; tone from pre-registered word lists). GDELT: (free, worldwide, machine-
translated, since 2017): per company query a daily timeline of article volume and average
tone (−100 … +100, typically −5 … +5). Prices: Yahoo. Universe: ~90 well-known US, Swiss and
German companies plus 6 cryptocurrencies (names chosen to be unambiguous).

Pre-registered (fixed before looking at outcomes):
  Daily tone z = (tone − mean of the previous 60 days) / std (≥ 30 days, days with < 5 articles
  excluded); attention z = same on log(1 + articles).
  Events (cool-down 20 trading days per stock and type):
    E1 tone shock positive    tone z ≥ +2
    E2 tone shock negative    tone z ≤ −2
    E3 attention spike        attention z ≥ +3
    E4 spike + negative tone  attention z ≥ +3 and tone z ≤ −1
    E5 spike + positive tone  attention z ≥ +3 and tone z ≥ +1
  Entry: close of the first trading day AFTER the news day (UTC) — what a reader could do.
  Outcome: excess return vs benchmark (US → SPY, .SW → SMI, .DE → DAX, crypto → none) after
  1, 5, 20 trading days; also the move already made (close before the news day → entry).
  Test: random-date bootstrap from all stock-days of the same group; Holm over all cells.
  Portfolio: each week long the 20 % with the most positive 5-day tone z, short the 20 % most
  negative, hold one week; gross and net of 10 bp per side.
Pure, injected for CI (`get` is a callable(url) → str).
"""
from __future__ import annotations
import json
import urllib.parse
import numpy as np
import pandas as pd

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode={mode}&format=json&startdatetime={s}&enddatetime={e}"
HORIZONS = {"1 d": 1, "5 d": 5, "20 d": 20}

UNIVERSE = [  # (GDELT query, Yahoo symbol)
    ('"Microsoft"', "MSFT"), ('"Nvidia"', "NVDA"), ('"Tesla"', "TSLA"), ('"Netflix"', "NFLX"),
    ('"Boeing"', "BA"), ('"Pfizer"', "PFE"), ('"Moderna"', "MRNA"), ('"Johnson & Johnson"', "JNJ"),
    ('"ExxonMobil"', "XOM"), ('"Chevron"', "CVX"), ('"JPMorgan"', "JPM"), ('"Goldman Sachs"', "GS"),
    ('"Morgan Stanley"', "MS"), ('"Citigroup"', "C"), ('"Wells Fargo"', "WFC"), ('"Walmart"', "WMT"),
    ('"Costco"', "COST"), ('"Home Depot"', "HD"), ('"McDonald\'s"', "MCD"), ('"Starbucks"', "SBUX"),
    ('"Nike"', "NKE"), ('"Disney"', "DIS"), ('"Intel"', "INTC"), ('"Advanced Micro Devices"', "AMD"),
    ('"Qualcomm"', "QCOM"), ('"Broadcom"', "AVGO"), ('"Cisco"', "CSCO"), ('"IBM"', "IBM"),
    ('"Salesforce"', "CRM"), ('"Adobe"', "ADBE"), ('"PayPal"', "PYPL"), ('"Uber"', "UBER"),
    ('"Airbnb"', "ABNB"), ('"Coinbase"', "COIN"), ('"Palantir"', "PLTR"), ('"Eli Lilly"', "LLY"),
    ('"AbbVie"', "ABBV"), ('"Amgen"', "AMGN"), ('"UnitedHealth"', "UNH"), ('"Caterpillar"', "CAT"),
    ('"General Motors"', "GM"), ('"Ford Motor"', "F"), ('"Lockheed Martin"', "LMT"),
    ('"Procter & Gamble"', "PG"), ('"Coca-Cola"', "KO"), ('"PepsiCo"', "PEP"),
    ('"Berkshire Hathaway"', "BRK-B"), ('"Mastercard"', "MA"), ('"American Express"', "AXP"),
    ('"Verizon"', "VZ"), ('"Comcast"', "CMCSA"), ('"Google"', "GOOGL"), ('("Facebook" OR "Meta Platforms")', "META"),
    ('"Amazon.com"', "AMZN"), ('"Oracle"', "ORCL"), ('"Starlink" OR "SpaceX"', None),
    ('"Nestle"', "NESN.SW"), ('"Novartis"', "NOVN.SW"), ('"Roche"', "ROG.SW"), ('"UBS"', "UBSG.SW"),
    ('"Zurich Insurance"', "ZURN.SW"), ('"ABB"', "ABBN.SW"), ('"Richemont"', "CFR.SW"), ('"Swatch"', "UHR.SW"),
    ('"Lonza"', "LONN.SW"), ('"Sika"', "SIKA.SW"), ('"Givaudan"', "GIVN.SW"), ('"Holcim"', "HOLN.SW"),
    ('"Swisscom"', "SCMN.SW"), ('"Swiss Re"', "SREN.SW"), ('"Logitech"', "LOGN.SW"), ('"Geberit"', "GEBN.SW"),
    ('"Partners Group"', "PGHN.SW"), ('"Alcon"', "ALC.SW"), ('"Sonova"', "SOON.SW"), ('"Kuehne+Nagel"', "KNIN.SW"),
    ('"Straumann"', "STMN.SW"), ('"Temenos"', "TEMN.SW"), ('"Idorsia"', "IDIA.SW"), ('"Julius Baer"', "BAER.SW"),
    ('"Schindler"', "SCHP.SW"), ('"Siemens"', "SIE.DE"), ('"SAP"', "SAP.DE"), ('"Volkswagen"', "VOW3.DE"),
    ('"BMW"', "BMW.DE"), ('"Mercedes-Benz"', "MBG.DE"), ('"Allianz"', "ALV.DE"), ('"Deutsche Bank"', "DBK.DE"),
    ('"BASF"', "BAS.DE"), ('"Bayer"', "BAYN.DE"), ('"Adidas"', "ADS.DE"), ('"Lufthansa"', "LHA.DE"),
    ('"Infineon"', "IFX.DE"), ('"Rheinmetall"', "RHM.DE"), ('"Zalando"', "ZAL.DE"),
    ('"Bitcoin"', "BTC-USD"), ('"Ethereum"', "ETH-USD"), ('("XRP" OR "Ripple")', "XRP-USD"),
    ('"Solana"', "SOL-USD"), ('"Dogecoin"', "DOGE-USD"), ('"Cardano"', "ADA-USD"),
]
UNIVERSE = [(q, s) for q, s in UNIVERSE if s]


def _interleave(items):
    """Round-robin over US / CH / DE / crypto so that a run cut short by the time budget stays balanced."""
    groups = {"us": [], "ch": [], "de": [], "cr": []}
    for q, sym in items:
        k = "cr" if sym.endswith("-USD") else "ch" if sym.endswith(".SW") else "de" if sym.endswith(".DE") else "us"
        groups[k].append((q, sym))
    out, i = [], 0
    while any(groups.values()):
        for k in ("us", "ch", "us", "de", "cr"):
            if groups[k]:
                out.append(groups[k].pop(0))
    return out


UNIVERSE = _interleave(UNIVERSE)


def benchmark_for(sym: str) -> str | None:
    if sym.endswith("-USD"):
        return None
    if sym.endswith(".SW"):
        return "^SSMI"
    if sym.endswith(".DE"):
        return "^GDAXI"
    return "SPY"


def group_of(sym: str) -> str:
    return "crypto" if sym.endswith("-USD") else "stocks"


def parse_timeline(body: str) -> pd.Series:
    """GDELT timeline JSON → daily Series (first series; value = tone or article count)."""
    js = json.loads(body) if body and body.strip().startswith("{") else {}
    tl = js.get("timeline") or []
    if not tl:
        return pd.Series(dtype=float)
    data = tl[0].get("data") or []
    if not data:
        return pd.Series(dtype=float)
    d = pd.to_datetime([x.get("date") for x in data], format="%Y%m%dT%H%M%SZ", errors="coerce", utc=True)
    v = pd.to_numeric(pd.Series([x.get("value") for x in data]), errors="coerce").to_numpy()
    s = pd.Series(v, index=d.tz_convert(None)).dropna()
    s = s[s.index.notna()]
    return s


def fetch_series(get, query: str, mode: str, start: pd.Timestamp, end: pd.Timestamp, sleep: float = 15.0,
                 log=None, stats: dict | None = None, backoff: float = 60.0) -> pd.Series:
    """Whole range in one call; if the API returns coarser than daily points, retry per year."""
    import time as _t
    q = urllib.parse.quote(query)
    def one(a, b):
        url = GDELT.format(q=q, mode=mode, s=f"{a:%Y%m%d%H%M%S}", e=f"{b:%Y%m%d%H%M%S}")
        for attempt in range(4):  # GDELT answers 429 when called too often → back off and retry
            if stats is not None:
                stats["calls"] = stats.get("calls", 0) + 1
            try:
                body = get(url)
                r = parse_timeline(body)
                if stats is not None:
                    stats["points"] = stats.get("points", 0) + len(r)
                    if len(r) == 0:
                        stats["empty"] = stats.get("empty", 0) + 1
                        stats.setdefault("empty_sample", (body or "")[:160])
                _t.sleep(sleep)
                return r
            except Exception as e:
                if stats is not None:
                    stats["errors"] = stats.get("errors", 0) + 1
                    stats["last_error"] = repr(e)[:160]
                if log:
                    log(f"#87 {query} {mode} {a:%Y}: {repr(e)[:80]}")
                if "429" in repr(e) and attempt < 3:
                    if stats is not None:
                        stats["retries"] = stats.get("retries", 0) + 1
                    _t.sleep(backoff * (2 ** attempt))
                    continue
                _t.sleep(sleep)
                return None
        return None
    s = one(start, end)
    span_days = (end - start).days
    if s is None:  # request failed even after retries → do not multiply the load with chunk requests
        return pd.Series(dtype=float)
    if 0 < len(s) < 0.5 * span_days:  # answered, but coarser than daily → yearly chunks
        parts = []
        for y in range(start.year, end.year + 1):
            a, b = max(start, pd.Timestamp(y, 1, 1)), min(end, pd.Timestamp(y, 12, 31, 23, 59, 59))
            parts.append(one(a, b))
        parts = [p for p in parts if p is not None and len(p)]
        s = pd.concat(parts) if parts else s
    if len(s) == 0:
        return s
    agg = "sum" if mode == "timelinevolraw" else "mean"
    return s.groupby(s.index.normalize()).agg(agg)


def zscore(x: pd.Series, window: int = 60, min_obs: int = 30) -> pd.Series:
    m = x.shift(1).rolling(window, min_periods=min_obs).mean()
    s = x.shift(1).rolling(window, min_periods=min_obs).std()
    return (x - m) / s.replace(0, np.nan)


def signals(tone: pd.Series, count: pd.Series, min_articles: int = 5) -> pd.DataFrame:
    idx = count.index.union(tone.index)
    c = count.reindex(idx).fillna(0.0)
    t = tone.reindex(idx).where(c >= min_articles)
    return pd.DataFrame({"tone_z": zscore(t.dropna()).reindex(idx), "att_z": zscore(np.log1p(c)), "articles": c})


EVENTS = {
    "E1 tone shock +": lambda s: s["tone_z"] >= 2,
    "E2 tone shock −": lambda s: s["tone_z"] <= -2,
    "E3 attention spike": lambda s: s["att_z"] >= 3,
    "E4 spike + negative tone": lambda s: (s["att_z"] >= 3) & (s["tone_z"] <= -1),
    "E5 spike + positive tone": lambda s: (s["att_z"] >= 3) & (s["tone_z"] >= 1),
}


def event_days(mask: pd.Series, px_index: pd.DatetimeIndex, cooldown: int = 20) -> list:
    """News day d → entry = first trading day strictly after d; enforce a cool-down in trading days."""
    out, last = [], -10 ** 9
    for d in mask[mask.fillna(False)].index:
        k = px_index.searchsorted(d, side="right")
        if k >= len(px_index):
            break
        if k - last >= cooldown:
            out.append(k); last = k
    return out


def excess_series(px: pd.Series, bench: pd.Series | None) -> dict:
    """Forward excess returns per horizon from each trading day's close (aligned to px index)."""
    v = px.to_numpy(dtype=float)
    b = bench.reindex(px.index).ffill().to_numpy(dtype=float) if bench is not None else None
    out = {}
    for h, n in HORIZONS.items():
        r = np.full(len(v), np.nan)
        r[:-n] = v[n:] / v[:-n] - 1
        if b is not None:
            rb = np.full(len(v), np.nan)
            rb[:-n] = b[n:] / b[:-n] - 1
            r = r - rb
        out[h] = r
    pre = np.full(len(v), np.nan)  # close two days before entry → entry (move already made)
    pre[2:] = v[2:] / v[:-2] - 1
    if b is not None:
        pb = np.full(len(v), np.nan); pb[2:] = b[2:] / b[:-2] - 1
        pre = pre - pb
    out["already"] = pre
    return out


def boot_p(base: np.ndarray, n: int, observed: float, reps: int = 4000, seed: int = 87) -> float:
    base = base[np.isfinite(base)]
    if n < 10 or len(base) < n:
        return float("nan")
    rng = np.random.default_rng(seed)
    m = base[rng.integers(0, len(base), size=(reps, n))].mean(axis=1)
    c = m.mean()
    return float((np.abs(m - c) >= abs(observed - c)).mean())


def holm(p: dict) -> dict:
    items = sorted((v, k) for k, v in p.items() if np.isfinite(v))
    m, out, run = len(items), {}, 0.0
    for i, (v, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v)); out[k] = run
    return out


def weekly_long_short(sig: dict, px: dict, bench: dict, cost_bp: float = 10.0) -> pd.Series:
    """Fridays: rank stocks by mean tone z of the last 5 calendar days; long top 20 %, short bottom
    20 %; next-week excess returns. Returns weekly net return series (gross in .attrs)."""
    fridays = pd.date_range("2017-03-03", pd.Timestamp.today().normalize(), freq="W-FRI")
    rows, gross = [], []
    for f0, f1 in zip(fridays[:-1], fridays[1:]):
        sc = {}
        for sym, s in sig.items():
            if group_of(sym) != "stocks":
                continue
            w = s["tone_z"].loc[f0 - pd.Timedelta(days=4):f0].dropna()
            p = px.get(sym)
            if len(w) == 0 or p is None:
                continue
            a, b = p.asof(f0), p.asof(f1)
            bb = bench.get(benchmark_for(sym))
            if not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
                continue
            r = b / a - 1
            if bb is not None:
                x0, x1 = bb.asof(f0), bb.asof(f1)
                if np.isfinite(x0) and np.isfinite(x1) and x0 > 0:
                    r -= x1 / x0 - 1
            sc[sym] = (float(w.mean()), r)
        if len(sc) < 20:
            continue
        ser = pd.Series({k: v[0] for k, v in sc.items()}).sort_values()
        k = max(1, len(ser) // 5)
        lo, hi = ser.index[:k], ser.index[-k:]
        g = np.mean([sc[x][1] for x in hi]) - np.mean([sc[x][1] for x in lo])
        gross.append(g)
        rows.append((f1, g - 4 * cost_bp / 10_000))  # both legs in and out
    out = pd.Series(dict(rows))
    out.attrs["gross"] = pd.Series(gross, index=out.index) if len(gross) == len(out) else None
    return out


def run_experiment87_report(sig: dict, px: dict, bench: dict, diag: list) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #87 — news tone and attention ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"Companies/coins with news + prices: {len(sig)}. " + (" ".join(diag[:6]) if diag else ""))
    L.append("Entry = close of the first trading day AFTER the news day. 'already' = move from two closes before "
             "entry to entry (what happened before a reader could act). p = random-date bootstrap; Holm over all cells.")
    L.append("")
    pv, cells = {}, []
    for grp in ("stocks", "crypto"):
        syms = [s for s in sig if group_of(s) == grp and s in px]
        if not syms:
            continue
        ex = {s: excess_series(px[s], bench.get(benchmark_for(s))) for s in syms}
        base = {h: np.concatenate([ex[s][h] for s in syms]) for h in list(HORIZONS) + ["already"]}
        for en, rule in EVENTS.items():
            ks = {s: event_days(rule(sig[s]), px[s].index) for s in syms}
            n = sum(len(v) for v in ks.values())
            row = {"group": grp, "event": en, "n": n}
            for h in list(HORIZONS) + ["already"]:
                vals = np.concatenate([ex[s][h][ks[s]] for s in syms if ks[s]]) if n else np.array([])
                vals = vals[np.isfinite(vals)]
                row[h] = (float(vals.mean()) if len(vals) else np.nan, float(np.median(vals)) if len(vals) else np.nan,
                          float((vals > 0).mean()) if len(vals) else np.nan, len(vals))
                if h in HORIZONS and len(vals) >= 10:
                    pv[(grp, en, h)] = boot_p(base[h], len(vals), float(vals.mean()))
            row["base"] = {h: float(np.nanmean(base[h])) for h in HORIZONS}
            cells.append(row)
    adj = holm(pv)
    for grp in ("stocks", "crypto"):
        rows = [c for c in cells if c["group"] == grp]
        if not rows:
            continue
        L.append(f"## {grp}")
        L.append("| event | n | already moved | " + " | ".join(f"{h} mean / median / >0 (p, Holm)" for h in HORIZONS) + " |")
        L.append("|---|--:|--:|" + "--:|" * len(HORIZONS))
        L.append("| *any day* | | | " + " | ".join(f"{100*rows[0]['base'][h]:+.2f} %" for h in HORIZONS) + " |")
        for c in rows:
            cs = []
            for h in HORIZONS:
                m, md, pos, k = c[h]
                p, q = pv.get((grp, c["event"], h), np.nan), adj.get((grp, c["event"], h), np.nan)
                cs.append(f"{100*m:+.2f} % / {100*md:+.2f} % / {100*pos:.0f} % ({p:.3f}, {q:.3f})" if k else "—")
            a = c["already"]
            L.append(f"| {c['event']} | {c['n']:,} | {100*a[0]:+.2f} % | " + " | ".join(cs) + " |")
        L.append("")
    ls = weekly_long_short(sig, px, bench)
    if len(ls) > 30:
        g = ls.attrs.get("gross")
        t = lambda x: float(x.mean() / x.std() * np.sqrt(len(x))) if x.std() > 0 else float("nan")
        L.append(f"## Weekly long/short by 5-day tone (stocks, {len(ls)} weeks)")
        if g is not None:
            L.append(f"- gross: {100*g.mean():+.3f} %/week (t {t(g):+.2f}) ≈ {100*g.mean()*52:+.1f} %/yr")
        L.append(f"- net of 10 bp per side: {100*ls.mean():+.3f} %/week (t {t(ls):+.2f}) ≈ {100*ls.mean()*52:+.1f} %/yr")
        L.append("")
    sig_cells = [k for k, v in adj.items() if v < 0.05]
    L.append(f"Cells tested: {len(pv)}; significant after Holm: {len(sig_cells)}"
             + (" — " + "; ".join(f"{a}/{b}/{c}" for a, b, c in sig_cells) if sig_cells else "") + ".")
    L.append("Caveats: GDELT tone is machine-scored and translated; company-name queries catch some unrelated "
             "articles (noise lowers power); events cluster in market-wide news days.")
    return "\n".join(L)


# ── Alpaca / Benzinga news (symbol-tagged, 2015 →) — used because GDELT throttles to ~0 ──────

ALPACA_NEWS = "https://data.alpaca.markets/v1beta1/news"
# Pre-registered finance word lists (in the spirit of Loughran–McDonald; fixed before the run).
POS_WORDS = frozenset("""beat beats beating exceed exceeds exceeded exceeding record upgrade upgraded upgrades
outperform outperforms raise raises raised raising boost boosts boosted surge surges surged soar soars soared
rally rallies rallied jump jumps jumped gain gains gained strong stronger strongest growth grow grows grew
profit profitable profits win wins won approval approved approves breakthrough expand expands expanded expansion
buyback buybacks dividend hike hikes hiked optimistic bullish upbeat robust accelerate accelerates accelerated
partnership launch launches launched tops topped""".split())
NEG_WORDS = frozenset("""miss misses missed missing downgrade downgraded downgrades underperform underperforms
cut cuts cutting lower lowers lowered plunge plunges plunged plummet plummets plummeted slump slumps slumped
drop drops dropped fall falls fell tumble tumbles tumbled sink sinks sank weak weaker weakest loss losses lose
loses lost decline declines declined lawsuit lawsuits sue sues sued probe probes investigation investigations
recall recalls recalled fraud fine fined fines penalty layoff layoffs halt halts halted delay delays delayed
warning warns warned bearish pessimistic concern concerns risk risks bankruptcy default defaults downturn
resign resigns resigned scandal breach hack hacked""".split())


def text_tone(text: str) -> float:
    import re
    w = re.findall(r"[a-z]+", (text or "").lower())
    p = sum(1 for x in w if x in POS_WORDS)
    n = sum(1 for x in w if x in NEG_WORDS)
    return (p - n) / (p + n + 1.0)


def alpaca_symbol(sym: str) -> str:
    return sym.replace("-USD", "USD") if sym.endswith("-USD") else sym


def fetch_alpaca_news(get_json, sym: str, start: str, end: str, max_pages: int = 600, sleep: float = 0.35,
                      stats: dict | None = None) -> pd.DataFrame:
    """All articles tagged with `sym` → DataFrame [ts (UTC), tone]. get_json(url) → dict."""
    import time as _t
    rows, token = [], None
    for _ in range(max_pages):
        url = (f"{ALPACA_NEWS}?symbols={urllib.parse.quote(alpaca_symbol(sym))}&start={start}&end={end}"
               f"&limit=50&sort=asc" + (f"&page_token={urllib.parse.quote(token)}" if token else ""))
        try:
            js = get_json(url)
        except Exception as e:
            if stats is not None:
                stats["errors"] = stats.get("errors", 0) + 1
                stats["last_error"] = repr(e)[:160]
            _t.sleep(5)
            continue
        if stats is not None:
            stats["calls"] = stats.get("calls", 0) + 1
        for a in js.get("news") or []:
            rows.append((a.get("created_at"), text_tone(f"{a.get('headline', '')} {a.get('summary', '')}")))
        token = js.get("next_page_token")
        _t.sleep(sleep)
        if not token:
            break
    if not rows:
        return pd.DataFrame(columns=["ts", "tone"])
    df = pd.DataFrame(rows, columns=["ts", "tone"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df.dropna()


def daily_from_articles(df: pd.DataFrame, start: str, end: str) -> tuple:
    """Articles → (daily mean tone, daily article count) on a full calendar index; the news day is the
    New York calendar date of publication."""
    idx = pd.date_range(pd.Timestamp(start).tz_localize(None).normalize(), pd.Timestamp(end).tz_localize(None).normalize(), freq="D")
    if df.empty:
        return pd.Series(dtype=float), pd.Series(0.0, index=idx)
    day = df["ts"].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    g = df.groupby(day)["tone"]
    return g.mean().reindex(idx), g.size().astype(float).reindex(idx).fillna(0.0)
