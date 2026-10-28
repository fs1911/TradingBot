"""
Experiments #69 / #81 — leverage: does 2× the risk give 2× the return?

#69 Daily-rebalanced leverage like leveraged ETFs: r_L = L·r − (L−1)·(cash + 0.5 %)/252 − fee/252
    (fee 0.9 % p.a. for L > 1), on the S&P 500 since 1928 (price + Shiller dividend yield),
    cash = T-bill (^IRX) from 1960, before that Shiller 10-year yield − 1 pt.
    L = 1, 1.5, 2, 3. CAGR, max drawdown, worst 10 years, share of all 20-year windows in
    which L beats 1×, 'ruin' (−90 % at any time). Plus 2× rebalanced only MONTHLY.
#81 Kelly and volatility drag: growth g(L) ≈ L·μ − L²σ²/2 → optimal L* = (μ − r)/σ².
    Hindsight-optimal leverage vs the leverage a real-time estimate (trailing 10 years)
    would have chosen — and what that estimate would have done (estimation risk).
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


def daily_inputs(gspc: pd.Series, irx: pd.Series | None, shiller: pd.DataFrame | None) -> pd.DataFrame:
    """Daily index return incl. dividends and daily cash rate."""
    px = pd.Series(gspc).dropna().astype(float)
    idx = pd.to_datetime(px.index)
    px.index = idx.tz_localize(None) if idx.tz is not None else idx
    r = px.pct_change()
    m = px.index.to_period("M")
    dy = pd.Series(0.0, index=px.index)
    cash_y = pd.Series(np.nan, index=px.index)
    if shiller is not None and not shiller.empty:
        sh = shiller.copy()
        sh.index = pd.to_datetime(sh.index).to_period("M")
        sh = sh[~sh.index.duplicated(keep="last")]
        d_p = (sh["div"] / sh["price"]).reindex(m).ffill()
        dy = pd.Series(d_p.to_numpy(), index=px.index).fillna(0.0)
        g = ((sh["gs10"] - 1.0).clip(lower=0) / 100).reindex(m).ffill()
        cash_y = pd.Series(g.to_numpy(), index=px.index)
    if irx is not None and len(irx):
        t = pd.Series(irx).dropna()
        ti = pd.to_datetime(t.index)
        t.index = ti.tz_localize(None) if ti.tz is not None else ti
        t = (t / 100).reindex(px.index).ffill()
        cash_y = t.where(t.notna(), cash_y)
    cash_y = cash_y.ffill().fillna(0.03)
    d = pd.DataFrame({"r": r + dy / 252, "cash": cash_y.shift(1).fillna(cash_y) / 252}).dropna()
    return d


def leveraged(d: pd.DataFrame, L: float, spread: float = 0.005, fee: float = 0.009) -> pd.Series:
    if L == 1:
        return d["r"]
    return L * d["r"] - (L - 1) * (d["cash"] + spread / 252) - fee / 252


def monthly_rebalanced(d: pd.DataFrame, L: float, spread: float = 0.005) -> pd.Series:
    """Leverage reset to L only at month starts; within the month assets and debt drift."""
    out = []
    for _, g in d.groupby(d.index.to_period("M")):
        assets = L * np.cumprod(1 + g["r"].to_numpy())
        debt = (L - 1) * np.cumprod(1 + g["cash"].to_numpy() + spread / 252)
        eq = np.maximum(assets - debt, 1e-6)
        out.append(eq / np.concatenate([[1.0], eq[:-1]]) - 1)
    return pd.Series(np.concatenate(out), index=d.index)


def stats(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    dd = eq / eq.cummax() - 1
    ann = eq.resample("YE").last() if isinstance(eq.index, pd.DatetimeIndex) else eq
    w10 = (ann / ann.shift(10)) ** (1 / 10) - 1
    return {"cagr": float(eq.iloc[-1] ** (1 / yrs) - 1) if eq.iloc[-1] > 0 else -1.0,
            "vol": float(r.std() * math.sqrt(252)), "maxdd": float(dd.min()),
            "worst10": float(w10.min()), "ruin": bool((eq <= 0.1 * eq.cummax()).any()),
            "final": float(eq.iloc[-1])}


def window_wins(r_l: pd.Series, r_1: pd.Series, years: int = 20) -> tuple:
    a = (1 + r_l).cumprod().resample("YE").last()
    b = (1 + r_1).cumprod().resample("YE").last()
    ra, rb = a / a.shift(years), b / b.shift(years)
    ok = ra.notna() & rb.notna()
    wins = (ra[ok] > rb[ok])
    return float(wins.mean()) if ok.any() else float("nan"), int(ok.sum()), float((ra[ok] < 1).mean()) if ok.any() else float("nan")


def kelly(monthly: pd.Series, cash_m: pd.Series, lookback: int = 120) -> pd.DataFrame:
    """Real-time Kelly leverage from trailing `lookback` months: (μ − r)/σ² (annualised)."""
    ex = (monthly - cash_m.reindex(monthly.index).fillna(0)).dropna()
    mu = ex.rolling(lookback).mean() * 12
    var = monthly.rolling(lookback).var() * 12
    return pd.DataFrame({"mu": mu, "var": var, "L": (mu / var).clip(-5, 10)}).dropna()


def run_experiment69_report(gspc: pd.Series, irx: pd.Series | None, shiller: pd.DataFrame | None) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiments #69 / #81 — leverage and Kelly ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    d = daily_inputs(gspc, irx, shiller)
    if len(d) < 5000:
        return "\n".join(L + ["Not enough data."])
    L.append(f"S&P 500 daily {d.index[0]:%Y-%m-%d} → {d.index[-1]:%Y-%m-%d} incl. dividends; borrowing at cash + 0.5 %, "
             f"fund fee 0.9 % p.a. for leveraged versions (typical leveraged ETF).")
    L.append("")
    L.append("## #69 Daily leverage (like leveraged ETFs)")
    L.append("| leverage | CAGR | volatility | max drawdown | worst 10 years p.a. | ever −90 %? | 20-y windows beating 1× | 20-y windows with a LOSS | ×final |")
    L.append("|---|--:|--:|--:|--:|:-:|--:|--:|--:|")
    base = leveraged(d, 1)
    for lev in (1, 1.5, 2, 3):
        r = leveraged(d, lev)
        st = stats(r)
        w, n, loss = window_wins(r, base)
        L.append(f"| {lev:g}× | {100*st['cagr']:+.1f} % | {100*st['vol']:.0f} % | {100*st['maxdd']:.0f} % | "
                 f"{100*st['worst10']:+.1f} % | {'yes' if st['ruin'] else 'no'} | "
                 f"{'—' if lev == 1 else f'{100*w:.0f} % of {n}'} | {100*loss:.0f} % | {st['final']:,.0f} |")
    r2m = monthly_rebalanced(d, 2.0)
    st = stats(r2m)
    w, n, loss = window_wins(r2m, base)
    L.append(f"| 2× monthly reset (no fund fee) | {100*st['cagr']:+.1f} % | {100*st['vol']:.0f} % | {100*st['maxdd']:.0f} % | "
             f"{100*st['worst10']:+.1f} % | {'yes' if st['ruin'] else 'no'} | {100*w:.0f} % of {n} | {100*loss:.0f} % | {st['final']:,.0f} |")
    L.append("")
    for a, b in (("1950-01-01", None), ("1990-01-01", None), ("2009-03-01", None)):
        sub = d[d.index >= a]
        if len(sub) < 252 * 5:
            continue
        parts = []
        for lev in (1, 2, 3):
            s = stats(leveraged(sub, lev))
            parts.append(f"{lev}× {100*s['cagr']:+.1f} % (DD {100*s['maxdd']:.0f} %)")
        L.append(f"- from {a[:7]}: " + ", ".join(parts))
    L.append("")
    L.append("## #81 Kelly: the growth-optimal leverage — in hindsight and in real time")
    mret = (1 + d["r"]).groupby(d.index.to_period("M")).prod() - 1
    mcash = (1 + d["cash"]).groupby(d.index.to_period("M")).prod() - 1
    mu = (mret - mcash).mean() * 12
    var = mret.var() * 12
    L.append(f"Whole sample: excess return μ − r = {100*mu:.1f} %/yr, σ = {100*math.sqrt(var):.1f} % → hindsight Kelly "
             f"L* = {mu/var:.2f}. Growth g(L) ≈ L·(μ−r) − L²σ²/2 + r: at L* the growth is maximal; above 2·L* it is "
             f"BELOW cash (volatility drag).")
    k = kelly(mret, mcash)
    if len(k):
        L.append(f"Real-time Kelly from the trailing 10 years ranged {k['L'].min():.1f} … {k['L'].max():.1f} "
                 f"(median {k['L'].median():.1f}); share of months it said > 2×: {100*(k['L'] > 2).mean():.0f} %, "
                 f"< 0 (short!): {100*(k['L'] < 0).mean():.0f} %.")
        lev = k["L"].clip(0, 3).shift(1).reindex(mret.index).dropna()
        rk = (lev * mret.reindex(lev.index) - (lev - 1) * (mcash.reindex(lev.index) + 0.005 / 12)).dropna()
        eq = (1 + rk).cumprod()
        b = (1 + mret.reindex(rk.index)).cumprod()
        yrs = len(rk) / 12
        L.append(f"Following the real-time Kelly estimate (capped 0–3×, monthly) {rk.index[0]}–{rk.index[-1]}: "
                 f"CAGR {100*(eq.iloc[-1]**(1/yrs)-1):+.1f} % vs 1× {100*(b.iloc[-1]**(1/yrs)-1):+.1f} %, "
                 f"max DD {100*(eq/eq.cummax()-1).min():.0f} % vs {100*(b/b.cummax()-1).min():.0f} %.")
    L.append("")
    L.append("Reading: leverage multiplies volatility, and volatility costs growth (≈ σ²/2 per unit² of leverage). "
             "Whether 2× pays off depends on the period; the growth-optimal leverage is only known in hindsight, and "
             "estimating it in real time swings wildly.")
    return "\n".join(L)
