"""
Experiments #70 and #72 — two classic saver questions on 150 years of real US data
(Shiller: S&P total return, 10-year bonds from yields, CPI).

#70 Lump sum vs staged entry, SAME money: an amount available today is either invested at
    once, or in 6 / 12 / 24 equal monthly parts (rest earns cash = 10-y yield − 1 pt).
    Real wealth after 10 years, every start month: how often does the lump sum win, by how
    much on average, and how bad is its worst case relative to staging?
#72 Retirement withdrawals: 30-year retirements starting every year, inflation-adjusted
    withdrawal of 3 / 3.5 / 4 / 4.5 / 5 % of the starting value, portfolios 100/0, 80/20,
    60/40, 40/60 stocks/bonds rebalanced yearly. Success = money lasts 30 years; worst start
    years; median money left (in multiples of the start value, real).
Caveat: US history only (the most successful market of the century → optimistic, cf. #53
Nikkei); Shiller prices are monthly averages (mild smoothing).
Pure, injected for CI.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def real_series(shiller: pd.DataFrame) -> pd.DataFrame:
    """Monthly real returns: stocks (TR), bonds (10-y from yields, duration 7), cash."""
    from .experiments_34 import real_stock_returns, real_bond_returns
    d = shiller.copy()
    d.index = pd.to_datetime(d.index).to_period("M")
    d = d[~d.index.duplicated(keep="last")].sort_index()
    infl = d["cpi"] / d["cpi"].shift(1)
    cash_nom = ((d["gs10"] - 1.0).clip(lower=0) / 100 / 12).shift(1)
    out = pd.DataFrame({"stock": real_stock_returns(d), "bond": real_bond_returns(d),
                        "cash": (1 + cash_nom) / infl - 1})
    return out.dropna()


def lump_vs_staged(r: pd.DataFrame, parts: int, years: int = 10) -> np.ndarray:
    """Ratio final(lump) / final(staged) for every start month."""
    s, c = r["stock"].to_numpy(), r["cash"].to_numpy()
    n = years * 12
    out = []
    for t0 in range(0, len(s) - n):
        lump = np.prod(1 + s[t0:t0 + n])
        st, cash = 0.0, 1.0
        for k in range(n):
            if k < parts:
                add = cash / (parts - k)
                cash -= add
                st += add
            st *= 1 + s[t0 + k]
            cash *= 1 + c[t0 + k]
        out.append(lump / (st + cash))
    return np.array(out)


def retirement(r: pd.DataFrame, w_stock: float, rate: float, years: int = 30) -> tuple:
    """Yearly steps (annual compounding of monthly returns), withdrawal at the start of each
    year, rebalanced yearly. → (success share, worst start, median final, starts list)."""
    yr = (1 + r).groupby(r.index.year).prod() - 1
    yr = yr[(r.groupby(r.index.year).size() == 12).to_numpy()]
    pr = w_stock * yr["stock"] + (1 - w_stock) * yr["bond"]
    years_idx = list(pr.index)
    res = []
    for i in range(len(years_idx) - years + 1):
        v = 1.0
        ok = True
        for k in range(years):
            v -= rate
            if v <= 0:
                ok = False
                break
            v *= 1 + pr.iloc[i + k]
        res.append((years_idx[i], ok, max(v, 0.0)))
    if not res:
        return float("nan"), None, float("nan"), []
    succ = np.mean([x[1] for x in res])
    finals = [x[2] for x in res]
    worst = min(res, key=lambda x: x[2])
    fails = [x[0] for x in res if not x[1]]
    return float(succ), worst[0], float(np.median(finals)), fails


def run_experiments70_72_report(shiller: pd.DataFrame) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiments #70 / #72 — lump sum vs staging, retirement withdrawals "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if shiller is None or shiller.empty:
        return "\n".join(L + ["Shiller data missing."])
    r = real_series(shiller)
    L.append(f"Real monthly returns {r.index[0]} → {r.index[-1]} (Shiller).")
    L.append("")
    L.append("## #70 Lump sum vs staged entry (same money, real wealth after 10 years)")
    L.append("| staged over | start months | lump sum wins | avg advantage of lump sum | lump sum's worst case vs staging | best case |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for parts in (6, 12, 24):
        x = lump_vs_staged(r, parts)
        L.append(f"| {parts} months | {len(x):,} | {100*(x > 1).mean():.0f} % | {100*(x.mean()-1):+.1f} % | "
                 f"{100*(x.min()-1):+.1f} % | {100*(x.max()-1):+.1f} % |")
    L.append("")
    L.append("## #72 Retirement: does the money last 30 years? (withdrawal = % of the start value, inflation-adjusted)")
    L.append("| stocks/bonds | 3 % | 3.5 % | 4 % | 4.5 % | 5 % | median left after 30 y at 4 % | worst start year at 4 % |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|")
    for ws in (1.0, 0.8, 0.6, 0.4):
        cells, med4, worst4 = [], None, None
        for rate in (0.03, 0.035, 0.04, 0.045, 0.05):
            succ, worst, med, fails = retirement(r, ws, rate)
            cells.append(f"{100*succ:.0f} %")
            if rate == 0.04:
                med4, worst4 = med, worst
        L.append(f"| {int(ws*100)}/{int(100-ws*100)} | " + " | ".join(cells) +
                 f" | ×{med4:.1f} | {worst4} |")
    succ, _, _, fails = retirement(r, 0.6, 0.045)
    if fails:
        L.append("")
        L.append(f"60/40 at 4.5 % failed for retirements starting in: {', '.join(map(str, fails[:20]))}"
                 f"{' …' if len(fails) > 20 else ''}.")
    L.append("")
    L.append("Reading: success rates are for the US, the best-performing market of the period — for other countries "
             "(Japan, much of Europe) safe rates were lower. 'Median left' shows how often the rule leaves a lot unused.")
    return "\n".join(L)
