"""
Experiments #53–#55 — what a private saver can actually use.

#53 (H2) Buy after crashes: when a market first falls 20 / 30 / 40 % below its all-time
    high (once per bear episode), what were the returns over the next 1, 3 and 5 years —
    versus all months? Bootstrap: share of random month sets with an equal or higher mean.
#54 (H3) Counter-cyclical savings plan: income 1 per month, same total money in every
    strategy. DCA invests 1 every month. Reserve strategies invest 0.8 and park 0.2 in cash;
    in a crash they invest extra from the reserve:
      R20  drawdown ≤ −20 %: invest 1 + min(reserve, 1) per month
      R30  drawdown first ≤ −30 % in an episode: invest the whole reserve at once
      RTR  trend score ≤ 1 (3/6/12-month returns vs cash, #45): invest 1 + min(reserve, 1)
    Compared over all rolling 20- and 30-year windows: final wealth vs DCA.
#55 (H4) What matters most: savings rate, fees, start age (horizon) or strategy?
    Real (inflation-adjusted) S&P total return, all rolling start months: final wealth of a
    monthly plan for different horizons, fees and savings — next to the size of the best
    strategy effects found in this project.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


# ── data helpers ──────────────────────────────────────────────────────────────

def shiller_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Shiller frame (price, div, cpi, gs10) → monthly nominal TR, real TR, price level,
    cash proxy (gs10 − 1 pt, floored at 0) on a Period index."""
    d = df.copy()
    d.index = pd.to_datetime(d.index).to_period("M")
    d = d[~d.index.duplicated(keep="last")].sort_index()
    tr = (d["price"] + d["div"].fillna(0) / 12) / d["price"].shift(1) - 1
    infl = d["cpi"] / d["cpi"].shift(1)
    real = (1 + tr) / infl - 1
    cash = ((d["gs10"] - 1.0).clip(lower=0) / 100 / 12).shift(1)
    return pd.DataFrame({"tr": tr, "real": real, "price": d["price"], "cash": cash}).dropna(subset=["tr"])


def monthly_from_daily(s: pd.Series) -> pd.Series:
    s = pd.Series(s).dropna()
    idx = pd.to_datetime(s.index)
    s.index = (idx.tz_localize(None) if idx.tz is not None else idx).to_period("M")
    return s.groupby(level=0).last()


def drawdown(level: pd.Series) -> pd.Series:
    return level / level.cummax() - 1


def crash_events(level: pd.Series, threshold: float) -> list:
    """First month per bear episode in which drawdown ≤ threshold (episode ends at a new high)."""
    dd = drawdown(level)
    ev, armed = [], True
    for t, v in dd.items():
        if v >= 0:
            armed = True
        elif armed and v <= threshold:
            ev.append(t)
            armed = False
    return ev


# ── #53 ───────────────────────────────────────────────────────────────────────

def fwd_returns(tr: pd.Series, months: int) -> pd.Series:
    g = (1 + tr).cumprod()
    return g.shift(-months) / g - 1


def crash_table(name: str, tr: pd.Series, level: pd.Series, rng, n_boot: int = 4000) -> list:
    L = [f"### {name} ({tr.index[0]} → {tr.index[-1]})",
         "| Trigger | events | 1Y after | 3Y after (p.a.) | 5Y after (p.a.) | worst 3Y | all months 3Y (p.a.) | "
         "bootstrap p (3Y) | dates |",
         "|---|--:|--:|--:|--:|--:|--:|--:|---|"]
    f12, f36, f60 = fwd_returns(tr, 12), fwd_returns(tr, 36), fwd_returns(tr, 60)
    base36 = f36.dropna()
    ann = lambda x, y: (1 + x) ** (1 / y) - 1 if np.isfinite(x) else float("nan")
    for th in (-0.20, -0.30, -0.40):
        ev = [e for e in crash_events(level, th) if e in tr.index]
        e36 = f36.reindex(ev).dropna()
        if not ev:
            L.append(f"| {int(th*100)} % | 0 | — | — | — | — | — | — | — |")
            continue
        p = float("nan")
        if len(e36) >= 2 and len(base36) > 50:
            draws = np.array([rng.choice(base36.to_numpy(), len(e36)).mean() for _ in range(n_boot)])
            p = float((draws >= e36.mean()).mean())
        L.append(f"| {int(th*100)} % | {len(ev)} | {100*f12.reindex(ev).mean():+.1f}% | "
                 f"{100*ann(e36.mean(), 3):+.1f}% | {100*ann(f60.reindex(ev).dropna().mean(), 5):+.1f}% | "
                 f"{100*e36.min():+.0f}% | {100*ann(base36.mean(), 3):+.1f}% | {p:.3f} | "
                 f"{', '.join(str(e) for e in ev[:8])}{' …' if len(ev) > 8 else ''} |")
    L.append("")
    return L


