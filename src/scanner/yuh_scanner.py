"""
Yuh scanner — daily check of every Yuh-tradable asset with the rules that survived the research
(RESEARCH.md #44, #46/#47, #43, #50/#62, #78, #91). No forecasts, no price targets.

Per asset (prices: Yahoo daily closes):
  trend      close ≥ 200-day average                                   (#91: fastest useful rule)
  market     the asset's home index ≥ its 200-day average             (SPY for US/global/ETF/crypto
                                                                         context, SMI for .SW, DAX for .DE)
  momentum   12-1 month return, percentile among the stocks scanned    (#43)
  shares     change in share count over ~12 months (Yahoo, split-safe; #50/#64):
             ≤ −2 % buyback (plus), ≥ +5 % dilution (warning)
  young      first trading day < 3 years ago → IPO warning (#78)

Colour
  stock   🟢 market ok, trend ok, momentum top 30 %, no dilution, not a young IPO
          🔴 trend broken, or dilution ≥ 5 %
          🟡 everything else
  ETF     🟢 market ok and trend ok; 🔴 trend broken; else 🟡
  crypto  🟢 trend ok; 🔴 trend broken (only rule that survived for crypto, #89)

Messages are sent only when a colour CHANGES, plus a monthly list of the strongest 🟢 stocks.
Pure functions; the bot injects data fetching and sending.
"""
from __future__ import annotations
import csv
import math
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

GREEN, YELLOW, RED = "🟢", "🟡", "🔴"


@dataclass
class Asset:
    name: str
    yahoo: str
    kind: str          # 'stock' | 'etf' | 'crypto'


@dataclass
class Verdict:
    colour: str
    reasons: list = field(default_factory=list)
    info: dict = field(default_factory=dict)


def load_universe(path: str) -> list:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            y, k = (r.get("yahoo") or "").strip(), (r.get("type") or "stock").strip().lower()
            if y and k in ("stock", "etf", "crypto"):
                out.append(Asset((r.get("name") or y).strip(), y, k))
    return out


def home_index(a: Asset) -> str:
    if a.yahoo.endswith(".SW"):
        return "^SSMI"
    if a.yahoo.endswith(".DE"):
        return "^GDAXI"
    return "SPY"


def trend_ok(px: pd.Series) -> tuple:
    px = px.dropna()
    if len(px) < 200:
        return None, None
    sma = float(px.iloc[-200:].mean())
    last = float(px.iloc[-1])
    return last >= sma, last / sma - 1


def momentum_12_1(px: pd.Series) -> float:
    px = px.dropna()
    if len(px) < 260:
        return float("nan")
    return float(px.iloc[-22] / px.iloc[-253] - 1)


def latest_share_change(changes: pd.Series, today: pd.Timestamp, max_age_days: int = 456) -> float:
    """Most recent annual share-count change whose fiscal year ended within ~15 months."""
    if changes is None or len(changes) == 0:
        return float("nan")
    c = changes[changes.index >= today - pd.Timedelta(days=max_age_days)]
    return float(c.iloc[-1]) if len(c) else float("nan")


