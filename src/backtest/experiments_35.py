"""
Experiment #35 — is the 130-year trend-filter result real or a data artefact?

#34 found the 10-month trend filter (stocks ↔ 10y bonds) beat 100% stocks over
1891–2023: 8.8% vs 6.65% real a year, max drawdown −44% vs −77%. But Shiller prices
are MONTHLY AVERAGES of daily closes. Averaging induces artificial positive
autocorrelation in monthly returns (the "Working effect"), which flatters exactly the
kind of trend rule tested. This experiment repeats the test with everything identical
except the price series:

  A. Shiller monthly-average prices (as in #34);
  B. true month-END closes built from daily S&P 500 data (Yahoo ^GSPC, since 1927).

Same dividends (Shiller dividend yield), same 10y-bond proxy, same CPI, same period.
It also measures the artefact directly (lag-1 autocorrelation of monthly returns under
A vs B), adds a 0%-cash variant as the out-of-market asset, and splits the month-end
result into eras (1928–49, 1950–89, 1990–) to see whether the edge is only 1929.
Pure/causal, injected for CI; the bot downloads both series with hard timeouts.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .rigor import block_bootstrap_pvalue, deflated_ok
from .experiments_34 import mstats, trend_position


def fetch_yahoo_daily(symbol: str = "^GSPC", start: str = "1927-12-01", timeout: int = 20):
    """Daily closes from Yahoo's chart API including pre-1970 history (negative epoch)."""
    import urllib.request
    import urllib.parse
    import time as _t
    from .experiments_32 import parse_yahoo_json
    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
           f"?period1={p1}&period2={int(_t.time())}&interval=1d&events=history")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return parse_yahoo_json(r.read().decode("utf-8", "replace"))
    except Exception:
        return pd.Series(dtype=float)


def month_end_closes(daily: pd.Series) -> pd.Series:
    """Last available daily close of each calendar month, indexed by monthly Period."""
    s = pd.Series(daily).astype(float).dropna().sort_index()
    idx = pd.to_datetime(s.index)
    idx = idx.tz_localize(None) if idx.tz is not None else idx
    s.index = idx.to_period("M")
    return s.groupby(level=0).last()


def build_panel(shiller: pd.DataFrame, daily: pd.Series) -> pd.DataFrame:
    """Monthly panel on a Period index: p_avg, p_me, div, cpi, gs10."""
    sh = shiller.copy()
    sh.index = pd.to_datetime(sh.index).to_period("M")
    sh = sh[~sh.index.duplicated(keep="last")]
    me = month_end_closes(daily).rename("p_me")
    panel = pd.concat([sh[["price", "div", "cpi", "gs10"]].rename(columns={"price": "p_avg"}),
                       me], axis=1)
    return panel.dropna(subset=["p_avg", "p_me", "cpi", "gs10"])


def real_returns(panel: pd.DataFrame, duration: float = 7.0) -> pd.DataFrame:
    """Real monthly returns: stocks from averages (A) and month-ends (B), bonds, cash 0%."""
    infl = panel["cpi"] / panel["cpi"].shift(1)
    div_m = panel["div"].fillna(0.0) / 12.0
    avg_nom = (panel["p_avg"] + div_m) / panel["p_avg"].shift(1) - 1.0
    me_nom = panel["p_me"] / panel["p_me"].shift(1) - 1.0 + div_m / panel["p_avg"]
    y = panel["gs10"] / 100.0
    bond_nom = y.shift(1) / 12.0 - duration * (y - y.shift(1))
    real = lambda nom: (1.0 + nom) / infl - 1.0
    return pd.DataFrame({"stock_avg": real(avg_nom), "stock_me": real(me_nom),
                         "bond": real(bond_nom), "cash0": real(pd.Series(0.0, index=panel.index))})


def lag1_autocorr(r: pd.Series) -> float:
    r = r.dropna()
    return float(r.autocorr(1)) if len(r) > 24 else float("nan")


