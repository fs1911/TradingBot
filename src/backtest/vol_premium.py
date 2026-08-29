"""
Volatility risk-premium edge test — the one hypothesis with a real, documented,
persistent mathematical core: implied volatility is on average higher than the
volatility that actually realises, so the seller of volatility earns the spread.

We can't cleanly get historical option chains, so we harvest the premium through
the tradeable instrument that embodies it: SVXY (short VIX short-term futures).
Holding SVXY ≈ being short volatility and collecting the roll/premium.

CRUCIAL HONESTY: this premium is compensation for CRASH RISK, not free money.
SVXY lost ~90% in a SINGLE day on 2018-02-05 ("Volmageddon"). So the report
surfaces the worst single-day return and max drawdown loudly, and tests a
trend-filtered variant (hold only above its 50-day average, else cash) that tries
to step aside before the blow-ups — the only version with a chance of a survivable
risk-adjusted edge. Walk-forward decides robustness, as always.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .trend_follow import _curve_stats


def _stats_plus(returns: pd.Series) -> dict:
    """_curve_stats plus the worst single-day return (the tail that matters here)."""
    s = _curve_stats(returns)
    r = returns.dropna()
    s["worst_day"] = round(float(r.min()) * 100, 1) if len(r) else 0.0
    return s


def short_vol_returns(df: pd.DataFrame, *, sign: float, mode: str, sma: int = 50,
                      commission_pct: float = 0.05, slippage_pct: float = 0.03) -> pd.Series:
    """Daily net returns of a short-volatility position on `df`.

    sign = +1 if df is already a short-vol instrument (SVXY); -1 to short a
    long-vol instrument (VXX). mode='naive' holds always; mode='trend' holds only
    when the instrument is above its `sma`-day average (else cash), decided at the
    prior close (no look-ahead)."""
    if len(df) < sma + 30:
        return pd.Series(dtype=float)
    df = df.sort_index().copy()
    inst_ret = (df["close"].pct_change() * sign).fillna(0)
    if mode == "naive":
        held = pd.Series(1.0, index=df.index)
    else:
        ma = df["close"].rolling(sma).mean()
        state = (df["close"] > ma).astype(float)
        held = state.shift(1).fillna(0.0)          # position today = signal at prior close
    cost = (commission_pct + slippage_pct) / 100
    turn = held.diff().abs().fillna(held)
    return (held * inst_ret - turn * cost).rename("ret")


def run_vol_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    short_vol_candidates: list[str],
    benchmark: str = "SPY",
    sma: int = 50,
    limit: int = 2500,
    window: int = 252,
    step: int = 63,
    commission_pct: float = 0.05,
    slippage_pct: float = 0.03,
) -> str:
    from datetime import datetime, timezone

    p = dict(commission_pct=commission_pct, slippage_pct=slippage_pct)
    lines = [f"# Volatility Risk-Premium Edge Test — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    lines.append("Harvest the vol premium via a short-VIX ETF. The premium is REAL but is "
                 "compensation for crash risk — watch 'worst day' and maxDD. MAR = return/|maxDD|. "
                 "The trend-filtered variant tries to step aside before blow-ups.")
    lines.append("")

    # Pick the first available short-vol instrument
    inst_df = None
    inst_name = None
    sign = 1.0
    for sym in short_vol_candidates:
        try:
            d = get_ohlcv(sym, "1Day", limit)
            if d is not None and len(d) >= sma + 60:
                inst_df, inst_name = d, sym
                sign = -1.0 if sym.upper() in ("VXX", "UVXY", "VIXY") else 1.0
                break
        except Exception as e:
            logger.warning(f"Vol: could not fetch {sym}: {e}")
    if inst_df is None:
        lines.append("_no short-vol instrument (SVXY/VXX/…) available on this data feed — cannot test_")
        return "\n".join(lines)

    try:
        bench_df = get_ohlcv(benchmark, "1Day", limit)
    except Exception:
        bench_df = None

    pos = "short" if sign > 0 else "short (inverted)"
    lines.append(f"Instrument: **{inst_name}** ({pos}-vol) · {len(inst_df)} daily bars "
                 f"{inst_df.index[0]:%Y-%m} → {inst_df.index[-1]:%Y-%m}")
    lines.append("")

    naive = short_vol_returns(inst_df, sign=sign, mode="naive", sma=sma, **p)
    trend = short_vol_returns(inst_df, sign=sign, mode="trend", sma=sma, **p)
    rows = [("Short-vol naive", naive), (f"Short-vol trend>{sma}d", trend)]
    if bench_df is not None and len(bench_df) > sma:
        rows.append((f"Hold {benchmark}", bench_df["close"].pct_change().fillna(0)))

    lines.append("| Strategy | total ret% | maxDD% | MAR | worst 1-day% | %inMkt |")
    lines.append("|---|--:|--:|--:|--:|--:|")
    for lbl, s in rows:
        st = _stats_plus(s)
        in_mkt = ""
        if lbl.startswith("Short-vol trend"):
            held = (short_vol_returns(inst_df, sign=sign, mode="trend", sma=sma, **p) != 0)
            in_mkt = f"{held.mean()*100:.0f}%"
        elif lbl.startswith("Short-vol naive"):
            in_mkt = "100%"
        lines.append(f"| {lbl} | {st['ret']:+.0f} | {st['dd']:.0f} | {st['mar']} | "
                     f"{st['worst_day']} | {in_mkt} |")
    lines.append("")

    # Walk-forward: trend-filtered short-vol vs holding the benchmark, on MAR
    if bench_df is not None:
        bench_ret = bench_df["close"].pct_change().fillna(0)
        common = trend.index.intersection(bench_ret.index)
        tr, bh = trend.loc[common], bench_ret.loc[common]
        rows_wf, i = [], 0
        while i + window <= len(common):
            ts = _curve_stats(tr.iloc[i:i + window])
            bs = _curve_stats(bh.iloc[i:i + window])
            rows_wf.append((common[i], common[i + window - 1], ts, bs,
                            ts["mar"] > bs["mar"] and ts["ret"] > 0))
            i += step
        if rows_wf:
            nb, n = sum(r[4] for r in rows_wf), len(rows_wf)
            pct = round(100 * nb / n)
            verdict = ("✅ robust edge" if pct >= 60 else
                       "⚠️ regime-dependent" if pct >= 40 else "❌ not robust")
            lines.append(f"**Walk-forward (trend short-vol vs {benchmark}):** beat in "
                         f"**{nb}/{n} windows ({pct}%)** → {verdict}")
            lines.append("")
            lines.append("| Window | Vol ret% | Vol MAR | Vol worstDay% | " + benchmark + " ret% | " + benchmark + " MAR | wins? |")
            lines.append("|---|--:|--:|--:|--:|--:|:--:|")
            for start, end, ts, bs, beat in rows_wf:
                wd = round(tr.loc[start:end].min() * 100, 1)
                lines.append(f"| {start:%Y-%m} → {end:%Y-%m} | {ts['ret']:+.0f} | {ts['mar']} | "
                             f"{wd} | {bs['ret']:+.0f} | {bs['mar']} | {'✅' if beat else '—'} |")
        lines.append("")

    lines.append("The vol premium is real, but a big negative 'worst day' / maxDD is the crash risk "
                 "you are paid to carry. An edge must beat buy-and-hold on MAR across MOST windows AND "
                 "keep the tail survivable.")
    return "\n".join(lines)