def judge(a: Asset, px: pd.Series, market_ok, mom_pct: float, share_ch: float, first_trade: pd.Timestamp | None,
          today: pd.Timestamp) -> Verdict:
    t_ok, dist = trend_ok(px)
    info = {"trend_dist": dist, "mom_pct": mom_pct, "share_ch": share_ch}
    if t_ok is None:
        return Verdict(YELLOW, ["zu wenig Kursdaten (< 200 Tage)"], info)
    reasons = []
    reasons.append(f"Trend {'intakt' if t_ok else 'gebrochen'} ({100*dist:+.0f} % zur 200-Tage-Linie)")
    if a.kind == "crypto":
        return Verdict(GREEN if t_ok else RED, reasons, info)
    if market_ok is not None:
        reasons.append("Marktlage " + ("ok" if market_ok else "schwach (Index unter 200-Tage-Linie)"))
    if a.kind == "etf":
        if not t_ok:
            return Verdict(RED, reasons, info)
        return Verdict(GREEN if market_ok else YELLOW, reasons, info)
    young = first_trade is not None and (today - first_trade).days < 3 * 365
    if young:
        reasons.append(f"Börsengang vor < 3 Jahren ({first_trade:%m.%Y}) — 73 % lagen nach 3 J. im Minus (#78)")
    if np.isfinite(share_ch):
        if share_ch >= 0.05:
            reasons.append(f"Verwässerung {100*share_ch:+.1f} % Aktien in 12 M")
        elif share_ch <= -0.02:
            reasons.append(f"Rückkauf {100*share_ch:+.1f} % Aktien in 12 M 👍")
    if np.isfinite(mom_pct):
        reasons.append(f"Momentum: stärker als {100*mom_pct:.0f} % der gescannten Aktien")
    dil = np.isfinite(share_ch) and share_ch >= 0.05
    if not t_ok or dil:
        return Verdict(RED, reasons, info)
    if market_ok and np.isfinite(mom_pct) and mom_pct >= 0.70 and not young:
        return Verdict(GREEN, reasons, info)
    return Verdict(YELLOW, reasons, info)


def percentiles(values: dict) -> dict:
    v = {k: x for k, x in values.items() if np.isfinite(x)}
    if not v:
        return {k: float("nan") for k in values}
    s = pd.Series(v).rank(pct=True)
    return {k: float(s.get(k, float("nan"))) for k in values}


def diff_states(prev: dict, new: dict) -> list:
    """[(yahoo, old colour or None, new colour)] for every change; first run reports nothing."""
    if not prev:
        return []
    return [(k, prev.get(k), c) for k, c in new.items() if prev.get(k) is not None and prev.get(k) != c]


def format_changes(changes: list, verdicts: dict, names: dict, day: pd.Timestamp, limit: int = 25) -> str:
    if not changes:
        return ""
    order = {RED: 0, GREEN: 1, YELLOW: 2}
    changes = sorted(changes, key=lambda x: order.get(x[2], 3))
    lines = [f"🔎 <b>Yuh-Scanner {day:%d.%m.%Y}</b> — {len(changes)} Änderung(en)", ""]
    for y, old, new in changes[:limit]:
        v = verdicts[y]
        lines.append(f"{old}→{new} <b>{names.get(y, y)}</b> ({y})")
        for r in v.reasons[:4]:
            lines.append(f"   • {r}")
    if len(changes) > limit:
        lines.append(f"… und {len(changes) - limit} weitere")
    lines.append("")
    lines.append("<i>Regeln aus der Forschung, keine Prognose. Im Einzelfall oft falsch; Vorteil nur über viele Fälle.</i>")
    return "\n".join(lines)


def format_monthly(verdicts: dict, names: dict, kinds: dict, day: pd.Timestamp, top: int = 10) -> str:
    g = [(y, v) for y, v in verdicts.items() if v.colour == GREEN and kinds.get(y) == "stock"]
    g.sort(key=lambda x: -(x[1].info.get("mom_pct") or 0))
    reds = sum(1 for v in verdicts.values() if v.colour == RED)
    lines = [f"📅 <b>Monatsliste {day:%m.%Y}</b> — {sum(1 for v in verdicts.values() if v.colour == GREEN)} 🟢, "
             f"{reds} 🔴 von {len(verdicts)} Titeln", "", "Stärkste 🟢-Aktien (Kandidaten, kein Kaufbefehl):"]
    for y, v in g[:top]:
        sc = v.info.get("share_ch")
        extra = f", Aktien {100*sc:+.1f} %" if sc is not None and np.isfinite(sc) else ""
        lines.append(f"• {names.get(y, y)} ({y}) — Momentum Top {100*(1 - v.info['mom_pct']):.0f} %{extra}")
    if not g:
        lines.append("• keine — Marktlage oder Trends erlauben derzeit keine Kauf-Kandidaten")
    lines.append("")
    lines.append("<i>Streuen (max. 5–10 % pro Titel), Kosten beachten, nicht alles auf einmal.</i>")
    return "\n".join(lines)


