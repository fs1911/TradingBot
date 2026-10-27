"""
Experiment #57 — the big overfitting test: what survives once we admit how much we tried?

Three tools from the backtest-overfitting literature, applied to the whole project:

  A Multiple testing over the REGISTER of every test statistic reported in RESEARCH.md
    (#11–#56). The project ran ≈ 270 trials in total; trials without a reported
    statistic count as p = 1 (conservative). Corrections: Bonferroni, Holm,
    Benjamini–Hochberg false discovery rate (q = 5 %), Harvey–Liu–Zhu (2016) t > 3.0.
    One-sided p-values in the PRE-REGISTERED direction (an edge must have the
    predicted sign).
  B Deflated Sharpe Ratio (Bailey & López de Prado 2014) for the project's best
    strategies: probability that the true Sharpe > 0 after accounting for the number
    of trials, the dispersion of Sharpe ratios across trials, sample length and
    non-normal returns. Sensitivity grid because the dispersion is not known exactly.
  C Probability of Backtest Overfitting (Bailey, Borwein, López de Prado & Zhu 2017)
    via combinatorially symmetric cross-validation (CSCV) on strategy families we can
    recompute from raw data: a trend-rule grid on the S&P 500 (1928→) and the #56
    factor candidates (developed markets 1990→). PBO = how often the in-sample winner
    lands in the bottom half out-of-sample. Pure-noise control should give ≈ 50 %.
Pure, injected for CI.
"""
from __future__ import annotations
import itertools
import math
import numpy as np
import pandas as pd

N_TRIALS_PROJECT = 270

