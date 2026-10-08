"""
Experiment #47 — the MARKET signal applied to single stocks.

#45: a stock's OWN trend signal fails on single stocks (entry-vs-exit 12M −5.5 pts).
#46: on equity INDICES the trend score + macro vote cuts false exits and halves
drawdowns. In big bear markets almost all stocks fall together, so can the index
signal protect a portfolio of single stocks?

Per stock (US large caps, SMI, DAX; monthly; costs 10 bps per unit turnover):
  B&H            — hold the stock
  Own trend      — the stock's own 3/6/12M score (#45)
  Market trend   — the home index's 3/6/12M score applied to the stock
  Market + macro — index score only when ≥2 of unemployment/credit/curve show stress,
                   otherwise fully invested (#46, F6)
Reported per region: median CAGR, max DD, Sharpe, before/after 2013, share of stocks
with a smaller drawdown / higher Sharpe than B&H, crisis returns of an equal-weight
portfolio, and a PLACEBO: the market weight series circularly shifted (same k for all
stocks of the region) — is the market TIMING informative for single stocks?
Survivorship: today's constituents (B&H flattered → biased AGAINST timing).
Pure, injected for CI.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .experiments_45 import monthly_closes, monthly_cash, trend_score, follow, mstats
from .experiments_46 import stress_series, filtered_weight, crisis_ret

CRISES = (("2000–02", "2000-04", "2002-09"), ("2008–09", "2007-11", "2009-02"),
          ("2011", "2011-05", "2011-09"), ("2018 Q4", "2018-10", "2018-12"),
          ("2020", "2020-02", "2020-03"), ("2022", "2022-01", "2022-09"))
VARIANTS = ("B&H", "Own trend", "Market trend", "Market + macro")


def market_weights(index_daily: pd.Series, irx: pd.Series, macro: dict) -> tuple:
    """Monthly market weights (trend, trend+macro) and the index cash series."""
    px = monthly_closes(index_daily)
    cash = monthly_cash(irx, px.index)
    sc = trend_score(px, cash).dropna()
    st = stress_series(macro, sc.index).get("F6 macro vote (≥2 of F1–F3)")
    wm = sc / 3.0
    wmm = filtered_weight(sc, st) if st is not None and st.notna().sum() > 24 else wm
    return wm, wmm


def stock_runs(daily: pd.Series, irx: pd.Series, wm: pd.Series, wmm: pd.Series,
               cost_bps: float = 10.0) -> dict | None:
    if daily is None or len(daily) < 600:
        return None
    px = monthly_closes(daily)
    px = px[px > 0]
    cash = monthly_cash(irx, px.index)
    own = trend_score(px, cash).dropna()
    idx = own.index.intersection(wm.index)
    if len(idx) < 60:
        return None
    px, cash = px.loc[idx], cash.loc[idx]
    w = {"B&H": pd.Series(1.0, index=idx), "Own trend": own.loc[idx] / 3.0,
         "Market trend": wm.loc[idx], "Market + macro": wmm.reindex(idx).fillna(wm.loc[idx])}
    rets = {k: follow(px, cash, v, 0.0 if k == "B&H" else cost_bps) for k, v in w.items()}
    return {"rets": rets, "stats": {k: mstats(r, cash) for k, r in rets.items()}, "cash": cash,
            "px": px}


def region_placebo(stocks: dict, irx: pd.Series, wm: pd.Series, n_shifts: int = 200,
                   min_shift: int = 24) -> tuple:
    """Median Sharpe gain (market-timed − B&H) across stocks: real vs shifted market
    weight series (same shift for all stocks)."""
    def gain(wser):
        g = []
        for d in stocks.values():
            px, cash = d["px"], d["cash"]
            ww = wser.reindex(px.index)
            if ww.isna().all():
                continue
            s1 = mstats(follow(px, cash, ww.fillna(1.0), 10.0), cash)
            s0 = d["stats"]["B&H"]
            if s1 and s0:
                g.append(s1["sharpe"] - s0["sharpe"])
        return float(np.median(g)) if g else float("nan")
    real = gain(wm)
    vals = wm.to_numpy()
    n = len(vals)
    ks = np.linspace(min_shift, n - min_shift, num=min(n_shifts, max(1, n - 2 * min_shift))).astype(int)
    plc = np.array([gain(pd.Series(np.roll(vals, k), index=wm.index)) for k in ks])
    plc = plc[np.isfinite(plc)]
    if not len(plc):
        return real, float("nan")
    return real, max(float((plc >= real).mean()), 1.0 / (len(plc) + 1))


def _p(x, d=0):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:+.{d}f}%"


def run_experiment47_report(regions: dict, irx: pd.Series, macro: dict, sources: dict | None = None,
                            n_trials: int = 222, n_shifts: int = 200) -> str:
    """regions: {name: (prices {ticker: daily}, index daily Series)}."""
    from datetime import datetime, timezone
    L = [f"# Experiment #47 — market signal applied to single stocks "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if sources:
        L.append("Macro sources: " + "; ".join(f"{k}: {v}" for k, v in sources.items()) + ".")
    L.append("Variants: B&H; own 3/6/12M trend (#45); home-index trend applied to the stock; index trend only "
             "under macro stress (≥2 of unemployment/credit/curve, #46). Monthly, 10 bps. Survivorship: today's "
             "constituents.")
    L.append("")
    summary = []
    for reg, (prices, index_daily) in regions.items():
        L.append(f"## {reg}")
        L.append("")
        if index_daily is None or len(index_daily) < 600:
            L += ["Index data missing.", ""]
            continue
        wm, wmm = market_weights(index_daily, irx, macro)
        stocks = {t: r for t, d in prices.items() if (r := stock_runs(d, irx, wm, wmm))}
        if len(stocks) < 5:
            L += [f"Only {len(stocks)} stocks with data.", ""]
            continue
        L.append(f"{len(stocks)} stocks; market invested {100*wm.mean():.0f}% (trend) / "
                 f"{100*wmm.mean():.0f}% (trend+macro) of months.")
        L.append("")
        L.append("| Variant | median CAGR | median max DD | median Sharpe | Sharpe ≤2012 | Sharpe >2012 | "
                 "stocks with smaller DD than B&H | stocks with higher Sharpe than B&H |")
        L.append("|---|--:|--:|--:|--:|--:|--:|--:|")
        med = lambda k, f: float(np.nanmedian([s["stats"][k].get(f, np.nan) for s in stocks.values()
                                               if s["stats"][k]]))
        for k in VARIANTS:
            better_dd = sum(s["stats"][k]["maxdd"] > s["stats"]["B&H"]["maxdd"] for s in stocks.values()
                            if s["stats"][k] and s["stats"]["B&H"]) if k != "B&H" else None
            better_sh = sum(s["stats"][k]["sharpe"] > s["stats"]["B&H"]["sharpe"] for s in stocks.values()
                            if s["stats"][k] and s["stats"]["B&H"]) if k != "B&H" else None
            L.append(f"| {k} | {_p(med(k, 'cagr'), 1)} | {_p(med(k, 'maxdd'))} | {med(k, 'sharpe'):.2f} | "
                     f"{med(k, 'pre'):.2f} | {med(k, 'post'):.2f} | "
                     f"{'—' if better_dd is None else f'{better_dd}/{len(stocks)}'} | "
                     f"{'—' if better_sh is None else f'{better_sh}/{len(stocks)}'} |")
        L.append("")
        # equal-weight portfolio of the stocks under each variant (crisis view)
        ew = {k: pd.concat([s["rets"][k] for s in stocks.values()], axis=1).mean(axis=1) for k in VARIANTS}
        cash_any = next(iter(stocks.values()))["cash"]
        L.append("Equal-weight portfolio of these stocks:")
        L.append("| Variant | CAGR | max DD | Sharpe | " + " | ".join(c[0] for c in CRISES) + " |")
        L.append("|---|--:|--:|--:|" + "--:|" * len(CRISES))
        for k, r in ew.items():
            s = mstats(r, cash_any.reindex(r.index).fillna(0.0))
            L.append(f"| {k} | {_p(s.get('cagr', np.nan), 1)} | {_p(s.get('maxdd', np.nan))} | "
                     f"{s.get('sharpe', float('nan')):.2f} | " +
                     " | ".join(_p(crisis_ret(r, a, b)) for _, a, b in CRISES) + " |")
        L.append("")
        real, p = region_placebo(stocks, irx, wm, n_shifts)
        real_m, p_m = region_placebo(stocks, irx, wmm, n_shifts)
        floor = 1.0 / (n_shifts + 1)
        fmt = lambda x: f"<{floor:.3f} (floor)" if x <= floor + 1e-12 else f"{x:.3f}"
        L.append(f"Placebo (market weights shifted, same k for all stocks): median Sharpe gain vs B&H "
                 f"market trend {real:+.3f} (p={fmt(p)}), market+macro {real_m:+.3f} (p={fmt(p_m)}).")
        L.append("")
        summary.append((reg, real, p, real_m, p_m))
    L.append("**Summary:** " + "; ".join(f"{r}: market trend ΔSharpe {a:+.2f} (p {b:.3f}), +macro {c:+.2f} "
                                          f"(p {d:.3f})" for r, a, b, c, d in summary) + ".")
    return "\n".join(L)
