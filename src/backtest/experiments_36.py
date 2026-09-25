"""
Experiment #36 — calendar anomalies over ~95 years, before vs after publication.

Earlier calendar tests (#11/#12) had a few years of data. With daily S&P 500 closes
since 1927 we can test the famous calendar anomalies over almost a century — and ask
the question that matters for any "discovered" pattern: does it survive once it is
published? (McLean & Pontiff 2016 find anomalies lose much of their return after
publication.) Anomalies and the year they entered the literature:

  turn-of-month  last + first 3 trading days       Ariel 1987
  monday         Friday-close → Monday-close       French 1980
  january        January vs other months            Rozeff & Kinney 1976
  pre-holiday    day before a non-weekend closure   Lakonishok & Smidt 1988
  halloween      Nov–Apr vs May–Oct ("Sell in May") Bouman & Jacobsen 2002

For each: mean daily return inside vs outside the window, Welch t, pre- vs
post-publication and last 20 years, Bonferroni-haircut significance; plus a
strategy that is invested only inside the window (0% cash otherwise, 5 bps per
switch) vs buy & hold. Price index (no dividends). The calendar is known in advance,
so the masks have no look-ahead. Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_32 import perf

ANOMALIES = {
    "turn-of-month (last+first 3 days)": 1987,
    "monday (weekend effect)": 1980,
    "january": 1976,
    "pre-holiday": 1988,
    "halloween (Nov–Apr)": 2002,
}


# ---------------------------------------------------------------- masks

def _naive(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(idx)
    return idx.tz_localize(None) if idx.tz is not None else idx


def tom_mask(idx) -> pd.Series:
    idx = _naive(idx)
    per = idx.to_period("M")
    s = pd.Series(np.arange(len(idx)), index=idx)
    first = s.groupby(per).rank(method="first") - 1          # 0-based position in month
    last = s.groupby(per).rank(method="first", ascending=False) - 1
    return pd.Series(((first <= 2) | (last == 0)).to_numpy(), index=idx)


def monday_mask(idx) -> pd.Series:
    idx = _naive(idx)
    return pd.Series(idx.weekday == 0, index=idx)


def january_mask(idx) -> pd.Series:
    idx = _naive(idx)
    return pd.Series(idx.month == 1, index=idx)


def halloween_mask(idx) -> pd.Series:
    idx = _naive(idx)
    return pd.Series(np.isin(idx.month, [11, 12, 1, 2, 3, 4]), index=idx)


def preholiday_mask(idx) -> pd.Series:
    """Trading day whose next trading day is not simply the next weekday/Monday."""
    idx = _naive(idx)
    nxt = pd.Series(idx, index=idx).shift(-1)
    gap = (nxt - pd.Series(idx, index=idx)).dt.days
    wd = pd.Series(idx.weekday, index=idx)
    normal = (gap == 1) | ((wd == 4) & (gap == 3))
    return (~normal & gap.notna()).rename(None)


MASKS = {
    "turn-of-month (last+first 3 days)": tom_mask,
    "monday (weekend effect)": monday_mask,
    "january": january_mask,
    "pre-holiday": preholiday_mask,
    "halloween (Nov–Apr)": halloween_mask,
}


# ---------------------------------------------------------------- stats

def welch(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 20 or len(b) < 20:
        return float("nan")
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((a.mean() - b.mean()) / se) if se > 0 else float("nan")


def p_two_sided(t: float) -> float:
    return float(math.erfc(abs(t) / math.sqrt(2))) if t == t else float("nan")


def compare(r: pd.Series, mask: pd.Series, start=None, end=None) -> dict:
    sub = r.loc[start:end].dropna()
    m = mask.reindex(sub.index).fillna(False).astype(bool)
    a, b = sub[m].to_numpy(), sub[~m].to_numpy()
    return {"in_bp": 1e4 * a.mean() if len(a) else float("nan"),
            "out_bp": 1e4 * b.mean() if len(b) else float("nan"),
            "t": welch(a, b), "n_in": len(a)}


def window_strategy(r: pd.Series, mask: pd.Series, cost_bps: float = 5.0) -> pd.Series:
    pos = mask.reindex(r.index).fillna(False).astype(float)
    return r * pos - pos.diff().abs().fillna(0.0) * cost_bps / 1e4


# ---------------------------------------------------------------- report

def run_experiment36_report(close: pd.Series, n_trials: int = 135) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #36 — calendar anomalies over ~95 years, before vs after "
             f"publication ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if close is None or len(close) < 5000:
        lines.append(f"**Missing data** — daily closes: {0 if close is None else len(close)}.")
        return "\n".join(lines)
    close = pd.Series(close).astype(float).dropna().sort_index()
    close.index = _naive(close.index)
    r = close.pct_change().dropna()
    end_year = r.index[-1].year
    recent = f"{end_year - 19}-01-01"
    crit = 0.05 / n_trials
    lines.append(f"S&P 500 daily, {r.index[0]:%Y-%m-%d} → {r.index[-1]:%Y-%m-%d} "
                 f"({len(r)} days, price index). Values: mean daily return in the window vs "
                 f"outside (basis points). Haircut: two-sided p < {crit:.5f} (α/{n_trials}).")
    lines.append("")
    lines.append("| Anomaly | published | BEFORE: in / out bp, t | AFTER: in / out bp, t | "
                 f"LAST 20y: in / out bp, t | after pub. sig? |")
    lines.append("|---|--:|---|---|---|:--:|")

    fmt = lambda c: f"{c['in_bp']:+.1f} / {c['out_bp']:+.1f}, {c['t']:+.2f}"
    verdicts = {}
    for name, year in ANOMALIES.items():
        mask = MASKS[name](r.index)
        pre = compare(r, mask, None, f"{year - 1}-12-31")
        post = compare(r, mask, f"{year + 1}-01-01", None)
        rec = compare(r, mask, recent, None)
        post_sig = (post["t"] == post["t"] and p_two_sided(post["t"]) < crit
                    and np.sign(post["t"]) == np.sign(pre["t"]))
        decay = (post["in_bp"] - post["out_bp"]) / (pre["in_bp"] - pre["out_bp"]) \
            if pre["in_bp"] != pre["out_bp"] else float("nan")
        verdicts[name] = (pre, post, rec, post_sig, decay)
        lines.append(f"| {name} | {year} | {fmt(pre)} | {fmt(post)} | {fmt(rec)} | "
                     f"{'✅' if post_sig else '❌'} |")
    lines.append("")

    lines.append("## Strategy: invested only inside the window (5 bps/switch, 0% cash) vs buy & hold")
    lines.append("| Rule | period | time invested | CAGR | Sharpe | max DD |")
    lines.append("|---|---|--:|--:|--:|--:|")
    g = lambda p: f"{100*p['cagr']:+.1f}% | {p['sharpe']:.2f} | {100*p['maxdd']:.0f}%"
    for label, start in (("full", None), (f"since {end_year - 19}", recent)):
        rr = r.loc[start:]
        lines.append(f"| buy & hold | {label} | 100% | {g(perf(rr))} |")
        for name in ANOMALIES:
            mask = MASKS[name](r.index)
            sr = window_strategy(rr, mask)
            inv = float(mask.reindex(rr.index).fillna(False).mean())
            lines.append(f"| {name} | {label} | {100*inv:.0f}% | {g(perf(sr))} |")
    lines.append("")

    surv = [n for n, v in verdicts.items() if v[3]]
    dec = ", ".join(f"{n.split(' ')[0]} {100*v[4]:.0f}%" for n, v in verdicts.items()
                    if v[4] == v[4])
    lines.append("---")
    lines.append(f"**Summary:** significant AFTER publication (same sign, haircut): "
                 f"{len(surv)}/{len(verdicts)} ({', '.join(surv) if surv else 'none'}). "
                 f"Post-publication effect size as % of pre-publication: {dec}.")
    return "\n".join(lines)
