"""
Experiment #41 — hardening the multi-asset trend-following result of #40.

#40 was the first result whose excess return passed the multiple-testing haircut, in
two independent universes. Results like that deserve the hardest attack before they
are trusted. On the same two universes (broad ETFs, long mutual funds):

  1. SIGNAL HORIZON: 1, 3, 6, 12 months and the blends 3/6/12 and 1/3/12 (mean of signs).
  2. COSTS: turnover cost 5/10/20 bps × short borrow fee 0/2/5% a year.
  3. LEVERAGE: gross exposure cap 1.0/1.5/2.0/3.0.
  4. REALISTIC VERSION: blend 3/6/12, 10 bps, 2% borrow, gross ≤ 2 — full rigor, pre/post
     2012, 60/40 with equity (paired Sharpe bootstrap).
  5. DRY SPELLS: longest time under water, worst rolling 3-year return, share of losing
     3-year windows, worst rolling 3-year excess Sharpe.
  6. PLACEBO: 100 runs with RANDOM long/short signs but identical weighting, vol target,
     leverage and costs. If real trend is not clearly better than random signs, #40 was
     an artefact of the machinery, not of trend.

Pure, injected for CI. Reuses #33/#38/#39/#40 building blocks.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .rigor import full_rigor
from .experiments_32 import perf
from .experiments_33 import cash_daily_returns
from .experiments_38 import _naive
from .experiments_39 import sharpe_excess, sharpe_diff_bootstrap
from .experiments_40 import build_returns, month_end_positions, _active, w_equity

PUB = "2012-12-31"


def make_tsmom(horizons=(252,), long_only=False, target=0.10, cap=3.0, placebo_rng=None):
    """Weight function factory. Signal = mean over horizons of sign(excess return);
    placebo_rng → random ±1 signs instead (same machinery)."""
    need = max(horizons) + 5

    def fn(hist: pd.DataFrame, cash_hist: pd.Series, eq_key: str) -> pd.Series:
        act = _active(hist, need)
        if not act:
            return pd.Series(dtype=float)
        if placebo_rng is not None:
            sig = pd.Series(placebo_rng.choice([-1.0, 1.0], len(act)), index=act)
        else:
            sigs = []
            for h in horizons:
                r = (1 + hist[act].tail(h).fillna(0.0)).prod() - 1
                c = float((1 + cash_hist.tail(h)).prod() - 1)
                sigs.append(np.sign(r - c))
            sig = sum(sigs) / len(sigs)
        if long_only:
            sig = sig.clip(lower=0.0)
        vol = hist[act].tail(60).std() * math.sqrt(252)
        raw = (sig / vol.replace(0, np.nan)).fillna(0.0)
        if (raw != 0).sum() == 0:
            return raw
        cov = hist[act].tail(120).fillna(0.0).cov().to_numpy() * 252
        pv = float(math.sqrt(max(raw.to_numpy() @ cov @ raw.to_numpy(), 1e-12)))
        w = raw * (target / pv)
        lim = min(cap, 1.0) if long_only else cap
        g = w.abs().sum()
        return w * (lim / g) if g > lim else w

    return fn


def run_with_costs(rets: pd.DataFrame, cash: pd.Series, weight_fn, eq_key: str,
                   cost_bps: float = 5.0, borrow: float = 0.0) -> pd.Series:
    """Monthly-rebalanced excess-return accounting with turnover cost and a daily
    borrow fee on the short leg."""
    mes = month_end_positions(rets.index)
    out = pd.Series(np.nan, index=rets.index)
    prev = pd.Series(dtype=float)
    for k, m in enumerate(mes[:-1]):
        w = weight_fn(rets.iloc[: m + 1], cash.iloc[: m + 1], eq_key).reindex(rets.columns).fillna(0.0)
        s, e = m + 1, mes[k + 1] + 1
        blk = rets.iloc[s:e].fillna(0.0)
        c = cash.iloc[s:e]
        short = float(w.clip(upper=0.0).abs().sum())
        pr = c + (blk.sub(c, axis=0) * w).sum(axis=1) - short * borrow / 252.0
        if len(pr):
            pr.iloc[0] -= float((w - prev.reindex(w.index).fillna(0.0)).abs().sum()) * cost_bps / 1e4
        out.iloc[s:e] = pr.to_numpy()
        prev = w
    return out.dropna()


def dry_spells(r: pd.Series, cash: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    under = eq < eq.cummax()
    longest = cur = 0
    for u in under.to_numpy():
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    r3 = (1 + r).rolling(756).apply(np.prod, raw=True) - 1
    x = r - cash.reindex(r.index).fillna(0.0)
    sh3 = x.rolling(756).mean() / x.rolling(756).std() * math.sqrt(252)
    return {"under_years": longest / 252, "worst3y": float(r3.min()),
            "neg3y": float((r3.dropna() < 0).mean()), "worst_sh3": float(sh3.min())}


def universe41(name: str, prices: dict, eq_key: str, irx: pd.Series, n_trials: int = 165,
               n_placebo: int = 100, n_boot: int = 3000) -> list:
    L = [f"## Universe: {name}", ""]
    rets = build_returns(prices)
    if rets.empty or eq_key not in rets.columns:
        L.append(f"No usable data (equity asset {eq_key} missing).")
        return L
    cash = cash_daily_returns(_naive(irx) if irx is not None and len(irx) else pd.Series(dtype=float),
                              rets.index)
    eq_first = rets.index.get_loc(rets[eq_key].first_valid_index())
    start = rets.index[min(len(rets.index) - 1, eq_first + 260)]

    def run(fn, cost=5.0, borrow=0.0):
        return run_with_costs(rets, cash, fn, eq_key, cost, borrow).loc[start:]

    eq = run(w_equity, 0.0, 0.0)
    c = cash.reindex(eq.index)
    L.append(f"Evaluated {eq.index[0]:%Y-%m-%d} → {eq.index[-1]:%Y-%m-%d}. Equity ({eq_key}) excess "
             f"Sharpe {sharpe_excess(eq, c):.2f}.")
    L.append("")

    def sig_cell(r):
        g = full_rigor("x", r - cash.reindex(r.index), n_trials)
        if g.get("verdict") == "insufficient data":
            return "—", "—"
        return f"{g['p_value']}", ("✅" if g["sig_after_haircut"] else "❌")

    # 1. horizons
    L.append("### 1 — Signal horizon (5 bps, no borrow fee, gross ≤ 3)")
    L.append("| Signal | CAGR | Sharpe (excess) | max DD | p | sig |")
    L.append("|---|--:|--:|--:|--:|:--:|")
    horizons = {"1m": (21,), "3m": (63,), "6m": (126,), "12m": (252,),
                "blend 3/6/12": (63, 126, 252), "blend 1/3/12": (21, 63, 252)}
    h_sig = 0
    for lbl, h in horizons.items():
        r = run(make_tsmom(h))
        p, s = sig_cell(r)
        h_sig += int(s == "✅")
        pp = perf(r)
        L.append(f"| {lbl} | {100*pp['cagr']:+.1f}% | {sharpe_excess(r, cash.reindex(r.index)):.2f} | "
                 f"{100*pp['maxdd']:.0f}% | {p} | {s} |")
    L.append("")

    # 2. costs (12m)
    L.append("### 2 — Costs (12m signal, gross ≤ 3): Sharpe (excess) / CAGR")
    L.append("| turnover cost \\ borrow | 0% | 2% | 5% |")
    L.append("|---|---|---|---|")
    cost_pos = 0
    for cb in (5.0, 10.0, 20.0):
        cells = []
        for bw in (0.0, 0.02, 0.05):
            r = run(make_tsmom((252,)), cb, bw)
            sh = sharpe_excess(r, cash.reindex(r.index))
            cost_pos += int(sh > 0)
            cells.append(f"{sh:.2f} / {100*perf(r)['cagr']:+.1f}%")
        L.append(f"| {cb:.0f} bps | " + " | ".join(cells) + " |")
    L.append("")

    # 3. leverage cap (12m, 10 bps, 2% borrow)
    L.append("### 3 — Leverage cap (12m, 10 bps, 2% borrow)")
    L.append("| gross cap | CAGR | vol | Sharpe (excess) | max DD |")
    L.append("|---|--:|--:|--:|--:|")
    for cap in (1.0, 1.5, 2.0, 3.0):
        r = run(make_tsmom((252,), cap=cap), 10.0, 0.02)
        pp = perf(r)
        L.append(f"| {cap:.1f}× | {100*pp['cagr']:+.1f}% | {100*r.std()*math.sqrt(252):.1f}% | "
                 f"{sharpe_excess(r, cash.reindex(r.index)):.2f} | {100*pp['maxdd']:.0f}% |")
    L.append("")

    # 4. realistic version
    real = run(make_tsmom((63, 126, 252), cap=2.0), 10.0, 0.02)
    eqr = eq.reindex(real.index)
    mix = 0.6 * eqr + 0.4 * real
    g = full_rigor(f"{name}: realistic TSMOM excess", real - cash.reindex(real.index), n_trials)
    bt = sharpe_diff_bootstrap(mix, eqr, cash, n=n_boot)
    crit = 0.05 / n_trials
    L.append("### 4 — Realistic version (blend 3/6/12, 10 bps, 2% borrow, gross ≤ 2)")
    L.append("| Portfolio | CAGR | vol | Sharpe (excess) | max DD | Sharpe ≤2012 | Sharpe >2012 |")
    L.append("|---|--:|--:|--:|--:|--:|--:|")
    for lbl, r in (("TSMOM realistic", real), (f"{eq_key}", eqr), ("60/40 equity + TSMOM", mix)):
        pp = perf(r)
        pre, post = r.loc[:PUB], r.loc["2013-01-01":]
        f = lambda x: f"{sharpe_excess(x, cash.reindex(x.index)):.2f}" if len(x) > 250 else "—"
        L.append(f"| {lbl} | {100*pp['cagr']:+.1f}% | {100*r.std()*math.sqrt(252):.1f}% | "
                 f"{sharpe_excess(r, cash.reindex(r.index)):.2f} | {100*pp['maxdd']:.0f}% | {f(pre)} | {f(post)} |")
    real_ok = g.get("sig_after_haircut", False)
    L.append("")
    L.append(f"Rigor (TSMOM realistic excess): p={g.get('p_value')}, sig after haircut "
             f"{'✅' if real_ok else '❌'}, walk-fwd {g.get('wf_pct')}%, regimes+ {g.get('regime_positive')}, "
             f"{g.get('verdict')}. 60/40 Sharpe gain {bt['obs']:+.2f} [{bt['lo']:+.2f}, {bt['hi']:+.2f}], "
             f"p={bt['p']:.4f} {'✅' if bt['p'] < crit and bt['obs'] > 0 else '❌'}.")
    L.append("")

    # 5. dry spells
    L.append("### 5 — Dry spells")
    L.append("| Portfolio | longest under water | worst 3y return | % of 3y windows < 0 | worst 3y Sharpe |")
    L.append("|---|--:|--:|--:|--:|")
    for lbl, r in (("TSMOM realistic", real), (f"{eq_key}", eqr), ("60/40 equity + TSMOM", mix)):
        d = dry_spells(r, cash)
        L.append(f"| {lbl} | {d['under_years']:.1f} y | {100*d['worst3y']:+.0f}% | "
                 f"{100*d['neg3y']:.0f}% | {d['worst_sh3']:+.2f} |")
    L.append("")

    # 6. placebo
    real12 = run(make_tsmom((252,)))
    sh_real = sharpe_excess(real12, cash.reindex(real12.index))
    rng = np.random.default_rng(41)
    plc = []
    for _ in range(n_placebo):
        r = run(make_tsmom((252,), placebo_rng=rng))
        plc.append(sharpe_excess(r, cash.reindex(r.index)))
    plc = np.array(plc)
    p_plc = float((plc >= sh_real).mean())
    L.append(f"### 6 — Placebo ({n_placebo} random-sign runs, identical machinery, 12m, 5 bps)")
    L.append(f"Real trend Sharpe {sh_real:.2f}; placebo median {np.median(plc):.2f}, 95th pct "
             f"{np.percentile(plc, 95):.2f}, max {plc.max():.2f}; share of placebo ≥ real: {p_plc:.2f}.")
    L.append("")
    L.append(f"**Summary {name}:** horizons significant {h_sig}/6; cost cells with positive excess "
             f"Sharpe {cost_pos}/9; realistic version sig {'yes' if real_ok else 'no'}; placebo p={p_plc:.2f}.")
    L.append("")
    return L


def run_experiment41_report(universes: dict, irx: pd.Series, n_trials: int = 165,
                            n_placebo: int = 100, n_boot: int = 3000) -> str:
    from datetime import datetime, timezone
    lines = [f"# Experiment #41 — hardening multi-asset trend following "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"Cash = 13-week T-bill {'(^IRX)' if irx is not None and len(irx) > 1000 else '(MISSING → 0%)'}; "
                 f"haircut α/{n_trials}.")
    lines.append("")
    for name, (prices, eq_key) in universes.items():
        lines += universe41(name, prices, eq_key, irx, n_trials, n_placebo, n_boot)
    return "\n".join(lines)
