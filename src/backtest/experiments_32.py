"""
Experiment #32 — decades of history (Stooq / Yahoo) for the two open questions.

Everything so far ran on ≤ ~8 years of broker data (stocks from ~2020). That misses
every big crash that matters: 1987, the dot-com bust (Nasdaq −78%), 2008 (S&P −57%),
and Japan's 1989 top (Nikkei −80%, 34 years to a new high). #31 showed the drawdown
signal cannot be judged on ~15 episodes. This experiment pulls free multi-decade daily
index history and re-tests:

  A. DEEP-DRAWDOWN SIGNAL at −20% / −35% / −50%: independent episodes, excess over the
     ordinary 90d return, non-overlapping t-test, both halves, DCA vs dip-reserve.
  B. TREND FILTERS across many cycles: 200d-SMA filter and 12-month time-series momentum
     vs buy & hold — CAGR, Sharpe, max drawdown, and full rigor on the DIFFERENTIAL
     (does timing beat simply holding?).

Price indices (no dividends) and 0% cash — conservative for the timing rules and noted
in the report. Network fetch is isolated in `fetch_long_history` with a hard timeout;
all analysis is pure and injected for CI.
"""
from __future__ import annotations
import json
from typing import Callable, Optional
import numpy as np
import pandas as pd

from .rigor import full_rigor, annualized_sharpe
from .experiments_30 import drawdown_from_ath
from .experiments_31 import zone_stats, dca_vs_dip_reserve

THRESHOLDS = (-0.20, -0.35, -0.50)


# ---------------------------------------------------------------- data (network)

def parse_stooq_csv(text: str) -> pd.Series:
    """Stooq daily CSV (Date,Open,High,Low,Close,Volume) → close Series."""
    if not text or not text.lstrip().lower().startswith("date"):
        return pd.Series(dtype=float)
    rows = [ln.split(",") for ln in text.strip().splitlines()[1:]]
    data = {}
    for r in rows:
        if len(r) >= 5:
            try:
                data[pd.Timestamp(r[0])] = float(r[4])
            except (ValueError, TypeError):
                continue
    return pd.Series(data, dtype=float).sort_index()


def parse_yahoo_json(text: str) -> pd.Series:
    """Yahoo chart API JSON → (adjusted) close Series indexed by date."""
    try:
        res = json.loads(text)["chart"]["result"][0]
        ts = res["timestamp"]
        ind = res["indicators"]
        closes = (ind.get("adjclose") or [{}])[0].get("adjclose") or ind["quote"][0]["close"]
    except (KeyError, IndexError, TypeError, ValueError):
        return pd.Series(dtype=float)
    idx = pd.to_datetime(ts, unit="s").normalize()
    s = pd.Series(closes, index=idx, dtype=float).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def fetch_long_history(stooq_sym: str, yahoo_sym: str, timeout: int = 20):
    """Try Stooq, then Yahoo. Returns (close Series, source). Hard timeout per call."""
    import urllib.request
    import urllib.parse
    import time as _t
    headers = {"User-Agent": "Mozilla/5.0 (research; TradingBot)"}
    if stooq_sym:
        try:
            url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(stooq_sym)}&i=d"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                s = parse_stooq_csv(r.read().decode("utf-8", "replace"))
            if len(s) > 1000:
                return s, "stooq"
        except Exception:
            pass
    if yahoo_sym:
        try:
            url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
                   f"{urllib.parse.quote(yahoo_sym)}?period1=0&period2={int(_t.time())}"
                   f"&interval=1d&events=history")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                s = parse_yahoo_json(r.read().decode("utf-8", "replace"))
            if len(s) > 1000:
                return s, "yahoo"
        except Exception:
            pass
    return pd.Series(dtype=float), "none"


# ---------------------------------------------------------------- analysis (pure)

def perf(returns: pd.Series) -> dict:
    r = returns.dropna()
    if len(r) < 50:
        return {"cagr": float("nan"), "sharpe": float("nan"), "maxdd": float("nan")}
    eq = (1.0 + r).cumprod()
    cagr = float(eq.iloc[-1] ** (252.0 / len(r)) - 1.0)
    return {"cagr": cagr, "sharpe": annualized_sharpe(r),
            "maxdd": float((eq / eq.cummax() - 1.0).min())}


def sma_filter_returns(px: pd.Series, window: int = 200, cost_bps: float = 5.0) -> pd.Series:
    """Hold when yesterday's close > its SMA(window), else cash (0%)."""
    ret = px.pct_change().fillna(0.0)
    pos = (px > px.rolling(window).mean()).astype(float).shift(1).fillna(0.0)
    return ret * pos - pos.diff().abs().fillna(0.0) * cost_bps / 1e4


def tsmom_returns(px: pd.Series, lookback: int = 252, cost_bps: float = 5.0) -> pd.Series:
    """Hold when the trailing `lookback`-day return is positive, else cash."""
    ret = px.pct_change().fillna(0.0)
    pos = ((px / px.shift(lookback) - 1.0) > 0).astype(float).shift(1).fillna(0.0)
    return ret * pos - pos.diff().abs().fillna(0.0) * cost_bps / 1e4


