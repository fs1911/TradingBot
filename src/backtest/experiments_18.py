"""
Experiment #18 — a NEW DATA REGIME: intraday (5-minute) bars instead of daily.

The whole project so far ran on daily bars — few observations, and blind to
intraday structure. This tests the user's hypothesis that the resolution was the
limitation. Intraday gives ~50-80x more observations and a different pattern class.

Strategy: intraday mean reversion, fully within-session (flat overnight, so no
gap risk). Within each trading day, a rolling z-score of price vs its recent
intraday mean; go long when stretched down (z < -entry), exit when it reverts
(z > -exit) or at the session close. Per-bar returns are aggregated to a DAILY P&L
series, which is then judged by the standard daily-calibrated rigor battery.

Honest note: intraday is where HFT has the structural edge and where costs/spreads
bite hardest — so costs matter a lot here. Causal throughout.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor, block_bootstrap_pvalue, deflated_ok, t_stat, annualized_sharpe


def intraday_meanrev_bar_returns(df, w=12, entry=1.5, exit=0.3,
                                 commission_pct=0.01, slippage_pct=0.02) -> pd.Series:
    """Per-BAR net returns of the within-session rolling-z mean-reversion strategy
    (flat overnight). Returns thousands of observations even when the calendar span
    is short — used for a significance read when there are too few sessions for the
    daily walk-forward battery."""
    if df is None or len(df) < 500:
        return pd.Series(dtype=float)
    c = df["close"].sort_index()
    idx = c.index
    day = (pd.Index(idx).tz_convert("UTC").normalize() if idx.tz is not None
           else pd.Index(idx).normalize())
    cost = (commission_pct + slippage_pct) / 100
    close = c.to_numpy()
    df2 = pd.DataFrame({"c": close, "day": day.values}, index=idx)
    out = []
    for _, grp in df2.groupby("day"):
        p = grp["c"].to_numpy()
        n = len(p)
        ts = grp.index
        if n < w + 5:
            out.append(pd.Series(np.zeros(n), index=ts)); continue
        r = np.zeros(n); r[1:] = p[1:] / p[:-1] - 1
        pos = np.zeros(n); cur = 0
        for i in range(n):
            if i < w:
                pos[i] = 0; continue
            win = p[i - w:i]; mu = win.mean(); sd = win.std()
            z = (p[i] - mu) / sd if sd > 0 else 0.0
            if i == n - 1:
                cur = 0
            elif cur == 0 and z < -entry:
                cur = 1
            elif cur == 1 and z > -exit:
                cur = 0
            pos[i] = cur
        held = np.concatenate([[0.0], pos[:-1]])
        turn = np.abs(np.diff(np.concatenate([[0.0], held])))
        out.append(pd.Series(held * r - turn * cost, index=ts))
    s = pd.concat(out).sort_index()
    s.name = "ret"
    return s


def _intraday_bar_eval(bar_ret: pd.Series, n_trials: int) -> dict:
    """Significance read on the per-bar series: total return, annualized Sharpe,
    t-stat, block-bootstrap p-value (+ haircut), and an in-/out-of-sample split by
    calendar midpoint. Honest caveat: a short calendar span is only ONE regime."""
    r = bar_ret.dropna()
    if len(r) < 500:
        return {"verdict": "insufficient bars"}
    # annualize using observed bars-per-day
    days = len(pd.Index(r.index).normalize().unique())
    bars_per_day = max(1, len(r) / max(days, 1))
    ann = bars_per_day * (365 if _is_crypto_index(r.index) else 252)
    sharpe = float(r.mean() / r.std() * np.sqrt(ann)) if r.std() > 0 else 0.0
    total = float((1 + r).prod() - 1) * 100
    ts = t_stat(r)
    p = block_bootstrap_pvalue(r, n=1500, block=20)
    sig = deflated_ok(p, n_trials)
    mid = r.index[len(r) // 2]
    is_ret = float((1 + r.loc[:mid]).prod() - 1) * 100
    oos_ret = float((1 + r.loc[mid:]).prod() - 1) * 100
    verdict = ("✅ significant (preliminary, 1 regime)" if (sig and oos_ret > 0)
               else "⚠️ significant but not haircut-proof" if (p < 0.05 and oos_ret > 0)
               else "❌ no edge")
    return {"days": days, "sharpe": round(sharpe, 2), "t_stat": round(ts, 2),
            "p_value": round(p, 4), "sig": sig, "total": total,
            "is_ret": is_ret, "oos_ret": oos_ret, "verdict": verdict}


def _is_crypto_index(idx) -> bool:
    # crypto trades weekends → many distinct weekday counts; heuristic
    try:
        wd = pd.Index(idx).dayofweek
        return bool((wd >= 5).mean() > 0.15)
    except Exception:
        return False


def intraday_meanrev_daily_returns(df, w=12, entry=1.5, exit=0.3,
                                   commission_pct=0.01, slippage_pct=0.02):
    """Within-day rolling-z mean reversion on intraday bars; returns a DAILY net
    return series (sum of per-bar P&L within each session). Flat overnight."""
    if df is None or len(df) < 500:
        return pd.Series(dtype=float)
    c = df["close"].sort_index()
    idx = c.index
    day = pd.Index(idx).tz_convert("UTC").normalize() if idx.tz is not None else pd.Index(idx).normalize()
    cost = (commission_pct + slippage_pct) / 100

    daily = {}
    close = c.to_numpy()
    # iterate per session
    df2 = pd.DataFrame({"c": close, "day": day.values})
    for d, grp in df2.groupby("day"):
        p = grp["c"].to_numpy()
        n = len(p)
        if n < w + 5:
            continue
        r = np.zeros(n)
        r[1:] = p[1:] / p[:-1] - 1
        # rolling mean/std over trailing w bars (causal, within day)
        pos = np.zeros(n)
        cur = 0
        for i in range(n):
            if i < w:
                pos[i] = 0; continue
            win = p[i - w:i]
            mu = win.mean(); sd = win.std()
            z = (p[i] - mu) / sd if sd > 0 else 0.0
            if i == n - 1:                     # force flat at session close
                cur = 0
            elif cur == 0 and z < -entry:
                cur = 1
            elif cur == 1 and z > -exit:
                cur = 0
            pos[i] = cur
        held = np.concatenate([[0.0], pos[:-1]])       # position during bar i = decision at i-1
        turn = np.abs(np.diff(np.concatenate([[0.0], held])))
        pnl = held * r - turn * cost
        daily[pd.Timestamp(d)] = float(pnl.sum())

    if not daily:
        return pd.Series(dtype=float)
    s = pd.Series(daily).sort_index()
    s.name = "ret"
    return s


def run_experiment18_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    symbols: list[str],
    timeframe: str = "5Min",
    n_trials: int = 50,
    limit: int = 20000,
) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #18 — intraday ({timeframe}) mean reversion "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"NEW DATA REGIME: intraday bars (~50-80x more observations than daily). "
                 f"Within-session rolling-z mean reversion, flat overnight, per-bar P&L aggregated "
                 f"to daily and judged by the full rigor battery (haircut α/{n_trials}). Intraday "
                 f"costs bite hard — watch whether any edge survives them.")
    lines.append("")
    lines.append("| Symbol | bars | days | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|:--:|:--:|:--:|---|")

    results = []
    short_survivors: list[str] = []
    for sym in symbols:
        try:
            df = get_ohlcv(sym, timeframe, limit)
        except Exception as e:
            logger.warning(f"Exp18: fetch {sym} failed: {e}")
            df = None
        if df is None or len(df) < 2000:
            lines.append(f"| {sym} | {0 if df is None else len(df)} | — | intraday data unavailable/too short |||||||")
            continue
        daily = intraday_meanrev_daily_returns(df)
        if not daily.empty and len(daily) >= 300:
            res = full_rigor(f"IntradayMR {sym}", daily, n_trials)
            results.append(res)
            lines.append(f"| {sym} | {len(df)} | {len(daily)} | {res['oos_ret']:+.0f} | {res['sharpe']} | "
                         f"{res['t_stat']} | {res['p_value']} | {'yes' if res['sig_after_haircut'] else 'no'} | "
                         f"{res['wf_pct']}% | {res['regime_positive']} | {res['verdict']} |")
        else:
            # Too few sessions for the daily walk-forward battery → bar-level read
            bar = intraday_meanrev_bar_returns(df)
            ev = _intraday_bar_eval(bar, n_trials)
            if ev.get("verdict", "").startswith(("✅", "⚠")):
                short_survivors.append(f"{sym} ({ev['verdict']})")
            if "days" in ev:
                lines.append(f"| {sym} | {len(df)} | {ev['days']} | tot {ev['total']:+.0f} · "
                             f"IS {ev['is_ret']:+.0f}/OOS {ev['oos_ret']:+.0f} | {ev['sharpe']} | "
                             f"{ev['t_stat']} | {ev['p_value']} | {'yes' if ev['sig'] else 'no'} | "
                             f"bar-level | 1 regime | {ev['verdict']} |")
            else:
                lines.append(f"| {sym} | {len(df)} | — | {ev.get('verdict','insufficient')} |||||||")

    lines.append("")
    survivors = [r for r in results if r.get("verdict", "").startswith("✅")]
    note = ""
    if short_survivors:
        note = (" Bar-level (PRELIMINARY, only ~70 days = one regime, needs paid multi-year "
                "intraday data to confirm): " + ", ".join(short_survivors))
    lines.append(f"**Summary:** {len(survivors)}/{len(results)} survive the full daily battery on "
                 f"intraday data." + (note if note else
                 " Free feed gives only ~70 days of intraday history — proper intraday research "
                 "needs a paid multi-year intraday data source."))
    return "\n".join(lines)
