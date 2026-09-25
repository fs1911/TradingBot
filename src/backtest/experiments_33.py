"""
Experiment #33 — the trend filter, judged fairly: real cash yield, dividends,
parameter robustness, and a savings-plan version.

#32 found the 200d-SMA filter cuts max drawdown in 9/9 markets over decades but
lowers CAGR — with cash at 0% and price indices (no dividends). Both assumptions bias
against it. This experiment removes them:

  1. CASH YIELD: out-of-market days earn the 13-week US T-bill yield (^IRX, since the
     1960s). For non-USD markets this US rate is a proxy (overstates CHF/JPY cash).
  2. DIVIDENDS: S&P 500 total-return index (^SP500TR); the DAX is a total-return
     (performance) index by construction.
  3. ROBUSTNESS: SMA 150 / 200 / 250 and a monthly-checked SMA200 (fewer whipsaws).
     A real effect must not depend on exactly "200, checked daily".
  4. SAVINGS PLAN (the practical question): monthly contribution of 1, three ways —
       plain DCA        : always buy the index;
       trend-DCA light  : buy only in an uptrend, otherwise park the contribution in
                          cash and invest the parked cash when the trend turns up;
       trend-DCA full   : at each month-end hold everything in the index in an uptrend
                          and everything in cash in a downtrend.
     Compared on final wealth multiple and maximum drawdown of the portfolio.

Full rigor runs on the (filter − buy&hold) daily differential. Pure/causal, injected
for CI; the bot fetches via the #32 long-history fetcher (hard timeout).
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

from .rigor import full_rigor
from .experiments_32 import perf


def cash_daily_returns(irx: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """^IRX (annualised %, e.g. 4.5) → daily cash return aligned to `index`.
    Missing yields forward-filled; before the first quote, 0."""
    if irx is None or len(irx) == 0:
        return pd.Series(0.0, index=index)
    y = pd.Series(irx).astype(float).clip(lower=0.0)
    y = y.reindex(y.index.union(index)).sort_index().ffill().reindex(index).fillna(0.0)
    return y / 100.0 / 252.0


def trend_position(px: pd.Series, window: int = 200, monthly: bool = False) -> pd.Series:
    """1 when yesterday's close was above its SMA(window), else 0. If `monthly`, the
    signal is only re-evaluated at month-ends and held in between."""
    above = (px > px.rolling(window).mean()).astype(float)
    above[px.rolling(window).mean().isna()] = np.nan
    if monthly:
        naive = px.index.tz_localize(None) if px.index.tz is not None else px.index
        is_me = pd.Series(naive.to_period("M"), index=px.index)
        is_me = is_me != is_me.shift(-1)
        above = above.where(is_me).ffill()
    return above.shift(1).fillna(0.0)


def filter_returns_with_cash(px: pd.Series, cash: pd.Series, window: int = 200,
                             monthly: bool = False, cost_bps: float = 5.0) -> pd.Series:
    ret = px.pct_change().fillna(0.0)
    pos = trend_position(px, window, monthly)
    return ret * pos + cash * (1.0 - pos) - pos.diff().abs().fillna(0.0) * cost_bps / 1e4


def savings_plans(px: pd.Series, cash: pd.Series, window: int = 200) -> dict:
    """Month-end simulation of plain DCA vs trend-DCA light vs trend-DCA full.
    Returns {plan: (final_multiple, max_drawdown)}."""
    px = px.dropna()
    sma = px.rolling(window).mean()
    naive = px.index.tz_localize(None) if px.index.tz is not None else px.index
    months = pd.Series(naive.to_period("M"), index=px.index)
    month_ends = px.index[(months != months.shift(-1)).to_numpy()]
    month_ends = [t for t in month_ends if not np.isnan(sma.loc[t])]
    if len(month_ends) < 24:
        return {}
    cash_growth = (1.0 + cash.reindex(px.index).fillna(0.0)).cumprod()

    state = {k: {"u": 0.0, "c": 0.0, "vals": []} for k in ("plain", "light", "full")}
    prev = None
    n = 0
    for t in month_ends:
        p = float(px.loc[t])
        g = float(cash_growth.loc[t] / cash_growth.loc[prev]) if prev is not None else 1.0
        up = p > float(sma.loc[t])
        n += 1
        for k, s in state.items():
            s["c"] *= g                       # parked cash earns T-bill yield
            if k == "plain":
                s["u"] += 1.0 / p
            elif k == "light":
                if up:
                    s["u"] += (1.0 + s["c"]) / p
                    s["c"] = 0.0
                else:
                    s["c"] += 1.0
            else:  # full
                total = s["u"] * p + s["c"] + 1.0
                if up:
                    s["u"], s["c"] = total / p, 0.0
                else:
                    s["u"], s["c"] = 0.0, total
            s["vals"].append((s["u"] * p + s["c"], n))
        prev = t
    out = {}
    for k, s in state.items():
        v = np.array([x for x, _ in s["vals"]])
        contrib = np.array([m for _, m in s["vals"]], dtype=float)
        # drawdown of value relative to contributions (neutralises new money inflows)
        ratio = v / contrib
        dd = float((ratio / np.maximum.accumulate(ratio) - 1.0).min())
        out[k] = (float(v[-1] / contrib[-1]), dd)
    return out


def run_experiment33_report(fetch: Callable[[dict], tuple], assets: list,
                            irx: pd.Series, n_trials: int = 110) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #33 — trend filter judged fairly (cash yield, dividends, "
             f"robustness, savings plans) ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    have_irx = irx is not None and len(irx) > 1000
    lines.append(f"Cash earns the 13-week US T-bill yield (^IRX"
                 f"{', from ' + format(irx.index[0], '%Y') if have_irx else ' UNAVAILABLE → 0%'}). "
                 f"For non-USD markets this is a proxy and flatters cash. Cells: CAGR / Sharpe / "
                 f"max drawdown. Rigor on (SMA200-with-cash − B&H).")
    lines.append("")

    lines.append("## Timing rules vs buy & hold")
    lines.append("| Asset | years | B&H | SMA200 daily | SMA200 monthly | SMA150 | SMA250 | "
                 "rigor SMA200−B&H |")
    lines.append("|---|--:|---|---|---|---|---|---|")
    g = lambda p: f"{100*p['cagr']:+.1f}% / {p['sharpe']:.2f} / {100*p['maxdd']:.0f}%"
    sum_ = {"cagr_win": 0, "sharpe_win": 0, "dd_win": 0, "robust": 0, "pass": 0, "n": 0}
    plans_rows = []
    for a in assets:
        try:
            px, src = fetch(a)
        except Exception:
            px, src = pd.Series(dtype=float), "error"
        if px is None or len(px) < 1500:
            lines.append(f"| {a['name']} | — | no data ({src}) | | | | | |")
            continue
        px = pd.Series(px).astype(float).dropna().sort_index()
        px.index = pd.to_datetime(px.index)
        px.index = px.index.tz_localize(None) if px.index.tz is not None else px.index
        cash = cash_daily_returns(irx, px.index)
        warm = 260
        bh_r = px.pct_change().fillna(0.0).iloc[warm:]
        variants = {
            "d200": filter_returns_with_cash(px, cash, 200).iloc[warm:],
            "m200": filter_returns_with_cash(px, cash, 200, monthly=True).iloc[warm:],
            "d150": filter_returns_with_cash(px, cash, 150).iloc[warm:],
            "d250": filter_returns_with_cash(px, cash, 250).iloc[warm:],
        }
        pb = perf(bh_r)
        pv = {k: perf(v) for k, v in variants.items()}
        rig = full_rigor(f"{a['name']} SMA200+cash − B&H", variants["d200"] - bh_r, n_trials)
        v = rig.get("verdict", "—")
        vshort = "✅" if v.startswith("✅") else "⚠️" if v.startswith("⚠") else "❌"
        sum_["n"] += 1
        sum_["cagr_win"] += int(pv["d200"]["cagr"] > pb["cagr"])
        sum_["sharpe_win"] += int(pv["d200"]["sharpe"] > pb["sharpe"])
        sum_["dd_win"] += int(pv["d200"]["maxdd"] > pb["maxdd"])
        sum_["robust"] += int(all(pv[k]["sharpe"] > pb["sharpe"] for k in pv))
        sum_["pass"] += int(v.startswith("✅"))
        lines.append(f"| {a['name']} | {len(px)/252:.0f} | {g(pb)} | {g(pv['d200'])} | "
                     f"{g(pv['m200'])} | {g(pv['d150'])} | {g(pv['d250'])} | {vshort} |")
        sp = savings_plans(px, cash)
        if sp:
            plans_rows.append((a["name"], sp))
    lines.append("")

    lines.append("## Savings plans (monthly contribution 1) — final multiple / max drawdown")
    lines.append("| Asset | plain DCA | trend-DCA light | trend-DCA full |")
    lines.append("|---|---|---|---|")
    light_win = full_win = full_dd = 0
    for name, sp in plans_rows:
        f = lambda x: f"{x[0]:.2f}× / {100*x[1]:.0f}%"
        light_win += int(sp["light"][0] > sp["plain"][0])
        full_win += int(sp["full"][0] > sp["plain"][0])
        full_dd += int(sp["full"][1] > sp["plain"][1])
        lines.append(f"| {name} | {f(sp['plain'])} | {f(sp['light'])} | {f(sp['full'])} |")
    lines.append("")

    n = sum_["n"]
    m = len(plans_rows)
    lines.append("---")
    lines.append(
        f"**Summary timing (with cash yield):** SMA200 beat B&H on CAGR in {sum_['cagr_win']}/{n}, "
        f"on Sharpe in {sum_['sharpe_win']}/{n}, on max drawdown in {sum_['dd_win']}/{n}; "
        f"all four variants beat B&H Sharpe in {sum_['robust']}/{n}; full rigor pass "
        f"{sum_['pass']}/{n}.")
    lines.append(
        f"**Summary savings plans:** trend-DCA light beat plain DCA in {light_win}/{m}; "
        f"trend-DCA full beat plain DCA in {full_win}/{m} and had a smaller max drawdown in "
        f"{full_dd}/{m}.")
    return "\n".join(lines)