def scan(universe: list, prices: dict, shares: dict, first_trade: dict, index_px: dict, today: pd.Timestamp) -> dict:
    """→ {yahoo: Verdict}. prices/index_px: {symbol: Series}; shares: {yahoo: change series}."""
    mkt = {}
    for sym, s in index_px.items():
        ok, _ = trend_ok(s) if s is not None else (None, None)
        mkt[sym] = ok
    moms = {a.yahoo: momentum_12_1(prices[a.yahoo]) for a in universe if a.kind == "stock" and a.yahoo in prices}
    pct = percentiles(moms)
    out = {}
    for a in universe:
        px = prices.get(a.yahoo)
        if px is None or len(px) == 0:
            continue
        out[a.yahoo] = judge(a, px, mkt.get(home_index(a)), pct.get(a.yahoo, float("nan")),
                             latest_share_change(shares.get(a.yahoo), today), first_trade.get(a.yahoo), today)
    return out


def summary_markdown(verdicts: dict, names: dict, kinds: dict, day: pd.Timestamp) -> str:
    rows = sorted(verdicts.items(), key=lambda x: ({GREEN: 0, YELLOW: 1, RED: 2}[x[1].colour], names.get(x[0], x[0])))
    L = [f"# Yuh-Scanner {day:%Y-%m-%d}", "",
         f"{sum(v.colour == GREEN for v in verdicts.values())} 🟢 · {sum(v.colour == YELLOW for v in verdicts.values())} 🟡 · "
         f"{sum(v.colour == RED for v in verdicts.values())} 🔴 of {len(verdicts)}", "",
         "| | name | symbol | type | reasons |", "|---|---|---|---|---|"]
    for y, v in rows:
        L.append(f"| {v.colour} | {names.get(y, y)} | {y} | {kinds.get(y, '')} | {'; '.join(v.reasons)} |")
    return "\n".join(L)


# ── universe from the public Yuh lists (neo-banques.ch, checked on the server) ─────────────

STOCKS_URL = "https://neo-banques.ch/en/yuh-stocks-list.htm"
ETF_URL = "https://neo-banques.ch/en/yuh-etf.htm"
EXCHANGE_SUFFIX = {"SIX": [".SW"], "XETR": [".DE"], "XETRA": [".DE"], "NYSE": [""], "NASDAQ": [""], "AMEX": [""],
                   "EURONEXT": [".PA", ".AS", ".BR", ".LS"], "LSE": [".L"], "MIL": [".MI"], "BME": [".MC"],
                   "VIE": [".VI"], "OMX": [".ST", ".CO", ".HE"], "BIT": [".MI"]}
# Renamed / moved listings (list symbol → Yahoo symbols to try first)
ALIASES = {("NYSE", "SQ"): ["XYZ"], ("SIX", "SQ"): ["SQN.SW"], ("BME", "SANT"): ["SAN.MC"], ("XETR", "DPW"): ["DHL.DE"],
           ("SIX", "DUFN"): ["AVOL.SW"], ("NYSE", "BP."): ["BP"], ("SIX", "BALN"): ["HBAN.SW"], ("SIX", "HELN"): ["HBAN.SW"],
           ("NYSE", "GPS"): ["GAP"], ("NASDAQ", "BRBY"): ["BRBY.L"], ("NYSE", "AML"): ["AML.L"]}
# Crypto: a selection of large coins; Yuh's own list is in the app (not public as a table).
CRYPTO = [("Bitcoin", "BTC-USD"), ("Ethereum", "ETH-USD"), ("XRP", "XRP-USD"), ("Solana", "SOL-USD"),
          ("Cardano", "ADA-USD"), ("Polkadot", "DOT-USD"), ("Chainlink", "LINK-USD"), ("Avalanche", "AVAX-USD"),
          ("Dogecoin", "DOGE-USD"), ("Litecoin", "LTC-USD"), ("Bitcoin Cash", "BCH-USD"), ("Stellar", "XLM-USD"),
          ("Uniswap", "UNI7083-USD"), ("Aave", "AAVE-USD"), ("Algorand", "ALGO-USD")]