def trend_comparison(px: pd.Series, n_trials: int = 100) -> dict:
    """B&H vs SMA200 vs 12m TSMOM on the common post-warm-up window, plus rigor on the
    SMA200-minus-B&H differential."""
    px = px.dropna().sort_index()
    warm = 260
    if len(px) < warm + 500:
        return {"insufficient": True}
    bh = px.pct_change().fillna(0.0).iloc[warm:]
    sma = sma_filter_returns(px).iloc[warm:]
    ts = tsmom_returns(px).iloc[warm:]
    res = full_rigor("SMA200 − B&H", sma - bh, n_trials)
    return {"bh": perf(bh), "sma": perf(sma), "ts": perf(ts), "rigor": res}


def run_experiment32_report(fetch: Callable[[dict], tuple], assets: list,
                            horizon: int = 90) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #32 — decades of history: drawdown signal & trend filters "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append("Free multi-decade daily index data (Stooq → Yahoo fallback). Price "
                 "indices without dividends, cash at 0% — conservative for timing rules.")
    lines.append("")

    loaded = []
    lines.append("## Data")
    lines.append("| Asset | source | from | years |")
    lines.append("|---|---|---|--:|")
    for a in assets:
        try:
            px, src = fetch(a)
        except Exception:
            px, src = pd.Series(dtype=float), "error"
        if px is None or len(px) < 1000:
            lines.append(f"| {a['name']} | {src} | — | — |")
            continue
        px = pd.Series(px).astype(float).dropna().sort_index()
        px.index = pd.to_datetime(px.index)
        px.index = px.index.tz_localize(None) if px.index.tz is not None else px.index
        loaded.append((a["name"], px))
        lines.append(f"| {a['name']} | {src} | {px.index[0]:%Y-%m-%d} | "
                     f"{len(px)/252:.0f} |")
    lines.append("")
    if not loaded:
        lines.append("**No long-history data could be loaded from the VM** (Stooq and "
                     "Yahoo both unavailable) — nothing to test.")
        return "\n".join(lines)

    # ---- A: drawdown signal
    lines.append(f"## A — Deep-drawdown signal ({horizon}d forward)")
    lines.append("| Asset | zone | episodes | ordinary fwd% | zone fwd% | excess pp | "
                 "t (non-overl.) | H1 / H2 excess | DCA × | dip-reserve × |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|---|--:|--:|")
    tally = {th: {"reached": 0, "pos": 0, "sig": 0, "both": 0, "dip": 0} for th in THRESHOLDS}
    f = lambda x: "—" if x != x else f"{100*x:+.1f}"
    for name, px in loaded:
        for th in THRESHOLDS:
            st = zone_stats(px, horizon, enter=th)
            dca, dip = dca_vs_dip_reserve(px, enter=th)
            if st.get("insufficient") or st["zone_days"] == 0:
                lines.append(f"| {name} | {th:.0%} | 0 | — | never | — | — | — | "
                             f"{dca:.2f} | {dip:.2f} |")
                continue
            t = tally[th]
            t["reached"] += 1
            t["pos"] += int(st["excess"] > 0)
            t["sig"] += int(st["t"] == st["t"] and st["t"] > 2.0)
            t["both"] += int(st["excess_h1"] == st["excess_h1"] and st["excess_h2"] ==
                             st["excess_h2"] and st["excess_h1"] > 0 and st["excess_h2"] > 0)
            t["dip"] += int(dip > dca)
            lines.append(
                f"| {name} | {th:.0%} | {st['episodes']} | {f(st['uncond'])} | "
                f"{f(st['zone'])} | {f(st['excess'])} | "
                f"{st['t']:.2f} (n={st['nov_in']}) | {f(st['excess_h1'])} / "
                f"{f(st['excess_h2'])} | {dca:.2f} | {dip:.2f} |")
    lines.append("")

    # ---- B: trend filters
    lines.append("## B — Trend filters vs buy & hold (CAGR / Sharpe / max drawdown)")
    lines.append("| Asset | B&H | SMA200 filter | 12m momentum | SMA200−B&H rigor |")
    lines.append("|---|---|---|---|---|")
    better_sharpe = better_dd = trend_pass = n_trend = 0
    g = lambda p: f"{100*p['cagr']:+.1f}% / {p['sharpe']:.2f} / {100*p['maxdd']:.0f}%"
    for name, px in loaded:
        tc = trend_comparison(px)
        if tc.get("insufficient"):
            lines.append(f"| {name} | — | — | — | insufficient |")
            continue
        n_trend += 1
        better_sharpe += int(tc["sma"]["sharpe"] > tc["bh"]["sharpe"])
        better_dd += int(tc["sma"]["maxdd"] > tc["bh"]["maxdd"])
        v = tc["rigor"].get("verdict", "—")
        trend_pass += int(v.startswith("✅"))
        vshort = "✅" if v.startswith("✅") else "⚠️" if v.startswith("⚠") else "❌"
        lines.append(f"| {name} | {g(tc['bh'])} | {g(tc['sma'])} | {g(tc['ts'])} | "
                     f"{vshort} |")
    lines.append("")

    lines.append("---")
    parts = []
    for th in THRESHOLDS:
        t = tally[th]
        parts.append(f"{th:.0%}: reached {t['reached']}/{len(loaded)}, excess>0 "
                     f"{t['pos']}, t>2 {t['sig']}, both halves {t['both']}, "
                     f"dip-reserve>DCA {t['dip']}")
    lines.append("**Summary A (drawdown):** " + "; ".join(parts) + ".")
    lines.append(f"**Summary B (trend):** SMA200 improved Sharpe in {better_sharpe}/{n_trend}, "
                 f"reduced max drawdown in {better_dd}/{n_trend}, beat B&H through full "
                 f"rigor in {trend_pass}/{n_trend}.")
    return "\n".join(lines)
