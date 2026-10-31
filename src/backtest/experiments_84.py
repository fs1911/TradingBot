"""
Experiment #84 — the final balance: every reported test statistic of the project in one
register, multiple-testing correction over ALL trials (update of #57, which covered #11–#56).

Trials: #57 counted ≈ 270 up to #56. Since then: #60 164 minute rules, #61 ≈ 50 map cells,
#86 75 event cells, #62–#85 ≈ 70 further variants → ≈ 630. Unreported trials count as p = 1.
Sensitivity: m = 320 (the Bonferroni base used in the individual reports).
Corrections: Bonferroni, Holm, Benjamini–Hochberg (5 %), Harvey–Liu–Zhu t > 3.
Part B: Deflated Sharpe of the best strategies with N = 630.
Pure (no data needed).
"""
from __future__ import annotations
import pandas as pd

from .experiments_57 import (REGISTER, DSR_CANDIDATES, one_sided_p, corrections, deflated_sharpe,
                             _phi_inv, _fmt_p)

N_TRIALS_TOTAL = 630

ADD = [
    # #59–#86 (values from RESEARCH.md / experiment*_results.md)
    ("60", "Best minute rule 1st half → 2nd half (ETH 1m reversal)", "t", -1.05, +1, "selection fails OOS"),
    ("61", "Daily index autocorrelation, OOS R² > 0 (median cell)", "p", 0.5, +1, "median OOS R² ≈ 0"),
    ("61", "CAPE predicts 10-year real return, out-of-sample", "p", 0.05, +1, "OOS R² +23 %, ~8 independent decades"),
    ("62", "Buybacks rank IC (walk-forward)", "t", 3.08, +1, "3rd confirmation of #50"),
    ("62", "Boosted trees rank IC (walk-forward)", "t", 0.68, +1, ""),
    ("62", "Ridge regression rank IC (walk-forward)", "t", -0.05, +1, "wrong sign"),
    ("62", "Human rule (buybacks+quality+momentum) rank IC", "t", 0.73, +1, ""),
    ("63", "SPF 10-year stock expectations vs reality (corr −0.32)", "p", 0.94, +1, "wrong sign"),
    ("63", "Livingston 12-m direction vs 'always up'", "p", 0.7, +1, "73 % vs 76 %"),
    ("64", "Buyback − dilution, CH/EU (3 years)", "t", -0.07, +1, "not testable (Yahoo 4 y)"),
    ("65", "Buy check: red underperforms (June cohorts)", "t", 0.91, +1, "disasters 9.0 % vs 4.9 %"),
    ("65", "Dilution ≥ 5 % underperforms (June cohorts)", "t", 0.91, +1, "disasters 10.2 %"),
    ("67", "Hedging USD into CHF beats unhedged (10-y windows 46 %)", "p", 0.6, +1, ""),
    ("68", "Home bias (more CH) improves Sharpe", "p", 0.9, +1, "wrong sign"),
    ("69", "2× daily leverage beats 1× (20-y windows 65 %)", "p", 0.2, +1, "ruin −98 %"),
    ("70", "Staging beats lump sum", "p", 0.99, +1, "lump sum wins 62–66 %"),
    ("83", "HMM regime switching beats buy & hold (walk-forward)", "p", 0.3, +1, "+0.5 pt/yr, trend rule better"),
    ("75", "Post-earnings drift top − bottom SUE decile (all)", "t", 2.56, +1, "since 2016 t 1.32"),
    ("75", "Post-earnings drift since 2016", "t", 1.32, +1, ""),
    ("76", "Insider cluster sales underperform (calendar portfolio vs SPY)", "t", 0.98, -1, "wrong sign"),
    ("76", "Insider cluster sales vs own control dates 12 M", "t", -6.9, -1, "design likely confounded"),
    ("76", "Very large insider sales vs SPY (calendar)", "t", 0.36, -1, "wrong sign"),
    ("79", "Dividend growers (5 y) beat universe", "t", -0.79, +1, "wrong sign"),
    ("79", "Dividend initiators beat universe", "t", 0.47, +1, ""),
    ("79", "Dividend cutters underperform", "t", -0.01, -1, ""),
    ("85", "Fair value most undervalued quintile beats universe", "t", 1.7, +1, ""),
    ("85", "Fair value Q5 − Q1", "t", 1.8, +1, ""),
    ("85", "Health score best quintile beats universe", "t", 0.0, +1, "worst quintile +3.4 %, t 2.1"),
    ("86", "Best event cell (S&P −10 % → SMI 1 M), bootstrap", "p", 0.016, +1, "0/75 after Holm"),
    ("86", "VIX > 40 → S&P 6 M above any day", "p", 0.089, +1, "two-sided bootstrap"),
    ("77", "Most − least shorted decile underperforms (1 M)", "t", -1.07, -1, "FINRA 2017→"),
]


