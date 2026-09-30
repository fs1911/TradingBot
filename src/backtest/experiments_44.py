"""
Experiment #44 — backtest of the EXACT live portfolio rule (src/strategies/trend_portfolio.py).

The bot now runs a long-only multi-asset trend portfolio (#40/#41) with BTC and ETH
added and a 3/6/12-month blend — a combination that was never tested as such. Before
trusting it, run the very same target_weights() function month by month on Yahoo
total-return prices (2006→), with turnover costs of 5 bps (ETFs) and 25 bps (crypto,
Alpaca taker fee) and cash earning BIL.

Compared: live rule, live rule without crypto, equal-weight buy & hold of the ETFs,
SPY, 60/40 SPY/IEF. Sensitivity: target vol 8/10/15%, crypto cap 5/10/20%.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from ..strategies.trend_portfolio import build_panel, target_weights
from .experiments_38 import _naive

CRISES = (("2008–09 GFC", "2007-10-09", "2009-03-09"), ("2020 Covid", "2020-02-19", "2020-03-23"),
          ("2022 bear", "2022-01-03", "2022-10-12"))


def month_end_idx(idx: pd.DatetimeIndex) -> list:
    per = pd.Series(idx.to_period("M"), index=idx)
    return [i for i, (a, b) in enumerate(zip(per, per.shift(-1))) if a != b]


def backtest_rule(panel: pd.DataFrame, universe: list, cash_col: str = "BIL",
                  cost_etf_bps: float = 5.0, cost_crypto_bps: float = 25.0, **kw) -> tuple:
    """Monthly: weights from data up to the month-end close, held from the next day.
    Returns (daily portfolio returns, avg gross, turnover per year)."""
    rets = panel.pct_change(fill_method=None)
    cash = rets[cash_col].fillna(0.0) if cash_col in rets else pd.Series(0.0, index=rets.index)
    cols = [c for c in universe if c in panel.columns]
    mes = month_end_idx(panel.index)
    out = pd.Series(np.nan, index=panel.index)
    prev = pd.Series(0.0, index=cols)
    gross, turn = [], 0.0
    for k, m in enumerate(mes[:-1]):
        hist = panel.iloc[: m + 1][cols + [cash_col]]
        w = target_weights(hist, cash_col=cash_col, **kw).reindex(cols).fillna(0.0)
        s, e = m + 1, mes[k + 1] + 1
        blk = rets.iloc[s:e][cols].fillna(0.0)
        c = cash.iloc[s:e]
        pr = c + (blk.sub(c, axis=0) * w).sum(axis=1)
        dw = (w - prev).abs()
        cost = sum(dw[a] * (cost_crypto_bps if "/" in a or "-USD" in a else cost_etf_bps) / 1e4 for a in cols)
        if len(pr):
            pr.iloc[0] -= cost
        out.iloc[s:e] = pr.to_numpy()
        gross.append(float(w.sum()))
        turn += float(dw.sum())
        prev = w
    r = out.dropna()
    yrs = max(len(r) / 252, 1e-9)
    return r, float(np.mean(gross)) if gross else 0.0, turn / yrs


def stats(r: pd.Series, cash: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 260:
        return {}
    eq = (1 + r).cumprod()
    x = r - cash.reindex(r.index).fillna(0.0)
    yearly = (1 + r).groupby(r.index.year).prod() - 1
    sh = lambda z: float(z.mean() / z.std() * math.sqrt(252)) if z.std() > 0 else float("nan")
    pre, post = x.loc[:"2012-12-31"], x.loc["2013-01-01":]
    return {"cagr": float(eq.iloc[-1] ** (252 / len(r)) - 1), "vol": float(r.std() * math.sqrt(252)),
            "sharpe": sh(x), "maxdd": float((eq / eq.cummax() - 1).min()),
            "worst_year": float(yearly.min()), "worst_year_y": int(yearly.idxmin()),
            "pre": sh(pre) if len(pre) > 260 else float("nan"),
            "post": sh(post) if len(post) > 260 else float("nan")}


def run_experiment44_report(prices: dict, live_universe: list, symbol_map: dict,
                            cash_sym: str = "BIL", calendar: str = "SPY",
                            horizons=(91, 182, 365), target_vol: float = 0.10,
                            caps: dict | None = None) -> str:
    """prices: {yahoo symbol: Series}; symbol_map: live symbol → yahoo symbol."""
    from datetime import datetime, timezone
    inv = {v: k for k, v in symbol_map.items()}
    closes = {inv.get(k, k): _naive(v) for k, v in prices.items() if v is not None and len(v) > 300}
    panel = build_panel(closes, calendar)
    L = [f"# Experiment #44 — backtest of the exact live trend-portfolio rule "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    have = [u for u in live_universe if u in panel.columns]
    L.append(f"Assets with data: {len(have)}/{len(live_universe)} "
             f"(missing: {', '.join(u for u in live_universe if u not in panel.columns) or '—'}). "
             f"Cash = {cash_sym} {'ok' if cash_sym in panel.columns else 'MISSING'}.")
    if panel.empty or calendar not in panel.columns or cash_sym not in panel.columns:
        return "\n".join(L + ["", "Insufficient data."])
    start = panel[calendar].first_valid_index() + pd.Timedelta(days=400)
    rets = panel.pct_change(fill_method=None)
    cash = rets[cash_sym].fillna(0.0)
    caps = caps or {"BTC/USD": 0.10, "ETH/USD": 0.10}
    kw = dict(horizons=horizons, target_vol=target_vol, max_gross=1.0, max_weight=0.25, caps=caps)
    etfs = [u for u in have if "/" not in u]

    runs = {}
    live, g_live, t_live = backtest_rule(panel, have, cash_sym, **kw)
    runs["Live rule (ETFs + BTC/ETH)"] = (live, g_live, t_live)
    noc, g_noc, t_noc = backtest_rule(panel, etfs, cash_sym, **kw)
    runs["Live rule without crypto"] = (noc, g_noc, t_noc)
    ew = rets[etfs].loc[start:].mean(axis=1)
    runs["EW buy & hold (ETFs, daily rebal.)"] = (ew, 1.0, float("nan"))
    runs["SPY buy & hold"] = (rets[calendar].loc[start:], 1.0, 0.0)
    if "IEF" in rets:
        runs["60/40 SPY/IEF"] = (0.6 * rets[calendar].loc[start:] + 0.4 * rets["IEF"].loc[start:], 1.0, float("nan"))

    L.append(f"Evaluated {start:%Y-%m-%d} → {panel.index[-1]:%Y-%m-%d}; monthly rebalance; costs 5 bps ETF / "
             f"25 bps crypto per unit turnover; cash = {cash_sym}.")
    L.append("")
    L.append("| Portfolio | CAGR | vol | Sharpe (excess) | max DD | worst year | Sharpe ≤2012 | Sharpe >2012 | "
             "avg invested | turnover/yr |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for name, (r, g, t) in runs.items():
        st = stats(r.loc[start:], cash)
        if not st:
            L.append(f"| {name} | — |")
            continue
        L.append(f"| {name} | {100*st['cagr']:+.1f}% | {100*st['vol']:.1f}% | {st['sharpe']:.2f} | "
                 f"{100*st['maxdd']:.0f}% | {100*st['worst_year']:+.0f}% ({st['worst_year_y']}) | "
                 f"{st['pre']:.2f} | {st['post']:.2f} | {100*g:.0f}% | "
                 f"{'—' if not np.isfinite(t) else f'{100*t:.0f}%'} |")
    L.append("")
    L.append("### Crises (total return)")
    L.append("| Crisis | " + " | ".join(runs) + " |")
    L.append("|---|" + "--:|" * len(runs))
    for lbl, a, b in CRISES:
        cells = []
        for r, _, _ in runs.values():
            seg = r.loc[a:b]
            cells.append(f"{100*((1+seg).prod()-1):+.0f}%" if len(seg) > 5 else "—")
        L.append(f"| {lbl} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("### Sensitivity of the live rule (Sharpe excess / max DD / CAGR)")
    L.append("| variant | Sharpe | max DD | CAGR |")
    L.append("|---|--:|--:|--:|")
    for lbl, over in (("target vol 8%", {"target_vol": 0.08}), ("target vol 15%", {"target_vol": 0.15}),
                      ("crypto cap 5%", {"caps": {k: 0.05 for k in caps}}),
                      ("crypto cap 20%", {"caps": {k: 0.20 for k in caps}}),
                      ("12-month signal only", {"horizons": (365,)})):
        r, _, _ = backtest_rule(panel, have, cash_sym, **{**kw, **over})
        st = stats(r.loc[start:], cash)
        if st:
            L.append(f"| {lbl} | {st['sharpe']:.2f} | {100*st['maxdd']:.0f}% | {100*st['cagr']:+.1f}% |")
    L.append("")
    s_live, s_spy = stats(live.loc[start:], cash), stats(rets[calendar].loc[start:], cash)
    if s_live and s_spy:
        L.append(f"**Summary:** live rule CAGR {100*s_live['cagr']:+.1f}% vs SPY {100*s_spy['cagr']:+.1f}%, "
                 f"max DD {100*s_live['maxdd']:.0f}% vs {100*s_spy['maxdd']:.0f}%, Sharpe {s_live['sharpe']:.2f} vs "
                 f"{s_spy['sharpe']:.2f}; since 2013 {s_live['post']:.2f} vs {s_spy['post']:.2f}.")
    return "\n".join(L)
