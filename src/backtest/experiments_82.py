"""
Experiment #82 — fat tails: how often do extreme days really happen, and what does the
popular claim 'if you miss the 10 best days you lose half your return' really mean?

S&P 500 daily since 1928 (Yahoo), plus Bitcoin since 2014.
  A Frequency of moves beyond 3 / 4 / 5 / 7 / 10 standard deviations vs the normal
    distribution (using the whole-sample σ and, fairer, a trailing 1-year σ).
  B Largest days: dates, and how many of the 10 best days fell within ±10 trading days of
    one of the 10 worst days (clustering in crises).
  C 'Missing the best days': CAGR when skipping the N best days, the N worst days, or BOTH;
    and a realistic market-timer who is out of the market on random days (same count).
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


def _phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def tail_counts(r: pd.Series, ks=(3, 4, 5, 7, 10)) -> list:
    r = r.dropna()
    sd_all = r.std()
    sd_roll = r.rolling(252).std().shift(1)
    out = []
    for k in ks:
        n_all = int((r.abs() > k * sd_all).sum())
        z = (r / sd_roll).dropna()
        n_roll = int((z.abs() > k).sum())
        p2 = math.erfc(k / math.sqrt(2))          # two-sided normal tail, exact even at 10 σ
        out.append({"k": k, "obs_all": n_all, "obs_roll": n_roll, "normal": len(r) * p2,
                    "every_years_normal": (1 / p2) / 252 if p2 > 0 else float("inf")})
    return out


def cagr(r: pd.Series) -> float:
    eq = float((1 + r).prod())
    return eq ** (252 / len(r)) - 1


def skip_days(r: pd.Series, n: int, which: str) -> float:
    r = r.dropna()
    if which == "best":
        drop = r.nlargest(n).index
    elif which == "worst":
        drop = r.nsmallest(n).index
    else:
        drop = r.nlargest(n).index.union(r.nsmallest(n).index)
    return cagr(r.drop(drop))


def random_out(r: pd.Series, n: int, sims: int = 2000, seed: int = 82) -> tuple:
    rng = np.random.default_rng(seed)
    v = r.dropna().to_numpy()
    res = []
    for _ in range(sims):
        keep = np.ones(len(v), bool)
        keep[rng.choice(len(v), n, replace=False)] = False
        res.append(np.prod(1 + v[keep]) ** (252 / keep.sum()) - 1)
    res = np.array(res)
    return float(np.median(res)), float(np.percentile(res, 5)), float(np.percentile(res, 95))


def clustering(r: pd.Series, n: int = 10, window: int = 10) -> int:
    best, worst = r.nlargest(n).index, r.nsmallest(n).index
    pos = {d: i for i, d in enumerate(r.index)}
    wpos = [pos[d] for d in worst]
    return int(sum(any(abs(pos[b] - w) <= window for w in wpos) for b in best))


def run_experiment82_report(series: dict) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #82 — fat tails and the 'best days' claim ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    for name, px in series.items():
        if px is None or len(px) < 2000:
            L.append(f"## {name}: no data")
            continue
        s = pd.Series(px).dropna().astype(float)
        idx = pd.to_datetime(s.index)
        s.index = idx.tz_localize(None) if idx.tz is not None else idx
        r = s.pct_change().dropna()
        L.append(f"## {name} — {r.index[0]:%Y-%m-%d} → {r.index[-1]:%Y-%m-%d}, {len(r):,} days, price only")
        L.append("")
        L.append("### A How often do extreme days happen?")
        L.append("| move beyond | observed (whole-sample σ) | observed (trailing 1-y σ) | expected if normal | normal says: once every … years |")
        L.append("|---|--:|--:|--:|--:|")
        for t in tail_counts(r):
            ev = t["every_years_normal"]
            evs = f"{ev:,.0f}" if ev < 1e7 else "> 10 million"
            L.append(f"| {t['k']} σ | {t['obs_all']} | {t['obs_roll']} | {t['normal']:.2f} | {evs} |")
        L.append("")
        L.append("### B Biggest days")
        L.append("Best: " + ", ".join(f"{d:%Y-%m-%d} {100*v:+.1f} %" for d, v in r.nlargest(5).items()))
        L.append("Worst: " + ", ".join(f"{d:%Y-%m-%d} {100*v:+.1f} %" for d, v in r.nsmallest(5).items()))
        L.append(f"Of the 10 best days, **{clustering(r)}** were within ±10 trading days of one of the 10 worst days.")
        L.append("")
        L.append("### C 'Missing the best days'")
        L.append("| days removed | skip N best | skip N worst | skip both | out on N RANDOM days (median, 5–95 %) |")
        L.append("|---|--:|--:|--:|--:|")
        L.append(f"| none | {100*cagr(r):+.2f} % | — | — | — |")
        for n in (5, 10, 20, 50):
            med, lo, hi = random_out(r, n, sims=500)
            L.append(f"| {n} | {100*skip_days(r, n, 'best'):+.2f} % | {100*skip_days(r, n, 'worst'):+.2f} % | "
                     f"{100*skip_days(r, n, 'both'):+.2f} % | {100*med:+.2f} % ({100*lo:+.2f} … {100*hi:+.2f}) |")
        L.append("")
    L.append("Reading: extreme days are far more frequent than a normal distribution predicts — risk models, stop "
             "losses and leverage built on 'normal' volatility underestimate crashes. The best and worst days cluster "
             "in the same crises, so 'missing the best days' alone is an unrealistic scenario; a timer who is out on "
             "random days loses very little, a timer who is out in crises misses both.")
    return "\n".join(L)