DSR_EXTRA = [
    ("Buybacks rank IC walk-forward (#62, t 3.08 over 15 y)", 3.08 / 15 ** 0.5, 15, 0.0, 4.0),
    ("Post-earnings drift top − bottom (#75, t 2.56 over 16 y)", 2.56 / 16 ** 0.5, 16, 0.0, 4.0),
]


def register() -> pd.DataFrame:
    reg = pd.DataFrame(REGISTER + ADD, columns=["exp", "test", "kind", "value", "sign", "note"])
    reg["p"] = [one_sided_p(k, v, s) for k, v, s in zip(reg["kind"], reg["value"], reg["sign"])]
    reg["t_equiv"] = [-_phi_inv(min(max(p, 1e-12), 1 - 1e-12)) for p in reg["p"]]
    return reg


def run_experiment84_report(n_trials: int = N_TRIALS_TOTAL, n_alt: int = 320) -> str:
    from datetime import datetime, timezone
    reg = register()
    for k, v in corrections(reg["p"].to_numpy(), m=n_trials).items():
        reg[k] = v
    alt = corrections(reg["p"].to_numpy(), m=n_alt)
    reg["hlz_t3"] = reg["t_equiv"] > 3.0
    L = [f"# Experiment #84 — final balance over the whole project ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append(f"Register: **{len(reg)}** reported statistics from #11–#86; project total ≈ **{n_trials}** trials "
             f"(unreported = p 1). One-sided p in the pre-registered direction.")
    L.append(f"Raw p < 0.05: **{int((reg['p'] < 0.05).sum())}** (pure chance would give ≈ {0.05*n_trials:.0f} of {n_trials}). "
             f"Survive Bonferroni: **{int(reg['bonferroni'].sum())}**, Holm: **{int(reg['holm'].sum())}**, "
             f"Benjamini–Hochberg 5 %: **{int(reg['bh'].sum())}**, Harvey–Liu–Zhu t > 3: **{int(reg['hlz_t3'].sum())}**.")
    L.append(f"Sensitivity m = {n_alt}: Bonferroni {int(alt['bonferroni'].sum())}, Holm {int(alt['holm'].sum())}, "
             f"BH {int(alt['bh'].sum())}.")
    L.append("")
    L.append("| # | test | p (one-sided) | t-equiv. | BH-FDR | Bonferroni | t>3 | note |")
    L.append("|---|---|--:|--:|:-:|:-:|:-:|---|")
    ok = lambda b: "✓" if b else "·"
    for _, r in reg.sort_values("p").head(40).iterrows():
        L.append(f"| {r['exp']} | {r['test']} | {_fmt_p(r['p'])} | {r['t_equiv']:.2f} | {ok(r['bh'])} | "
                 f"{ok(r['bonferroni'])} | {ok(r['hlz_t3'])} | {r['note']} |")
    L.append(f"(top 40 of {len(reg)} shown; the rest have p > {reg.sort_values('p')['p'].iloc[min(39, len(reg)-1)]:.3f})")
    L.append("")
    L.append(f"## Deflated Sharpe (N = {n_trials} trials) — probability the true Sharpe > 0")
    L.append("| strategy | Sharpe p.a. | years | σ(SR)=0.2 | σ(SR)=0.4 |")
    L.append("|---|--:|--:|--:|--:|")
    for name, sr, yrs, sk, ku in list(DSR_CANDIDATES) + DSR_EXTRA:
        L.append(f"| {name} | {sr:.2f} | {yrs} | {deflated_sharpe(sr, yrs, n_trials, 0.2, sk, ku):.2f} | "
                 f"{deflated_sharpe(sr, yrs, n_trials, 0.4, sk, ku):.2f} |")
    L.append("")
    L.append("Caveat: some survivors are design artefacts flagged in RESEARCH.md (e.g. #76 control dates, "
             "RSI(2) gross of costs) — statistical survival is necessary, not sufficient.")
    return "\n".join(L)
