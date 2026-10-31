# Experiment #84 — final balance over the whole project (2026-10-31 16:01 UTC)

Register: **93** reported statistics from #11–#86; project total ≈ **630** trials (unreported = p 1). One-sided p in the pre-registered direction.
Raw p < 0.05: **41** (pure chance would give ≈ 32 of 630). Survive Bonferroni: **11**, Holm: **11**, Benjamini–Hochberg 5 %: **18**, Harvey–Liu–Zhu t > 3: **18**.
Sensitivity m = 320: Bonferroni 11, Holm 11, BH 21.

| # | test | p (one-sided) | t-equiv. | BH-FDR | Bonferroni | t>3 | note |
|---|---|--:|--:|:-:|:-:|:-:|---|
| 37 | Volatility risk premium (VIX − realised) | <0.000001 | 7.03 | ✓ | ✓ | ✓ | a risk premium, not a forecast |
| 76 | Insider cluster sales vs own control dates 12 M | <0.000001 | 6.90 | ✓ | ✓ | ✓ | design likely confounded |
| 36 | Pre-holiday BEFORE publication | <0.000001 | 6.40 | ✓ | ✓ | ✓ | 0/5 after publication |
| 36 | Turn-of-month BEFORE publication | <0.000001 | 6.30 | ✓ | ✓ | ✓ | 0/5 after publication |
| 36 | Monday effect BEFORE publication | <0.000001 | 6.10 | ✓ | ✓ | ✓ | 0/5 after publication |
| 24 | Funding carry basket (gross) | 0.0000 | 4.75 | ✓ | ✓ | ✓ | dead at 5 %/yr costs |
| 26 | Funding carry tilt (gross) | 0.0000 | 4.75 | ✓ | ✓ | ✓ | cash-plus, cost-fragile |
| 27 | Cross-exchange funding spread | 0.0000 | 4.75 | ✓ | ✓ | ✓ | ~1.5 %/yr, economically trivial |
| 43 | Momentum factor (Europe) | 0.0000 | 4.70 | ✓ | ✓ | ✓ |  |
| 43 | Momentum factor UMD (US) | 0.0000 | 4.60 | ✓ | ✓ | ✓ |  |
| 40 | Multi-asset trend long/short (long universe) | 0.0000 | 4.26 | ✓ | ✓ | ✓ | Sharpe −30 % after 2012 |
| 52 | Value, smallest stocks, after publication | 0.0005 | 3.30 | ✓ | · | ✓ | micro caps |
| 17 | RSI(2) low-vol regime SPY | 0.0010 | 3.09 | ✓ | · | ✓ | contradicted pre-registration |
| 12 | RSI(2) reversal SPY | 0.0010 | 3.09 | ✓ | · | ✓ | gross of realistic costs (#13) |
| 12 | RSI(2) reversal QQQ | 0.0010 | 3.09 | ✓ | · | ✓ | gross of realistic costs (#13) |
| 41 | Realistic trend, long universe | 0.0010 | 3.09 | ✓ | · | ✓ |  |
| 62 | Buybacks rank IC (walk-forward) | 0.0010 | 3.08 | ✓ | · | ✓ | 3rd confirmation of #50 |
| 50 | Buyback quintile − universe | 0.0013 | 3.01 | ✓ | · | ✓ |  |
| 50b | App rule shares −2 % | 0.0026 | 2.80 | · | · | · |  |
| 50 | Buybacks ∩ quality | 0.0029 | 2.76 | · | · | · |  |
| 43 | Buffett mix long-only Sharpe gain | 0.0030 | 2.75 | · | · | · |  |
| 52 | Momentum, smallest stocks, after publication | 0.0047 | 2.60 | · | · | · | micro caps |
| 47 | Index trend + macro on CH stocks (placebo) | 0.0050 | 2.58 | · | · | · | placebo floor |
| 46 | Macro vote filter vs placebo | 0.0050 | 2.58 | · | · | · | placebo floor |
| 75 | Post-earnings drift top − bottom SUE decile (all) | 0.0052 | 2.56 | · | · | · | since 2016 t 1.32 |
| 50b | Dilution +5 % underperforms | 0.0062 | 2.50 | · | · | · |  |
| 50 | Issuance quintile underperforms | 0.0082 | 2.40 | · | · | · |  |
| 41 | Multi-asset trend vs placebo | 0.010 | 2.33 | · | · | · | placebo resolution 1/100 |
| 47 | Index trend + macro on US stocks (placebo) | 0.010 | 2.33 | · | · | · |  |
| 34 | CAPE predicts 1-year real return | 0.011 | 2.30 | · | · | · |  |
| 86 | Best event cell (S&P −10 % → SMI 1 M), bootstrap | 0.016 | 2.14 | · | · | · | 0/75 after Holm |
| 21 | Momentum long-only top decile | 0.019 | 2.06 | · | · | · | turned out to be beta (#22) |
| 43 | Low-variance long-only Sharpe gain | 0.020 | 2.05 | · | · | · |  |
| 34 | CAPE predicts 3-year real return | 0.023 | 2.00 | · | · | · |  |
| 34 | CAPE predicts 10-year real return | 0.029 | 1.90 | · | · | · | n = 14 windows |
| 15 | Machine learning (logit) QQQ direction | 0.030 | 1.88 | · | · | · |  |
| 47 | Index trend + macro on DE stocks (placebo) | 0.030 | 1.88 | · | · | · |  |
| 41 | Realistic trend, broad universe | 0.035 | 1.81 | · | · | · | Sharpe 0.03 after 2012 |
| 85 | Fair value Q5 − Q1 | 0.036 | 1.80 | · | · | · |  |
| 11 | XLE seasonality | 0.044 | 1.71 | · | · | · |  |
(top 40 of 93 shown; the rest have p > 0.044)

## Deflated Sharpe (N = 630 trials) — probability the true Sharpe > 0
| strategy | Sharpe p.a. | years | σ(SR)=0.2 | σ(SR)=0.4 |
|---|--:|--:|--:|--:|
| Multi-asset trend long/short, long universe (#40) | 0.76 | 45 | 0.81 | 0.00 |
| Live portfolio rule 1994–2026 (#44) | 0.75 | 32 | 0.74 | 0.00 |
| Realistic trend, long universe (#41) | 0.54 | 45 | 0.29 | 0.00 |
| Buyback quintile excess (#50, t 3.01 over 17 y) | 0.73 | 17 | 0.67 | 0.02 |
| Buybacks ∩ quality excess (#50, t 2.76 over 17 y) | 0.67 | 17 | 0.57 | 0.01 |
| Small value after publication (#52, t 3.3 over 34 y) | 0.57 | 34 | 0.37 | 0.00 |
| Buybacks rank IC walk-forward (#62, t 3.08 over 15 y) | 0.80 | 15 | 0.74 | 0.04 |
| Post-earnings drift top − bottom (#75, t 2.56 over 16 y) | 0.64 | 16 | 0.52 | 0.01 |

Caveat: some survivors are design artefacts flagged in RESEARCH.md (e.g. #76 control dates, RSI(2) gross of costs) — statistical survival is necessary, not sufficient.