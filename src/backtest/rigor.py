"""
Rigor battery — stronger, more meaningful statistical tests than the basic
OOS/walk-forward/cost checks. Answers "real edge or luck?" with actual numbers.

Includes:
  - annualized Sharpe and the t-statistic of daily returns
  - a block-bootstrap p-value (does the mean return beat zero, accounting for
    autocorrelation?) — the direct "is it luck?" test
  - a multiple-testing (Bonferroni) haircut: with N hypotheses tried, the bar for
    significance is alpha/N, not alpha — this quantifies the data-snooping risk
  - sub-period (regime) stability: does it work in all thirds of history?
  - a full_rigor() that combines everything into one honest verdict.

Pure numpy/pandas. All causal — operates on a strategy's realised daily returns.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .trend_follow import _curve_stats
from .oos_runner import split_is_oos


def annualized_sharpe(returns: pd.Series) -> float:
    r = returns.dropna()
    if len(r) < 20 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(252))


def t_stat(returns: pd.Series) -> float:
    """t-statistic of the mean daily return (|t|>~2 ≈ 95% significant, before
    multiple-testing correction)."""
    r = returns.dropna()
    if len(r) < 20 or r.std() == 0:
        return 0.0
    return float(r.mean() / (r.std() / np.sqrt(len(r))))


def block_bootstrap_pvalue(returns: pd.Series, n: int = 2000, block: int = 10,
                           seed: int = 0) -> float:
    """One-sided p-value for H0: mean return <= 0, via a moving-block bootstrap
    (preserves short-term autocorrelation). p = fraction of resamples whose mean
    is <= 0. Low p → the positive mean is unlikely to be luck."""
    r = returns.dropna().to_numpy()
    if len(r) < block * 3:
        return 1.0
    rng = np.random.default_rng(seed)
    nblocks = int(np.ceil(len(r) / block))
    means = np.empty(n)
    max_start = len(r) - block
    for i in range(n):
        starts = rng.integers(0, max_start + 1, nblocks)
        sample = np.concatenate([r[s:s + block] for s in starts])[:len(r)]
        means[i] = sample.mean()
    return float(np.mean(means <= 0))


def deflated_ok(pvalue: float, n_trials: int, alpha: float = 0.05) -> bool:
    """Bonferroni haircut: with n_trials hypotheses tried, require p < alpha/n_trials."""
    return pvalue < alpha / max(1, n_trials)


def subperiod_stability(returns: pd.Series, k: int = 3):
    """Split history into k equal parts; return (per-part stats, #positive parts)."""
    r = returns.dropna()
    out = []
    L = len(r) // k
    for i in range(k):
        seg = r.iloc[i * L:] if i == k - 1 else r.iloc[i * L:(i + 1) * L]
        out.append(_curve_stats(seg))
    positive = sum(1 for s in out if s["ret"] > 0)
    return out, positive


def full_rigor(name: str, returns: pd.Series, n_trials: int = 15,
               window: int = 252, step: int = 63) -> dict:
    """Run the full battery on a strategy's daily returns and produce one honest
    verdict that requires: positive OOS, decent walk-forward, statistical
    significance AFTER a multiple-testing haircut, and stability across regimes."""
    r = returns.dropna()
    if len(r) < max(window + step, 300):
        return {"name": name, "verdict": "insufficient data"}

    is_r, oos_r = split_is_oos(r.to_frame("r"))
    oos = _curve_stats(oos_r["r"])

    # walk-forward
    hits = total = 0
    i = 0
    while i + window <= len(r):
        st = _curve_stats(r.iloc[i:i + window])
        total += 1
        if st["ret"] > 0 and st["mar"] > 0.5:
            hits += 1
        i += step
    wf_pct = round(100 * hits / total) if total else 0

    sharpe = annualized_sharpe(r)
    tstat = t_stat(r)
    pval = block_bootstrap_pvalue(r)
    sig = deflated_ok(pval, n_trials)
    parts, pos_parts = subperiod_stability(r)

    # Verdict: ALL must hold — OOS positive, walk-forward majority, statistically
    # significant after multiple-testing haircut, and positive in every regime third.
    if (oos["ret"] > 0 and wf_pct >= 60 and sig and pos_parts == len(parts)):
        verdict = "✅ survives full rigor"
    elif oos["ret"] > 0 and wf_pct >= 50 and pval < 0.05:
        verdict = "⚠️ significant but not multiple-testing-proof / regime-fragile"
    else:
        verdict = "❌ no robust edge"

    return {
        "name": name, "oos_ret": oos["ret"], "oos_mar": oos["mar"],
        "sharpe": round(sharpe, 2), "t_stat": round(tstat, 2),
        "p_value": round(pval, 4), "sig_after_haircut": sig,
        "wf_pct": wf_pct, "regime_positive": f"{pos_parts}/{len(parts)}",
        "verdict": verdict,
    }


def rigor_row(res: dict) -> str:
    """Format a full_rigor result as one Markdown table row."""
    if res.get("verdict") == "insufficient data":
        return f"| {res['name']} | insufficient data |||||||"
    return (f"| {res['name']} | {res['oos_ret']:+.0f} | {res['sharpe']} | {res['t_stat']} | "
            f"{res['p_value']} | {'yes' if res['sig_after_haircut'] else 'no'} | "
            f"{res['wf_pct']}% | {res['regime_positive']} | {res['verdict']} |")


RIGOR_HEADER = ("| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | "
                "Walk-fwd | regimes+ | Verdict |\n|---|--:|--:|--:|--:|:--:|:--:|:--:|---|")