# (experiment, test, kind, value, predicted sign, note)
#   kind 't' → t-statistic, 'p' → one-sided p-value already in the predicted direction.
#   Values copied from RESEARCH.md / experiment*_results.md.
REGISTER = [
    ("11", "XLE seasonality", "p", 0.044, +1, ""),
    ("11", "Copper lead-lag", "t", -2.6, +1, "wrong sign"),
    ("12", "RSI(2) reversal SPY", "p", 0.001, +1, "gross of realistic costs (#13)"),
    ("12", "RSI(2) reversal QQQ", "p", 0.001, +1, "gross of realistic costs (#13)"),
    ("15", "Machine learning (logit) QQQ direction", "p", 0.03, +1, ""),
    ("17", "RSI(2) low-vol regime SPY", "p", 0.001, +1, "contradicted pre-registration"),
    ("20", "Momentum long/short 92 stocks", "p", 0.15, +1, ""),
    ("20", "Short-term reversal after costs", "t", -3.7, +1, "wrong sign"),
    ("21", "Momentum long-only top decile", "p", 0.0195, +1, "turned out to be beta (#22)"),
    ("23", "Rebalancing premium", "p", 0.73, +1, ""),
    ("24", "Funding carry basket (gross)", "p", 1e-6, +1, "dead at 5 %/yr costs"),
    ("26", "Funding carry tilt (gross)", "p", 1e-6, +1, "cash-plus, cost-fragile"),
    ("27", "Cross-exchange funding spread", "p", 1e-6, +1, "~1.5 %/yr, economically trivial"),
    ("34", "CAPE predicts 1-year real return", "t", 2.3, +1, ""),
    ("34", "CAPE predicts 3-year real return", "t", 2.0, +1, ""),
    ("34", "CAPE predicts 10-year real return", "t", 1.9, +1, "n = 14 windows"),
    ("34", "10-month trend filter (Shiller averages)", "p", 0.059, +1, "~2/3 artefact (#35)"),
    ("35", "Trend filter on true month-end closes", "p", 0.56, +1, ""),
    ("36", "Turn-of-month BEFORE publication", "t", 6.3, +1, "0/5 after publication"),
    ("36", "Monday effect BEFORE publication", "t", 6.1, +1, "0/5 after publication"),
    ("36", "Pre-holiday BEFORE publication", "t", 6.4, +1, "0/5 after publication"),
    ("37", "Volatility risk premium (VIX − realised)", "t", 12.6, +1, "a risk premium, not a forecast"),
    ("39", "PutWrite + trend vs S&P (Sharpe diff)", "p", 0.09, +1, ""),
    ("40", "Multi-asset trend long/short (long universe)", "p", 1e-5, +1, "Sharpe −30 % after 2012"),
    ("41", "Multi-asset trend vs placebo", "p", 0.01, +1, "placebo resolution 1/100"),
    ("41", "Realistic trend, broad universe", "p", 0.035, +1, "Sharpe 0.03 after 2012"),
    ("41", "Realistic trend, long universe", "p", 0.001, +1, ""),
    ("43", "Momentum factor UMD (US)", "t", 4.6, +1, ""),
    ("43", "Momentum factor (Europe)", "t", 4.7, +1, ""),
    ("43", "Low-variance long-only Sharpe gain", "p", 0.02, +1, ""),
    ("43", "Buffett mix long-only Sharpe gain", "p", 0.003, +1, ""),
    ("46", "Macro vote filter vs placebo", "p", 0.005, +1, "placebo floor"),
    ("47", "Index trend + macro on US stocks (placebo)", "p", 0.01, +1, ""),
    ("47", "Index trend + macro on CH stocks (placebo)", "p", 0.005, +1, "placebo floor"),
    ("47", "Index trend + macro on DE stocks (placebo)", "p", 0.03, +1, ""),
    ("48", "Insider cluster buys, calendar portfolio", "t", -0.96, +1, "wrong sign"),
    ("49", "Quality score Q5 − universe", "t", 0.42, +1, ""),
    ("50", "Buyback quintile − universe", "t", 3.01, +1, ""),
    ("50", "Issuance quintile underperforms", "t", 2.40, +1, ""),
    ("50", "Buybacks ∩ quality", "t", 2.76, +1, ""),
    ("50b", "App rule shares −2 %", "t", 2.8, +1, ""),
    ("50b", "Dilution +5 % underperforms", "t", 2.5, +1, ""),
    ("50b", "Buybacks value-weighted", "t", -0.3, +1, "wrong sign"),
    ("51", "Berkshire clone vs SPY", "t", -0.99, +1, "wrong sign"),
    ("51", "Hedge-fund best ideas vs SPY", "t", -0.12, +1, "wrong sign"),
    ("51", "Hedge-fund consensus vs SPY", "t", -0.09, +1, "wrong sign"),
    ("51", "All hedge-fund holdings vs SPY", "t", -0.47, +1, "wrong sign"),
    ("52", "Value, smallest stocks, after publication", "t", 3.3, +1, "micro caps"),
    ("52", "Momentum, smallest stocks, after publication", "t", 2.6, +1, "micro caps"),
    ("52", "Value, biggest stocks, after publication", "t", 0.6, +1, ""),
    ("52", "Momentum, biggest stocks, after publication", "t", 1.0, +1, ""),
    ("52", "Profitability, smallest stocks, after publication", "t", 0.0, +1, ""),
    ("53", "Buy after −20 % (S&P since 1871)", "p", 0.741, +1, ""),
    ("53", "Buy after −30 % (S&P since 1871)", "p", 0.635, +1, ""),
    ("53", "Buy after −40 % (S&P since 1871)", "p", 0.116, +1, ""),
    ("56", "Momentum big, developed 2011→ (OOS)", "t", 0.18, +1, ""),
    ("56", "Quality big, developed 2011→ (OOS)", "t", 1.32, +1, ""),
    ("56", "Small value, developed 2011→ (OOS)", "t", -1.00, +1, "wrong sign"),
    ("56", "Small momentum, developed 2011→ (OOS)", "t", 0.15, +1, "blind pick"),
    ("56", "Multi-factor 3, developed 2011→ (OOS)", "t", -0.18, +1, "wrong sign"),
    ("56", "Multi-factor 4, developed 2011→ (OOS)", "t", -0.02, +1, "wrong sign"),
    ("56", "Factor momentum, developed 2011→ (OOS)", "t", 0.35, +1, ""),
]

# Best strategies for the Deflated Sharpe: (name, annual Sharpe, years, skew, kurtosis)
DSR_CANDIDATES = [
    ("Multi-asset trend long/short, long universe (#40)", 0.76, 45, -0.3, 5.0),
    ("Live portfolio rule 1994–2026 (#44)", 0.75, 32, -0.5, 6.0),
    ("Realistic trend, long universe (#41)", 0.54, 45, -0.3, 5.0),
    ("Buyback quintile excess (#50, t 3.01 over 17 y)", 3.01 / math.sqrt(17), 17, 0.0, 4.0),
    ("Buybacks ∩ quality excess (#50, t 2.76 over 17 y)", 2.76 / math.sqrt(17), 17, 0.0, 4.0),
    ("Small value after publication (#52, t 3.3 over 34 y)", 3.3 / math.sqrt(34), 34, 0.3, 6.0),
]


def _phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _phi_inv(p):
    from statistics import NormalDist
    return NormalDist().inv_cdf(min(max(p, 1e-12), 1 - 1e-12))


def one_sided_p(kind: str, value: float, sign: int = +1) -> float:
    if kind == "p":
        return float(value)
    return 1 - _phi(sign * value)