# ── #54 ───────────────────────────────────────────────────────────────────────

def trend_score_m(level: pd.Series, cash: pd.Series) -> pd.Series:
    cidx = (1 + cash.fillna(0)).cumprod()
    sc = sum(((level / level.shift(h) - 1) > (cidx / cidx.shift(h) - 1)).astype(float) for h in (3, 6, 12))
    return sc.where(level.shift(12).notna())


def simulate(tr: pd.Series, cash: pd.Series, level: pd.Series, score: pd.Series, rule: str) -> float:
    """Final wealth (stocks + reserve) of a 1-per-month plan over the given window."""
    dd = drawdown(level)
    stock, reserve, armed = 0.0, 0.0, True
    for t in tr.index:
        stock *= 1 + tr[t]
        reserve *= 1 + (cash.get(t, 0.0) if np.isfinite(cash.get(t, np.nan)) else 0.0)
        d = dd.get(t, 0.0)
        if rule == "DCA":
            stock += 1.0
            continue
        invest, reserve = 0.8, reserve + 0.2
        if d >= 0:
            armed = True
        if rule == "R20" and d <= -0.20:
            x = min(reserve, 1.0); invest += x; reserve -= x
        elif rule == "R30" and d <= -0.30 and armed:
            invest += reserve; reserve = 0.0; armed = False
        elif rule == "RTR" and score.get(t, 3) <= 1:
            x = min(reserve, 1.0); invest += x; reserve -= x
        stock += invest
    return stock + reserve


def window_compare(tr: pd.Series, cash: pd.Series, level: pd.Series, years: int, step: int = 12) -> dict:
    score = trend_score_m(level, cash)
    n = years * 12
    out = {r: [] for r in ("R20", "R30", "RTR")}
    for start in range(0, len(tr) - n + 1, step):
        idx = tr.index[start:start + n]
        w = {r: simulate(tr.loc[idx], cash.reindex(idx).fillna(0), level, score, r) for r in ("DCA", "R20", "R30", "RTR")}
        for r in out:
            out[r].append(w[r] / w["DCA"])
    return {r: np.array(v) for r, v in out.items()}


# ── #55 ───────────────────────────────────────────────────────────────────────

def plan_wealth(real: pd.Series, months: int, monthly: float, fee_pa: float, step: int = 12) -> np.ndarray:
    """Final real wealth of `monthly` saved for `months`, all start months (every `step`)."""
    r = (1 + real.to_numpy()) * (1 - fee_pa / 12) - 1
    out = []
    for s in range(0, len(r) - months + 1, step):
        w = 0.0
        for x in r[s:s + months]:
            w = (w + monthly) * (1 + x)
        out.append(w)
    return np.array(out)


# ── report ─────────────────────────────────────────────────────────────────────

