"""
Experiment #39 — is "PutWrite + trend filter" really better, or just less risky?

#38: PutWrite gated by the S&P 500 200d trend had Sharpe 0.98 vs 0.58 for the S&P 500
TR and max drawdown −16% vs −55% — but lower CAGR (7.0% vs 9.8%), and the rigor battery
only tests returns. This experiment tests the risk-adjusted claim properly:

  1. SHARPE-DIFFERENCE TEST: excess-over-cash Sharpe of the strategy vs S&P 500 TR,
     PutWrite and S&P+trend, with a PAIRED block bootstrap (both series resampled with
     the same 20-day blocks, 5000 draws) → one-sided p and 95% CI of the difference,
     Bonferroni haircut over the project's trial count.
  2. EQUAL RISK: lever the strategy 1.5×, 2× and to the S&P's volatility, paying
     T-bill + 1%/y on borrowed money → does it then beat the S&P on return, and at what
     drawdown?
  3. ROBUSTNESS: SMA 150/200/250 × daily/monthly check × start 1997/2002/2007/2012 —
     in how many of the 24 cells does the strategy's Sharpe beat the S&P's?

Pure, injected for CI; reuses #33/#38 building blocks.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_32 import perf
from .experiments_33 import cash_daily_returns, trend_position
from .experiments_38 import _naive


def prepare(put: pd.Series, sptr: pd.Series, irx: pd.Series) -> dict:
    put, sptr = _naive(put), _naive(sptr)
    idx = put.index.intersection(sptr.index)
    put, sptr = put.loc[idx], sptr.loc[idx]
    irx_n = _naive(irx) if irx is not None and len(irx) else pd.Series(dtype=float)
    return {"sp_level": sptr, "r_put": put.pct_change().fillna(0.0),
            "r_sp": sptr.pct_change().fillna(0.0), "cash": cash_daily_returns(irx_n, idx)}


def gated(r: pd.Series, sp_level: pd.Series, cash: pd.Series, window: int = 200,
          monthly: bool = False, cost_bps: float = 5.0) -> pd.Series:
    pos = trend_position(sp_level, window, monthly)
    return r * pos + cash * (1 - pos) - pos.diff().abs().fillna(0.0) * cost_bps / 1e4


def sharpe_excess(r: pd.Series, cash: pd.Series) -> float:
    x = (r - cash.reindex(r.index).fillna(0.0)).dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if x.std() > 0 else float("nan")


def sharpe_diff_bootstrap(a: pd.Series, b: pd.Series, cash: pd.Series,
                          n: int = 5000, block: int = 20, seed: int = 0) -> dict:
    """Paired moving-block bootstrap of Sharpe(a) − Sharpe(b) on excess returns."""
    c = cash.reindex(a.index).fillna(0.0)
    xa = (a - c).to_numpy()
    xb = (b.reindex(a.index) - c).to_numpy()
    T = len(xa)
    obs = sharpe_excess(a, cash) - sharpe_excess(b.reindex(a.index), cash)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / block))
    diffs = np.empty(n)
    offs = np.arange(block)
    for i in range(n):
        starts = rng.integers(0, T - block + 1, nb)
        ix = (starts[:, None] + offs[None, :]).ravel()[:T]
        sa, sb = xa[ix], xb[ix]
        diffs[i] = (sa.mean() / sa.std() - sb.mean() / sb.std()) * math.sqrt(252)
    # one-sided p for H0: diff ≤ 0, centred on the observed difference
    p = float(np.mean((diffs - obs) >= obs)) if obs > 0 else 1.0
    return {"obs": obs, "p": p, "lo": float(np.percentile(diffs, 2.5)),
            "hi": float(np.percentile(diffs, 97.5))}


def levered(r: pd.Series, cash: pd.Series, lev: float, spread: float = 0.01) -> pd.Series:
    c = cash.reindex(r.index).fillna(0.0)
    return lev * r - (lev - 1.0) * (c + spread / 252.0)


def run_experiment39_report(series: dict, n_trials: int = 155, n_boot: int = 5000) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #39 — PutWrite + trend: really better, or only less risky? "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    put, sptr, irx = series.get("PUT"), series.get("SP500TR"), series.get("IRX")
    if put is None or len(put) < 2000 or sptr is None or len(sptr) < 2000:
        lines.append("**Missing data** — need ^PUT and ^SP500TR daily history.")
        return "\n".join(lines)
    d = prepare(put, sptr, irx if irx is not None else pd.Series(dtype=float))
    warm = 250
    cash = d["cash"].iloc[warm:]
    sp = d["r_sp"].iloc[warm:]
    pw = d["r_put"].iloc[warm:]
    strat = gated(d["r_put"], d["sp_level"], d["cash"]).iloc[warm:]
    sp_tf = gated(d["r_sp"], d["sp_level"], d["cash"]).iloc[warm:]
    have_cash = irx is not None and len(irx) > 1000
    crit = 0.05 / n_trials
    lines.append(f"Daily {strat.index[0]:%Y-%m-%d} → {strat.index[-1]:%Y-%m-%d}. Sharpe = excess over "
                 f"13-week T-bill{'' if have_cash else ' (MISSING → 0%)'}. Bootstrap: paired 20-day "
                 f"blocks, {n_boot} draws; haircut p < {crit:.5f}.")
    lines.append("")

    # 1. Sharpe-difference tests
    lines.append("## 1 — Sharpe-difference test (PutWrite + trend vs …)")
    lines.append("| vs | Sharpe strat | Sharpe other | difference | 95% CI | p (one-sided) | sig after haircut |")
    lines.append("|---|--:|--:|--:|---|--:|:--:|")
    sig_count = 0
    for name, other in (("S&P 500 TR", sp), ("PutWrite", pw), ("S&P 500 TR + trend", sp_tf)):
        bt = sharpe_diff_bootstrap(strat, other, cash, n=n_boot)
        sig = bt["p"] < crit and bt["obs"] > 0
        sig_count += int(sig)
        lines.append(f"| {name} | {sharpe_excess(strat, cash):.2f} | {sharpe_excess(other, cash):.2f} | "
                     f"{bt['obs']:+.2f} | [{bt['lo']:+.2f}, {bt['hi']:+.2f}] | {bt['p']:.4f} | "
                     f"{'✅' if sig else '❌'} |")
    lines.append("")

    # 2. Equal risk via leverage
    vol_sp, vol_st = sp.std() * math.sqrt(252), strat.std() * math.sqrt(252)
    lev_eq = float(vol_sp / vol_st) if vol_st > 0 else 1.0
    lines.append("## 2 — Equal risk: levered strategy (financing T-bill + 1%/y) vs S&P 500 TR")
    lines.append("| Portfolio | leverage | CAGR | vol | max DD |")
    lines.append("|---|--:|--:|--:|--:|")
    p_sp = perf(sp)
    lines.append(f"| S&P 500 TR | 1.0× | {100*p_sp['cagr']:+.1f}% | {100*vol_sp:.1f}% | {100*p_sp['maxdd']:.0f}% |")
    lev_rows = {}
    for L in (1.0, 1.5, 2.0, lev_eq):
        r = levered(strat, cash, L)
        p = perf(r)
        lev_rows[L] = p
        tag = " (= S&P vol)" if L == lev_eq else ""
        lines.append(f"| PutWrite + trend | {L:.2f}×{tag} | {100*p['cagr']:+.1f}% | "
                     f"{100*r.std()*math.sqrt(252):.1f}% | {100*p['maxdd']:.0f}% |")
    lines.append("")

    # 3. Robustness grid
    lines.append("## 3 — Robustness: Sharpe (excess) strategy vs S&P 500 TR")
    lines.append("| start | SMA150 d | SMA150 m | SMA200 d | SMA200 m | SMA250 d | SMA250 m | S&P |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|--:|")
    wins = cells = 0
    for start in ("1997", "2002", "2007", "2012"):
        row = []
        sp_s = d["r_sp"].loc[start:].iloc[warm if start == "1997" else 0:]
        c_s = d["cash"].reindex(sp_s.index)
        sh_sp = sharpe_excess(sp_s, c_s)
        for w in (150, 200, 250):
            for monthly in (False, True):
                g = gated(d["r_put"], d["sp_level"], d["cash"], w, monthly).reindex(sp_s.index)
                sh = sharpe_excess(g, c_s)
                cells += 1
                wins += int(sh > sh_sp)
                row.append(f"{sh:.2f}")
        lines.append(f"| {start} | " + " | ".join(row) + f" | {sh_sp:.2f} |")
    lines.append("")

    beat_eq = lev_rows[lev_eq]["cagr"] > p_sp["cagr"]
    lines.append("---")
    lines.append(
        f"**Summary:** Sharpe difference significant after haircut in {sig_count}/3 comparisons. "
        f"At equal volatility ({lev_eq:.2f}× leverage, financed at T-bill+1%) the strategy returns "
        f"{100*lev_rows[lev_eq]['cagr']:+.1f}% vs {100*p_sp['cagr']:+.1f}% for the S&P with max DD "
        f"{100*lev_rows[lev_eq]['maxdd']:.0f}% vs {100*p_sp['maxdd']:.0f}% → "
        f"{'beats' if beat_eq else 'does not beat'} the S&P at equal risk. Robustness: strategy Sharpe "
        f"> S&P in {wins}/{cells} parameter × start-year cells.")
    return "\n".join(lines)
