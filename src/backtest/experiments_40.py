"""
Experiment #40 — trend following across many asset classes.

Everything so far tested trend rules on equity indices only. The best-documented
form of trend following is time-series momentum across a broad, diversified set of
asset classes (Moskowitz, Ooi & Pedersen 2012; Hurst, Ooi & Pedersen "A Century of
Evidence on Trend-Following"), valued mainly as "crisis alpha" next to equities.

Two universes (total-return prices via Yahoo adjclose, cash = 13-week T-bill):
  broad  — ~20 ETFs: equities, bonds, commodities, currencies (≈2006→)
  long   — Vanguard/Fidelity mutual funds: US & intl equity, long & intermediate
           Treasuries, high yield, precious-metal miners, energy, real estate (≈1987→)

Strategies (monthly rebalanced at month-end, applied from the next day, 5 bps per
unit turnover, excess-return accounting: portfolio = cash + Σ w·(r − cash)):
  EW buy & hold          — 1/N of the assets available (fair benchmark)
  Faber GTAA             — 1/N per asset only if above its 10-month SMA, else cash
  TSMOM long/short       — sign of 12m excess return, inverse-vol, 10% vol target, gross ≤ 3
  TSMOM long-only        — same, longs only, gross ≤ 1 (no leverage)
  S&P buy & hold         — the equity asset of the universe
  60/40 S&P + TSMOM L/S  — does trend help an equity portfolio?

Reported: CAGR, vol, excess Sharpe, max DD, correlation with the equity asset, avg
gross exposure; crisis returns; Sharpe before vs after publication (2012); full rigor
on TSMOM excess returns and on Faber − EW; paired bootstrap on the 60/40 Sharpe gain.
Pure, injected for CI.
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

PUB = "2012-12-31"
CRISES = (("1987 crash", "1987-08-25", "1987-12-04"),
          ("2000–02 dot-com", "2000-03-24", "2002-10-09"),
          ("2008–09 GFC", "2007-10-09", "2009-03-09"),
          ("2020 Covid", "2020-02-19", "2020-03-23"),
          ("2022 bear", "2022-01-03", "2022-10-12"))


def build_returns(prices: dict) -> pd.DataFrame:
    cols = {}
    for k, s in prices.items():
        if s is None or len(s) < 300:
            continue
        cols[k] = _naive(s)
    if not cols:
        return pd.DataFrame()
    px = pd.DataFrame(cols).sort_index().ffill(limit=5)
    return px.pct_change()


def month_end_positions(idx: pd.DatetimeIndex) -> list:
    per = pd.Series(idx.to_period("M"), index=idx)
    return [i for i, (a, b) in enumerate(zip(per, per.shift(-1))) if a != b]


def _active(hist: pd.DataFrame, min_days: int) -> list:
    return [c for c in hist.columns if hist[c].tail(min_days).notna().sum() >= min_days - 5]


def w_equal(hist, cash_hist, eq_key):
    act = _active(hist, 60)
    return pd.Series(1.0 / len(act), index=act) if act else pd.Series(dtype=float)


def w_faber(hist, cash_hist, eq_key):
    act = _active(hist, 215)
    if not act:
        return pd.Series(dtype=float)
    lvl = (1 + hist[act].fillna(0.0)).cumprod()
    up = lvl.iloc[-1] > lvl.tail(210).mean()
    return up.astype(float) / len(act)


def _tsmom(hist, cash_hist, long_only: bool, target: float = 0.10, cap: float = 3.0):
    act = _active(hist, 257)
    if not act:
        return pd.Series(dtype=float)
    r12 = (1 + hist[act].tail(252).fillna(0.0)).prod() - 1
    c12 = float((1 + cash_hist.tail(252)).prod() - 1)
    sig = np.sign(r12 - c12)
    if long_only:
        sig = sig.clip(lower=0.0)
    vol = hist[act].tail(60).std() * math.sqrt(252)
    raw = (sig / vol.replace(0, np.nan)).fillna(0.0)
    if (raw != 0).sum() == 0:
        return raw
    cov = hist[act].tail(120).fillna(0.0).cov().to_numpy() * 252
    pv = float(math.sqrt(max(raw.to_numpy() @ cov @ raw.to_numpy(), 1e-12)))
    w = raw * (target / pv)
    gross = w.abs().sum()
    lim = 1.0 if long_only else cap
    return w * (lim / gross) if gross > lim else w


def w_tsmom_ls(hist, cash_hist, eq_key):
    return _tsmom(hist, cash_hist, long_only=False)


def w_tsmom_lo(hist, cash_hist, eq_key):
    return _tsmom(hist, cash_hist, long_only=True)


def w_equity(hist, cash_hist, eq_key):
    return pd.Series({eq_key: 1.0}) if eq_key in hist.columns else pd.Series(dtype=float)


def run_strategy(rets: pd.DataFrame, cash: pd.Series, weight_fn, eq_key: str,
                 cost_bps: float = 5.0):
    """Daily returns + average gross exposure for a monthly-rebalanced weight rule."""
    idx = rets.index
    mes = month_end_positions(idx)
    out = pd.Series(np.nan, index=idx)
    prev = pd.Series(dtype=float)
    grosses = []
    for k, m in enumerate(mes[:-1]):
        hist = rets.iloc[: m + 1]
        w = weight_fn(hist, cash.iloc[: m + 1], eq_key)
        w = w.reindex(rets.columns).fillna(0.0)
        start, end = m + 1, mes[k + 1] + 1
        block = rets.iloc[start:end].fillna(0.0)
        c = cash.iloc[start:end]
        pr = c + (block.sub(c, axis=0) * w).sum(axis=1)
        turn = float((w - prev.reindex(w.index).fillna(0.0)).abs().sum())
        if len(pr):
            pr.iloc[0] -= turn * cost_bps / 1e4
        out.iloc[start:end] = pr.to_numpy()
        prev = w
        grosses.append(float(w.abs().sum()))
    return out.dropna(), (float(np.mean(grosses)) if grosses else 0.0)


def crisis(r: pd.Series, a: str, b: str) -> float:
    seg = r.loc[a:b]
    return float((1 + seg).prod() - 1) if len(seg) > 5 else float("nan")


def universe_report(name: str, prices: dict, eq_key: str, irx: pd.Series,
                    n_trials: int = 160, n_boot: int = 3000) -> list:
    lines = [f"## Universe: {name}", ""]
    rets = build_returns(prices)
    if rets.empty or eq_key not in rets.columns:
        lines.append(f"No usable data (equity asset {eq_key} missing).")
        return lines
    cash = cash_daily_returns(_naive(irx) if irx is not None and len(irx) else pd.Series(dtype=float),
                              rets.index)
    starts = {c: rets[c].first_valid_index() for c in rets.columns}
    missing = [k for k, s in prices.items() if s is None or len(s) < 300]
    lines.append("Assets (first date): " + ", ".join(f"{c} {starts[c]:%Y}" for c in rets.columns)
                 + (f". Missing: {', '.join(missing)}" if missing else "") + ".")
    lines.append("")

    rules = {"EW buy & hold": w_equal, "Faber GTAA (10m SMA)": w_faber,
             "TSMOM long/short (10% vol)": w_tsmom_ls, "TSMOM long-only": w_tsmom_lo,
             f"{eq_key} buy & hold": w_equity}
    res, gross = {}, {}
    for k, fn in rules.items():
        res[k], gross[k] = run_strategy(rets, cash, fn, eq_key)
    common = None
    for s in res.values():
        common = s.index if common is None else common.intersection(s.index)
    # common start: once the equity asset has a 12-month history (TSMOM warm-up)
    eq_first = rets.index.get_loc(rets[eq_key].first_valid_index())
    start = rets.index[min(len(rets.index) - 1, eq_first + 260)]
    for k in res:
        res[k] = res[k].loc[common].loc[start:]
    eq = res[f"{eq_key} buy & hold"]
    res["60/40 equity + TSMOM L/S"] = 0.6 * eq + 0.4 * res["TSMOM long/short (10% vol)"]
    gross["60/40 equity + TSMOM L/S"] = float("nan")
    c = cash.reindex(eq.index)
    lines.append(f"Evaluated {eq.index[0]:%Y-%m-%d} → {eq.index[-1]:%Y-%m-%d}.")
    lines.append("")
    lines.append("| Strategy | CAGR | vol | Sharpe (excess) | max DD | corr w/ equity | avg gross |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|")
    for k, r in res.items():
        p = perf(r)
        corr = float(r.corr(eq)) if k != f"{eq_key} buy & hold" else 1.0
        g = gross.get(k, float("nan"))
        lines.append(f"| {k} | {100*p['cagr']:+.1f}% | {100*r.std()*math.sqrt(252):.1f}% | "
                     f"{sharpe_excess(r, c):.2f} | {100*p['maxdd']:.0f}% | {corr:+.2f} | "
                     f"{'—' if g != g else f'{g:.2f}'} |")
    lines.append("")

    lines.append("| Crisis | " + " | ".join(res.keys()) + " |")
    lines.append("|---|" + "--:|" * len(res))
    for cname, a, b in CRISES:
        vals = [crisis(r, a, b) for r in res.values()]
        if all(v != v for v in vals):
            continue
        lines.append(f"| {cname} | " + " | ".join("—" if v != v else f"{100*v:+.0f}%" for v in vals) + " |")
    lines.append("")

    lines.append("| Sharpe (excess) | before 2013 | after 2012 |")
    lines.append("|---|--:|--:|")
    for k, r in res.items():
        pre, post = r.loc[:PUB], r.loc["2013-01-01":]
        f = lambda x: f"{sharpe_excess(x, cash.reindex(x.index)):.2f}" if len(x) > 250 else "—"
        lines.append(f"| {k} | {f(pre)} | {f(post)} |")
    lines.append("")

    ts = res["TSMOM long/short (10% vol)"]
    rig_ts = full_rigor(f"{name}: TSMOM L/S excess", ts - c, n_trials)
    rig_fb = full_rigor(f"{name}: Faber − EW", res["Faber GTAA (10m SMA)"] - res["EW buy & hold"], n_trials)
    bt = sharpe_diff_bootstrap(res["60/40 equity + TSMOM L/S"], eq, cash, n=n_boot)
    crit = 0.05 / n_trials
    lines.append("| Test | result |")
    lines.append("|---|---|")
    for lbl, rg in (("TSMOM L/S excess return > 0", rig_ts), ("Faber GTAA − EW buy & hold", rig_fb)):
        if rg.get("verdict") == "insufficient data":
            lines.append(f"| {lbl} | insufficient data |")
        else:
            lines.append(f"| {lbl} | p={rg['p_value']}, sig after haircut {'✅' if rg['sig_after_haircut'] else '❌'}, "
                         f"walk-fwd {rg['wf_pct']}%, regimes+ {rg['regime_positive']}, {rg['verdict']} |")
    lines.append(f"| 60/40 Sharpe − equity Sharpe (bootstrap) | {bt['obs']:+.2f}, 95% CI "
                 f"[{bt['lo']:+.2f}, {bt['hi']:+.2f}], p={bt['p']:.4f}, "
                 f"sig after haircut {'✅' if bt['p'] < crit and bt['obs'] > 0 else '❌'} |")
    lines.append("")
    return lines


def run_experiment40_report(universes: dict, irx: pd.Series, n_trials: int = 160,
                            n_boot: int = 3000) -> str:
    """universes: {name: (prices_dict, equity_key)}"""
    from datetime import datetime, timezone

    lines = [f"# Experiment #40 — trend following across asset classes "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append("Monthly rebalancing, total-return prices, cash = 13-week T-bill "
                 f"{'(^IRX)' if irx is not None and len(irx) > 1000 else '(MISSING → 0%)'}, "
                 f"5 bps per unit turnover. Haircut α/{n_trials}. Published: MOP 2012.")
    lines.append("")
    for name, (prices, eq_key) in universes.items():
        lines += universe_report(name, prices, eq_key, irx, n_trials, n_boot)
    return "\n".join(lines)