def run_experiments53_55_report(shiller: pd.DataFrame, markets: dict, irx: pd.Series | None = None) -> str:
    """markets: {name: (daily close Series, is_total_return)} from Yahoo."""
    from datetime import datetime, timezone
    rng = np.random.default_rng(53)
    L = [f"# Experiments #53–#55 — crash buying, counter-cyclical savings, what really matters "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    sm = shiller_monthly(shiller) if shiller is not None and not shiller.empty else pd.DataFrame()
    series = {}
    if not sm.empty:
        lvl = (1 + sm["tr"]).cumprod()
        series["S&P 500 TR (Shiller, 1871→)"] = (sm["tr"], sm["price"], sm["cash"])
    irx_m = monthly_from_daily(irx) / 100 / 12 if irx is not None and len(irx) else None
    for name, (daily, _) in markets.items():
        if daily is None or len(daily) < 600:
            continue
        lv = monthly_from_daily(daily)
        tr = lv.pct_change().dropna()
        cash = irx_m.shift(1).reindex(tr.index).fillna(0.0) if irx_m is not None else pd.Series(0.0, index=tr.index)
        series[name] = (tr, lv.reindex(tr.index), cash)

    L.append("## #53 (H2) — buying after crashes")
    L.append("Trigger = first month per bear market in which the index is X % below its all-time high. Returns are "
             "total return where available (Shiller, funds), else price only. Bootstrap p = share of random month sets "
             "(same size) with an equal or higher 3-year return.")
    L.append("")
    for name, (tr, lv, _) in series.items():
        L += crash_table(name, tr, lv, rng)

    L.append("## #54 (H3) — counter-cyclical savings plan (same total money)")
    L.append("Final wealth relative to plain DCA over all rolling windows (start every 12 months). Reserve earns cash "
             "(T-bill where available; Shiller: 10-year yield − 1 pt).")
    L.append("")
    L.append("| Market | window | rule | median vs DCA | % windows better | worst | best |")
    L.append("|---|--:|---|--:|--:|--:|--:|")
    for name, (tr, lv, cash) in series.items():
        for yrs in (20, 30):
            if len(tr) < yrs * 12 + 12:
                continue
            res = window_compare(tr, cash, lv, yrs)
            for r, v in res.items():
                if len(v):
                    L.append(f"| {name} | {yrs} y | {r} | {100*(np.median(v)-1):+.1f}% | {100*(v > 1).mean():.0f}% | "
                             f"{100*(v.min()-1):+.1f}% | {100*(v.max()-1):+.1f}% |")
    L.append("")

    L.append("## #55 (H4) — what matters most for a saver (real S&P total return, Shiller)")
    if sm.empty:
        L.append("Shiller data missing.")
    else:
        real = sm["real"].dropna()
        L.append(f"Real (inflation-adjusted) monthly returns {real.index[0]} → {real.index[-1]}, every start year. "
                 f"Amounts in today's money; 500 per month unless stated.")
        L.append("")
        L.append("| Scenario | worst | 10 % | median | 90 % | best | total paid in |")
        L.append("|---|--:|--:|--:|--:|--:|--:|")
        scen = [("10 years, fee 0.2 %", 120, 500, 0.002), ("20 years, fee 0.2 %", 240, 500, 0.002),
                ("30 years, fee 0.2 %", 360, 500, 0.002), ("40 years, fee 0.2 %", 480, 500, 0.002),
                ("30 years, fee 1.0 %", 360, 500, 0.010), ("30 years, fee 2.0 %", 360, 500, 0.020),
                ("30 years, 300/month", 360, 300, 0.002), ("30 years, 1000/month", 360, 1000, 0.002)]
        med = {}
        for lbl, m, amt, fee in scen:
            w = plan_wealth(real, m, amt, fee)
            if not len(w):
                continue
            q = np.percentile(w, [10, 50, 90])
            med[lbl] = q[1]
            L.append(f"| {lbl} | {w.min():,.0f} | {q[0]:,.0f} | {q[1]:,.0f} | {q[2]:,.0f} | {w.max():,.0f} | {amt*m:,.0f} |")
        L.append("")
        if med:
            b = med.get("30 years, fee 0.2 %", np.nan)
            L.append("Median effect vs the 30-year / 500 / 0.2 % baseline:")
            for lbl in ("40 years, fee 0.2 %", "30 years, fee 1.0 %", "30 years, fee 2.0 %", "30 years, 1000/month"):
                if lbl in med:
                    L.append(f"- {lbl}: {100*(med[lbl]/b-1):+.0f}%")
            for lbl, extra in (("strategy +1 %/yr (e.g. buyback tilt after costs, optimistic)", 0.01),
                               ("strategy +2.6 %/yr (#50 best case, before costs/taxes)", 0.026)):
                w = plan_wealth(real, 360, 500, 0.002 - extra)
                L.append(f"- {lbl}: {100*(np.median(w)/b-1):+.0f}%")
    return "\n".join(L)