def _cells(table_html: str) -> list:
    import html as _h
    import re as _re
    rows = _re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=_re.S | _re.I)
    return [[_h.unescape(_re.sub(r"<[^>]+>", "", c)).strip()
             for c in _re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, flags=_re.S | _re.I)] for r in rows]


def _first_table(page: str) -> list:
    import re as _re
    m = _re.search(r"<table.*?</table>", page, flags=_re.S | _re.I)
    return _cells(m.group(0)) if m else []


def parse_stock_list(page: str) -> list:
    """→ [(name, exchange, symbol, currency)] from the stock table (header: Company Name / Stock Market / Symbol / Currency)."""
    rows = _first_table(page)
    if not rows:
        return []
    head = [h.lower() for h in rows[0]]
    try:
        i_n = next(i for i, h in enumerate(head) if "company" in h or "firma" in h)
        i_x = next(i for i, h in enumerate(head) if "market" in h or "börse" in h)
        i_s = next(i for i, h in enumerate(head) if "symbol" in h)
        i_c = next(i for i, h in enumerate(head) if "currency" in h or "währung" in h)
    except StopIteration:
        return []
    out = []
    for r in rows[1:]:
        if len(r) > max(i_n, i_x, i_s, i_c) and r[i_s]:
            out.append((r[i_n], r[i_x].upper(), r[i_s].upper(), r[i_c].upper()))
    return out


def parse_etf_list(page: str) -> list:
    """→ [(name, ticker, isin)] from the ETF table (header: … ETF Name / Ticker / ISIN / TER)."""
    rows = _first_table(page)
    if not rows:
        return []
    head = [h.lower() for h in rows[0]]
    try:
        i_n = next(i for i, h in enumerate(head) if "etf name" in h or h == "name")
        i_t = next(i for i, h in enumerate(head) if "ticker" in h)
        i_i = next(i for i, h in enumerate(head) if "isin" in h)
    except StopIteration:
        return []
    return [(r[i_n], r[i_t].upper(), r[i_i].upper()) for r in rows[1:] if len(r) > max(i_n, i_t, i_i) and r[i_t]]


def stock_candidates(exchange: str, symbol: str) -> list:
    base = symbol.rstrip(".").replace(".", "-").replace("/", "-").replace(" ", "-")
    return ALIASES.get((exchange, symbol), []) + [base + s for s in EXCHANGE_SUFFIX.get(exchange, ["", ".SW", ".DE", ".PA", ".AS"])]


def etf_candidates(ticker: str) -> list:
    base = ticker.split(".")[0]
    return [base + ".SW", base, base + ".DE", base + ".L"]


def build_universe(stock_page: str, etf_page: str, valid) -> tuple:
    """valid(symbol) → bool (has recent prices). → (rows [name, yahoo, type], skipped [name])."""
    rows, skipped, seen = [], [], set()
    for name, ex, sym, _ in parse_stock_list(stock_page):
        hit = next((c for c in stock_candidates(ex, sym) if valid(c)), None)
        if hit and hit not in seen:
            rows.append((name, hit, "stock")); seen.add(hit)
        elif not hit:
            skipped.append(f"{name} ({ex}:{sym})")
    for name, t, _ in parse_etf_list(etf_page):
        hit = next((c for c in etf_candidates(t) if valid(c)), None)
        if hit and hit not in seen:
            rows.append((name, hit, "etf")); seen.add(hit)
        elif not hit:
            skipped.append(f"{name} ({t})")
    for name, y in CRYPTO:
        if y not in seen and valid(y):
            rows.append((name, y, "crypto")); seen.add(y)
    return rows, skipped


def write_universe(path: str, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "yahoo", "type"])
        w.writerows(rows)