def _row(name, r, base, n_trials):
    st = mstats(r)
    if base is None:
        return (f"| {name} | {100*st['cagr']:+.2f}% | {st['sharpe']:.2f} | "
                f"{100*st['maxdd']:.0f}% | — | — | — |"), None
    d = (r - base).dropna()
    p = block_bootstrap_pvalue(d, block=12)
    sig = deflated_ok(p, n_trials)
    mid = d.index[len(d) // 2]
    halves = bool(d.loc[:mid].mean() > 0 and d.loc[mid:].mean() > 0)
    return (f"| {name} | {100*st['cagr']:+.2f}% | {st['sharpe']:.2f} | {100*st['maxdd']:.0f}% | "
            f"{p:.3f} | {'✅' if sig else '❌'} | {'✅' if halves else '❌'} |"), (st, p, sig, halves)


def run_experiment35_report(shiller: pd.DataFrame, daily: pd.Series, n_trials: int = 125) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #35 — trend filter: real edge or averaging artefact? "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if shiller is None or len(shiller) < 240 or daily is None or len(daily) < 5000:
        lines.append(f"**Missing data** — Shiller months: {0 if shiller is None else len(shiller)}, "
                     f"daily S&P closes: {0 if daily is None else len(daily)}. Nothing to test.")
        return "\n".join(lines)

    panel = build_panel(shiller, daily)
    rr = real_returns(panel)
    pos_avg = trend_position(rr["stock_avg"])
    pos_me = trend_position(rr["stock_me"])
    start = pd.concat([pos_avg, pos_me, rr], axis=1).dropna().index.min()
    rr = rr.loc[start:]
    pos_avg, pos_me = pos_avg.loc[start:], pos_me.loc[start:]

    lines.append(f"Months: {len(rr)} ({rr.index[0]} → {rr.index[-1]}). Daily closes from "
                 f"{pd.to_datetime(daily.index[0]):%Y-%m-%d}. Real returns, Shiller dividends, "
                 f"10y-bond proxy; 10-month SMA signal, lagged one month.")
    lines.append("")

    ac_avg, ac_me = lag1_autocorr(rr["stock_avg"]), lag1_autocorr(rr["stock_me"])
    lines.append("## The artefact, measured")
    lines.append("| Price series | lag-1 autocorrelation of monthly returns |")
    lines.append("|---|--:|")
    lines.append(f"| A: monthly averages (Shiller) | {ac_avg:+.3f} |")
    lines.append(f"| B: true month-end closes | {ac_me:+.3f} |")
    lines.append("")

    trend_avg = pos_avg * rr["stock_avg"] + (1 - pos_avg) * rr["bond"]
    trend_me = pos_me * rr["stock_me"] + (1 - pos_me) * rr["bond"]
    trend_me_cash = pos_me * rr["stock_me"] + (1 - pos_me) * rr["cash0"]

    lines.append("## Head to head (real)")
    lines.append("| Series / rule | real CAGR | Sharpe | max DD | p vs own B&H | sig after haircut | "
                 "both halves |")
    lines.append("|---|--:|--:|--:|--:|:--:|:--:|")
    out = {}
    for name, r, base in (
        ("A · 100% stocks (averages)", rr["stock_avg"], None),
        ("A · trend filter (averages)", trend_avg, rr["stock_avg"]),
        ("B · 100% stocks (month-end)", rr["stock_me"], None),
        ("B · trend filter (month-end, bonds)", trend_me, rr["stock_me"]),
        ("B · trend filter (month-end, 0% cash)", trend_me_cash, rr["stock_me"]),
    ):
        row, res = _row(name, r, base, n_trials)
        lines.append(row)
        out[name] = (mstats(r), res)
    lines.append("")

    lines.append("## Month-end version by era (trend − 100% stocks)")
    lines.append("| Era | months | excess %/y | stocks max DD | trend max DD |")
    lines.append("|---|--:|--:|--:|--:|")
    eras = (("1928–1949", "1928-01", "1949-12"), ("1950–1989", "1950-01", "1989-12"),
            ("1990–end", "1990-01", str(rr.index[-1])))
    era_pos = 0
    for name, a, b in eras:
        sl = slice(pd.Period(a, "M"), pd.Period(b, "M"))
        s_, t_ = rr["stock_me"].loc[sl], trend_me.loc[sl]
        if len(s_) < 24:
            continue
        ex = 100 * 12 * (t_ - s_).mean()
        era_pos += int(ex > 0)
        lines.append(f"| {name} | {len(s_)} | {ex:+.2f} | {100*mstats(s_)['maxdd']:.0f}% | "
                     f"{100*mstats(t_)['maxdd']:.0f}% |")
    lines.append("")

    ga = out["A · trend filter (averages)"][0]["cagr"] - out["A · 100% stocks (averages)"][0]["cagr"]
    gb = out["B · trend filter (month-end, bonds)"][0]["cagr"] - out["B · 100% stocks (month-end)"][0]["cagr"]
    kept = (gb / ga) if ga and ga == ga and ga != 0 else float("nan")
    rb = out["B · trend filter (month-end, bonds)"][1]
    lines.append("---")
    lines.append(
        f"**Summary:** autocorrelation {ac_avg:+.2f} (averages) vs {ac_me:+.2f} (month-end). "
        f"Trend-filter CAGR advantage {100*ga:+.2f} pp with averages vs {100*gb:+.2f} pp with "
        f"true month-end closes — {100*kept:.0f}% of the #34 edge survives. Month-end version: "
        f"p={rb[1]:.3f}, significant after haircut: {'yes' if rb[2] else 'no'}, positive in both "
        f"halves: {'yes' if rb[3] else 'no'}, positive in {era_pos}/3 eras.")
    return "\n".join(lines)