def corrections(pvals: np.ndarray, m: int, q: float = 0.05) -> dict:
    """Bonferroni, Holm and Benjamini–Hochberg on `pvals`, as if m tests were run
    (the m − len(pvals) unreported tests count as p = 1)."""
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    bonf = p <= q / m
    holm = np.zeros(len(p), bool)
    for rank, i in enumerate(order):
        if p[i] <= q / (m - rank):
            holm[i] = True
        else:
            break
    bh = np.zeros(len(p), bool)
    k_max = -1
    for rank, i in enumerate(order):
        if p[i] <= q * (rank + 1) / m:
            k_max = rank
    if k_max >= 0:
        bh[order[:k_max + 1]] = True
    return {"bonferroni": bonf, "holm": holm, "bh": bh}


def deflated_sharpe(sr_ann: float, years: float, n_trials: int, sr_std_ann: float,
                    skew: float = 0.0, kurt: float = 3.0, periods: int = 12) -> float:
    """Bailey & López de Prado (2014). Returns P(true SR > 0 | best of n_trials)."""
    sr = sr_ann / math.sqrt(periods)
    v = (sr_std_ann / math.sqrt(periods)) ** 2
    T = years * periods
    g = 0.5772156649
    sr0 = math.sqrt(v) * ((1 - g) * _phi_inv(1 - 1 / n_trials) + g * _phi_inv(1 - 1 / (n_trials * math.e)))
    den = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    return _phi((sr - sr0) * math.sqrt(T - 1) / den)


