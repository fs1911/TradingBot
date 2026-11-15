"""
Experiment #92 — backtest of the live Yuh scanner's stock colour (requested 15.11.2026).

The colour rule is imported from src/scanner/yuh_scanner.stock_colour, i.e. exactly what the
scanner sends today; nothing is tuned here. At every month-end 2010 → (today − 12 M), for every
US stock of the large-cap universe (SEC assets ≥ $1bn, price ≥ $5):
  trend      month-end close ≥ 200-trading-day average
  market     SPY ≥ its 200-day average
  momentum   12-1 month return, percentile among the stocks of that month
  shares     share-count change from the newest 10-K/10-Q FILED by that month-end (SEC, #65)
  young      first Yahoo price after 2005-02 and less than 3 years before the month-end
Outcomes: next 1 / 3 / 12 months, minus SPY; 'disaster' = 12-month return ≤ −40 % (as #65) and
3-month return ≤ −20 % vs SPY. Monthly portfolios (equal weight, rebalanced monthly): 🟢, 🔴 and the
whole universe, gross and net of 0.10 % and 0.50 % per trade side (0.50 % ≈ Yuh). Green − red
monthly spread with t-statistic (non-overlapping months); halves ≤ 2017 / 2018 →.
Caveat: survivorship — Yahoo has prices only for stocks still listed (biases every group upwards,
the red group probably the most, because failures tend to be red before they disappear).
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from ..scanner.yuh_scanner import stock_colour, GREEN, YELLOW, RED


def monthly_features(daily: pd.Series) -> pd.DataFrame:
    """Daily closes → month-end close, above-200-day flag, first price date (for IPO age)."""
    d = daily.dropna().astype("float32")
    if len(d) < 220:
        return pd.DataFrame()
    sma = d.rolling(200).mean()
    me = d.groupby(d.index.to_period("M")).tail(1)
    out = pd.DataFrame({"close": me.to_numpy(dtype=float),
                        "above": (me >= sma.reindex(me.index)).where(sma.reindex(me.index).notna()).to_numpy()},
                       index=me.index.to_period("M"))
    out.attrs["first"] = d.index[0]
    return out


def mom_12_1(close: pd.Series) -> pd.Series:
    return close.shift(1) / close.shift(12) - 1


def build_panel(feats: dict, share_ch, spy_feat: pd.DataFrame, months, first_cut: pd.Timestamp = pd.Timestamp("2005-02-01"),
                min_price: float = 5.0) -> pd.DataFrame:
    """feats: {ticker: monthly_features}; share_ch(ticker, period) → float. One row per (month, ticker)."""
    spy_close = spy_feat["close"]
    rows = []
    mom = {t: mom_12_1(f["close"]) for t, f in feats.items()}
    for m in months:
        mkt = spy_feat["above"].get(m)
        mkt_ok = None if mkt is None or pd.isna(mkt) else bool(mkt)
        s0 = spy_close.get(m)
        cands = []
        for t, f in feats.items():
            if m not in f.index:
                continue
            c0, ab = f.at[m, "close"], f.at[m, "above"]
            if not (np.isfinite(c0) and c0 >= min_price) or pd.isna(ab):
                continue
            cands.append((t, c0, bool(ab), mom[t].get(m, np.nan)))
        if len(cands) < 30:
            continue
        mser = pd.Series({t: mo for t, _, _, mo in cands}).astype(float)
        pct = mser.rank(pct=True)
        end = m.to_timestamp(how="end")
        for t, c0, ab, mo in cands:
            f = feats[t]
            first = f.attrs.get("first")
            young = bool(first is not None and first >= first_cut and (end - first).days < 3 * 365)
            sc = share_ch(t, m)
            col = stock_colour(ab, mkt_ok, float(pct.get(t, np.nan)), sc, young)
            r = {}
            for h in (1, 3, 12):
                m2 = m + h
                c1, sp1 = f["close"].get(m2), spy_close.get(m2)
                r[h] = (c1 / c0 - 1 - (sp1 / s0 - 1)) if (c1 is not None and sp1 is not None and s0 and np.isfinite(c1)) else np.nan
                r[f"abs{h}"] = (c1 / c0 - 1) if (c1 is not None and np.isfinite(c1)) else np.nan
            rows.append((m, t, col, sc, young, r[1], r[3], r[12], r["abs1"], r["abs12"]))
    return pd.DataFrame(rows, columns=["month", "ticker", "colour", "share_ch", "young", "ex1", "ex3", "ex12", "abs1", "abs12"])


def portfolio(d: pd.DataFrame, colour: str | None, cost_side: float) -> pd.Series:
    """Equal-weight monthly portfolio of one colour (None = all), next-month absolute return net of
    cost_side × turnover (both sides)."""
    out, prev = {}, set()
    for m, g in d.groupby("month"):
        g = g[g["abs1"].notna()]
        if colour is not None:
            g = g[g["colour"] == colour]
        if len(g) == 0:
            out[m] = 0.0; prev = set(); continue
        cur = set(g["ticker"])
        turnover = 1.0 if not prev else len(cur ^ prev) / max(len(cur | prev), 1)
        out[m] = float(g["abs1"].mean()) - 2 * cost_side * turnover
        prev = cur
    return pd.Series(out).sort_index()


def perf(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 12:
        return {"cagr": np.nan, "maxdd": np.nan}
    eq = (1 + r).cumprod()
    return {"cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1), "maxdd": float((eq / eq.cummax() - 1).min())}


def tstat(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std(ddof=1) * math.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def run_experiment92_report(d: pd.DataFrame, spy_ret: pd.Series, diag: list | None = None) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #92 — backtest of the Yuh scanner colour (US stocks) ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    if d.empty:
        L.append("No data.")
        return "\n".join(L)
    L.append(f"{d['month'].nunique()} months {d['month'].min()}–{d['month'].max()}, {d['ticker'].nunique():,} stocks, "
             f"{len(d):,} stock-months. Colour share: " + ", ".join(f"{c} {100*(d['colour'] == c).mean():.0f} %" for c in (GREEN, YELLOW, RED)) + ".")
    L.append("")
    L.append("## 1 What happened after each colour (vs SPY; disaster = 12 M ≤ −40 % absolute, or 3 M ≤ −20 % vs SPY)")
    L.append("| colour | stock-months | 1 M mean | 3 M mean | 12 M mean / median | 12 M beat SPY | disaster 12 M | disaster 3 M |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|")
    for c in (GREEN, YELLOW, RED):
        g = d[d["colour"] == c]
        e12 = g["ex12"].dropna()
        L.append(f"| {c} | {len(g):,} | {100*g['ex1'].mean():+.2f} % | {100*g['ex3'].mean():+.2f} % | "
                 f"{100*e12.mean():+.1f} % / {100*e12.median():+.1f} % | {100*(e12 > 0).mean():.0f} % | "
                 f"{100*(g['abs12'].dropna() <= -0.40).mean():.1f} % | {100*(g['ex3'].dropna() <= -0.20).mean():.1f} % |")
    # spread
    m1 = d.groupby(["month", "colour"])["ex1"].mean().unstack()
    L.append("")
    if GREEN in m1 and RED in m1:
        sp = (m1[GREEN] - m1[RED]).dropna()
        a = sp[sp.index <= pd.Period("2017-12", "M")]
        b = sp[sp.index > pd.Period("2017-12", "M")]
        L.append(f"- 🟢 − 🔴 next month: {100*sp.mean():+.2f} %/month (t {tstat(sp):+.2f}, {len(sp)} months); "
                 f"≤ 2017 {100*a.mean():+.2f} % (t {tstat(a):+.2f}); 2018 → {100*b.mean():+.2f} % (t {tstat(b):+.2f})")
    if GREEN in m1:
        gs = m1[GREEN].dropna()
        L.append(f"- 🟢 vs SPY next month: {100*gs.mean():+.2f} %/month (t {tstat(gs):+.2f})")
    L.append("")
    # portfolios
    L.append("## 2 Monthly portfolios (equal weight, rebalanced monthly)")
    L.append("| portfolio | CAGR gross | CAGR net 0.10 %/side | CAGR net 0.50 %/side (≈ Yuh) | max drawdown (gross) |")
    L.append("|---|--:|--:|--:|--:|")
    for name, c in (("🟢 only", GREEN), ("🔴 only", RED), ("whole universe", None)):
        g0, g1, g5 = portfolio(d, c, 0.0), portfolio(d, c, 0.001), portfolio(d, c, 0.005)
        p0 = perf(g0)
        L.append(f"| {name} | {100*p0['cagr']:+.1f} % | {100*perf(g1)['cagr']:+.1f} % | {100*perf(g5)['cagr']:+.1f} % | {100*p0['maxdd']:.0f} % |")
    sp_ = spy_ret.reindex(sorted(d["month"].unique())).shift(-1).dropna() if spy_ret is not None else None
    if sp_ is not None and len(sp_):
        ps = perf(sp_)
        L.append(f"| SPY (buy & hold) | {100*ps['cagr']:+.1f} % | — | — | {100*ps['maxdd']:.0f} % |")
    L.append("")
    L.append("Reading: 'trifft' is not the goal — the question is whether 🟢 stocks did better and 🔴 stocks crashed "
             "more often, over many cases, after costs.")
    L.append("Caveats: survivorship (only stocks still listed have Yahoo prices); US large caps only; market rule "
             "= SPY above its 200-day average; Yuh costs (0.5 %/side + 0.95 % FX for USD) make monthly trading expensive.")
    return "\n".join(L)