def pbo_cscv(R: pd.DataFrame, S: int = 16, metric=None) -> dict:
    """Probability of backtest overfitting via CSCV. R: T×N strategy returns.
    Split rows into S blocks; for each of C(S, S/2) halves choose the in-sample best by
    `metric` (default Sharpe), measure its out-of-sample rank. PBO = P(logit ≤ 0)."""
    R = R.dropna()
    if metric is None:
        metric = lambda x: x.mean() / x.std(ddof=1).replace(0, np.nan)
    T, N = R.shape
    if N < 2 or T < S * 4:
        return {"pbo": float("nan"), "n_splits": 0}
    blocks = np.array_split(np.arange(T), S)
    logits, deg = [], []
    combos = list(itertools.combinations(range(S), S // 2))
    if len(combos) > 5000:
        rng = np.random.default_rng(57)
        combos = [combos[i] for i in rng.choice(len(combos), 5000, replace=False)]
    for c in combos:
        ins = np.concatenate([blocks[i] for i in c])
        oos = np.concatenate([blocks[i] for i in range(S) if i not in c])
        m_in, m_out = metric(R.iloc[ins]), metric(R.iloc[oos])
        best = m_in.idxmax()
        rank = (m_out.rank(method="average")[best]) / (N + 1)
        logits.append(math.log(rank / (1 - rank)))
        deg.append((m_in[best], m_out[best]))
    logits = np.array(logits)
    d = np.array(deg)
    return {"pbo": float((logits <= 0).mean()), "n_splits": len(logits),
            "is_best_mean": float(d[:, 0].mean()), "oos_of_best_mean": float(d[:, 1].mean()),
            "oos_median_all": float(np.median(d[:, 1]))}


def trend_grid(px_m: pd.Series, cash_m: pd.Series) -> pd.DataFrame:
    """Monthly trend rules on an index: in the market when price > SMA(L months) × (1 + b),
    else cash. L ∈ 2..12, buffer b ∈ {0, 1, 2 %}, plus buy & hold → T×34 returns."""
    r = px_m.pct_change()
    cash = cash_m.reindex(r.index).fillna(0.0)
    out = {"Buy & hold": r}
    for L in range(2, 13):
        sma = px_m.rolling(L).mean()
        for b in (0.0, 0.01, 0.02):
            sig = (px_m > sma * (1 + b)).astype(float).shift(1)
            trade = sig.diff().abs().fillna(0) * 0.001
            out[f"SMA{L}m buf{int(b*100)}%"] = sig * r + (1 - sig) * cash - trade
    return pd.DataFrame(out).dropna()


def _fmt_p(p):
    return "<0.000001" if p < 1e-6 else (f"{p:.4f}" if p < 0.01 else f"{p:.3f}")


def run_experiment57_report(families: dict, n_trials: int = N_TRIALS_PROJECT) -> str:
    """families: {name: T×N DataFrame of strategy returns} for part C."""
    from datetime import datetime, timezone
    L = [f"# Experiment #57 — the big overfitting test ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]

    # A
    reg = pd.DataFrame(REGISTER, columns=["exp", "test", "kind", "value", "sign", "note"])
    reg["p"] = [one_sided_p(k, v, s) for k, v, s in zip(reg["kind"], reg["value"], reg["sign"])]
    reg["t_equiv"] = [-_phi_inv(p) for p in reg["p"]]
    c = corrections(reg["p"].to_numpy(), m=n_trials)
    for k, v in c.items():
        reg[k] = v
    reg["hlz_t3"] = reg["t_equiv"] > 3.0
    L.append("## A Multiple testing over the whole project")
    L.append(f"Register: **{len(reg)}** reported test statistics from RESEARCH.md; project total ≈ **{n_trials}** "
             f"trials (unreported ones count as p = 1). One-sided p in the pre-registered direction. "
             f"Raw p < 0.05: **{int((reg['p'] < 0.05).sum())}**. Survive Bonferroni: **{int(reg['bonferroni'].sum())}**, "
             f"Holm: **{int(reg['holm'].sum())}**, Benjamini–Hochberg FDR 5 %: **{int(reg['bh'].sum())}**, "
             f"Harvey–Liu–Zhu t > 3: **{int(reg['hlz_t3'].sum())}**.")
    L.append("")
    L.append("| # | test | p (one-sided) | t-equiv. | p<0.05 | BH-FDR | Bonferroni | t>3 | note |")
    L.append("|---|---|--:|--:|:-:|:-:|:-:|:-:|---|")
    ok = lambda b: "✓" if b else "·"
    for _, r in reg.sort_values("p").iterrows():
        L.append(f"| {r['exp']} | {r['test']} | {_fmt_p(r['p'])} | {r['t_equiv']:.2f} | {ok(r['p'] < 0.05)} | "
                 f"{ok(r['bh'])} | {ok(r['bonferroni'])} | {ok(r['hlz_t3'])} | {r['note']} |")
    L.append("")
    expected_false = 0.05 * n_trials
    L.append(f"Pure chance would give ≈ {expected_false:.0f} of {n_trials} trials with p < 0.05; we observed "
             f"{int((reg['p'] < 0.05).sum())} (plus unreported ones).")
    L.append("")

    # B
    L.append("## B Deflated Sharpe ratio (probability the true Sharpe > 0)")
    L.append("Sharpe dispersion across trials is unknown → grid. Trials N = 56 (one per experiment) and "
             f"N = {n_trials} (every variant). Values > 0.95 = survives.")
    L.append("")
    grid = [(56, 0.2), (56, 0.4), (n_trials, 0.2), (n_trials, 0.4)]
    L.append("| strategy | Sharpe p.a. | years | " + " | ".join(f"N={n}, σ(SR)={s}" for n, s in grid) + " |")
    L.append("|---|--:|--:|" + "--:|" * len(grid))
    for name, sr, yrs, sk, ku in DSR_CANDIDATES:
        vals = [deflated_sharpe(sr, yrs, n, s, sk, ku) for n, s in grid]
        L.append(f"| {name} | {sr:.2f} | {yrs} | " + " | ".join(f"{v:.2f}" for v in vals) + " |")
    L.append("")

    # C
    L.append("## C Probability of backtest overfitting (CSCV, 16 blocks)")
    L.append("PBO = share of in-sample/out-of-sample splits in which the in-sample WINNER ends in the bottom half "
             "out-of-sample. ≈ 50 % = picking the winner is no better than picking at random.")
    L.append("")
    L.append("| family | strategies | months | PBO | Sharpe of IS winner: in-sample → out-of-sample | median OOS Sharpe of all |")
    L.append("|---|--:|--:|--:|--:|--:|")
    rng = np.random.default_rng(7)
    fam = dict(families)
    fam["Control: 30 pure-noise strategies"] = pd.DataFrame(rng.normal(0.005, 0.04, (600, 30)))
    for name, R in fam.items():
        if R is None or R.empty:
            L.append(f"| {name} | — | — | no data | — | — |")
            continue
        res = pbo_cscv(R)
        ann = math.sqrt(12)
        L.append(f"| {name} | {R.shape[1]} | {len(R.dropna())} | **{100*res['pbo']:.0f}%** | "
                 f"{res['is_best_mean']*ann:.2f} → {res['oos_of_best_mean']*ann:.2f} | {res['oos_median_all']*ann:.2f} |")
    L.append("")
    L.append("Reading: a low PBO means the in-sample winner tends to stay good — the family has a real, stable "
             "ranking. A PBO near 50 % means 'the best backtest' is mostly luck.")
    return "\n".join(L)
