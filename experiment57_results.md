# Experiment #57 — the big overfitting test (2026-10-27 17:30 UTC)

## A Multiple testing over the whole project
Register: **62** reported test statistics from RESEARCH.md; project total ≈ **270** trials (unreported ones count as p = 1). One-sided p in the pre-registered direction. Raw p < 0.05: **35**. Survive Bonferroni: **10**, Holm: **10**, Benjamini–Hochberg FDR 5 %: **19**, Harvey–Liu–Zhu t > 3: **16**.

| # | test | p (one-sided) | t-equiv. | p<0.05 | BH-FDR | Bonferroni | t>3 | note |
|---|---|--:|--:|:-:|:-:|:-:|:-:|---|
| 37 | Volatility risk premium (VIX − realised) | <0.000001 | 7.03 | ✓ | ✓ | ✓ | ✓ | a risk premium, not a forecast |
| 36 | Pre-holiday BEFORE publication | <0.000001 | 6.40 | ✓ | ✓ | ✓ | ✓ | 0/5 after publication |
| 36 | Turn-of-month BEFORE publication | <0.000001 | 6.30 | ✓ | ✓ | ✓ | ✓ | 0/5 after publication |
| 36 | Monday effect BEFORE publication | <0.000001 | 6.10 | ✓ | ✓ | ✓ | ✓ | 0/5 after publication |
| 24 | Funding carry basket (gross) | 0.0000 | 4.75 | ✓ | ✓ | ✓ | ✓ | dead at 5 %/yr costs |
| 27 | Cross-exchange funding spread | 0.0000 | 4.75 | ✓ | ✓ | ✓ | ✓ | ~1.5 %/yr, economically trivial |
| 26 | Funding carry tilt (gross) | 0.0000 | 4.75 | ✓ | ✓ | ✓ | ✓ | cash-plus, cost-fragile |
| 43 | Momentum factor (Europe) | 0.0000 | 4.70 | ✓ | ✓ | ✓ | ✓ |  |
| 43 | Momentum factor UMD (US) | 0.0000 | 4.60 | ✓ | ✓ | ✓ | ✓ |  |
| 40 | Multi-asset trend long/short (long universe) | 0.0000 | 4.26 | ✓ | ✓ | ✓ | ✓ | Sharpe −30 % after 2012 |
| 52 | Value, smallest stocks, after publication | 0.0005 | 3.30 | ✓ | ✓ | · | ✓ | micro caps |
| 41 | Realistic trend, long universe | 0.0010 | 3.09 | ✓ | ✓ | · | ✓ |  |
| 17 | RSI(2) low-vol regime SPY | 0.0010 | 3.09 | ✓ | ✓ | · | ✓ | contradicted pre-registration |
| 12 | RSI(2) reversal SPY | 0.0010 | 3.09 | ✓ | ✓ | · | ✓ | gross of realistic costs (#13) |
| 12 | RSI(2) reversal QQQ | 0.0010 | 3.09 | ✓ | ✓ | · | ✓ | gross of realistic costs (#13) |
| 50 | Buyback quintile − universe | 0.0013 | 3.01 | ✓ | ✓ | · | ✓ |  |
| 50b | App rule shares −2 % | 0.0026 | 2.80 | ✓ | ✓ | · | · |  |
| 50 | Buybacks ∩ quality | 0.0029 | 2.76 | ✓ | ✓ | · | · |  |
| 43 | Buffett mix long-only Sharpe gain | 0.0030 | 2.75 | ✓ | ✓ | · | · |  |
| 52 | Momentum, smallest stocks, after publication | 0.0047 | 2.60 | ✓ | · | · | · | micro caps |
| 47 | Index trend + macro on CH stocks (placebo) | 0.0050 | 2.58 | ✓ | · | · | · | placebo floor |
| 46 | Macro vote filter vs placebo | 0.0050 | 2.58 | ✓ | · | · | · | placebo floor |
| 50b | Dilution +5 % underperforms | 0.0062 | 2.50 | ✓ | · | · | · |  |
| 50 | Issuance quintile underperforms | 0.0082 | 2.40 | ✓ | · | · | · |  |
| 41 | Multi-asset trend vs placebo | 0.010 | 2.33 | ✓ | · | · | · | placebo resolution 1/100 |
| 47 | Index trend + macro on US stocks (placebo) | 0.010 | 2.33 | ✓ | · | · | · |  |
| 34 | CAPE predicts 1-year real return | 0.011 | 2.30 | ✓ | · | · | · |  |
| 21 | Momentum long-only top decile | 0.019 | 2.06 | ✓ | · | · | · | turned out to be beta (#22) |
| 43 | Low-variance long-only Sharpe gain | 0.020 | 2.05 | ✓ | · | · | · |  |
| 34 | CAPE predicts 3-year real return | 0.023 | 2.00 | ✓ | · | · | · |  |
| 34 | CAPE predicts 10-year real return | 0.029 | 1.90 | ✓ | · | · | · | n = 14 windows |
| 15 | Machine learning (logit) QQQ direction | 0.030 | 1.88 | ✓ | · | · | · |  |
| 47 | Index trend + macro on DE stocks (placebo) | 0.030 | 1.88 | ✓ | · | · | · |  |
| 41 | Realistic trend, broad universe | 0.035 | 1.81 | ✓ | · | · | · | Sharpe 0.03 after 2012 |
| 11 | XLE seasonality | 0.044 | 1.71 | ✓ | · | · | · |  |
| 34 | 10-month trend filter (Shiller averages) | 0.059 | 1.56 | · | · | · | · | ~2/3 artefact (#35) |
| 39 | PutWrite + trend vs S&P (Sharpe diff) | 0.090 | 1.34 | · | · | · | · |  |
| 56 | Quality big, developed 2011→ (OOS) | 0.093 | 1.32 | · | · | · | · |  |
| 53 | Buy after −40 % (S&P since 1871) | 0.116 | 1.20 | · | · | · | · |  |
| 20 | Momentum long/short 92 stocks | 0.150 | 1.04 | · | · | · | · |  |
| 52 | Momentum, biggest stocks, after publication | 0.159 | 1.00 | · | · | · | · |  |
| 52 | Value, biggest stocks, after publication | 0.274 | 0.60 | · | · | · | · |  |
| 49 | Quality score Q5 − universe | 0.337 | 0.42 | · | · | · | · |  |
| 56 | Factor momentum, developed 2011→ (OOS) | 0.363 | 0.35 | · | · | · | · |  |
| 56 | Momentum big, developed 2011→ (OOS) | 0.429 | 0.18 | · | · | · | · |  |
| 56 | Small momentum, developed 2011→ (OOS) | 0.440 | 0.15 | · | · | · | · | blind pick |
| 52 | Profitability, smallest stocks, after publication | 0.500 | -0.00 | · | · | · | · |  |
| 56 | Multi-factor 4, developed 2011→ (OOS) | 0.508 | -0.02 | · | · | · | · | wrong sign |
| 51 | Hedge-fund consensus vs SPY | 0.536 | -0.09 | · | · | · | · | wrong sign |
| 51 | Hedge-fund best ideas vs SPY | 0.548 | -0.12 | · | · | · | · | wrong sign |
| 35 | Trend filter on true month-end closes | 0.560 | -0.15 | · | · | · | · |  |
| 56 | Multi-factor 3, developed 2011→ (OOS) | 0.571 | -0.18 | · | · | · | · | wrong sign |
| 50b | Buybacks value-weighted | 0.618 | -0.30 | · | · | · | · | wrong sign |
| 53 | Buy after −30 % (S&P since 1871) | 0.635 | -0.35 | · | · | · | · |  |
| 51 | All hedge-fund holdings vs SPY | 0.681 | -0.47 | · | · | · | · | wrong sign |
| 23 | Rebalancing premium | 0.730 | -0.61 | · | · | · | · |  |
| 53 | Buy after −20 % (S&P since 1871) | 0.741 | -0.65 | · | · | · | · |  |
| 48 | Insider cluster buys, calendar portfolio | 0.831 | -0.96 | · | · | · | · | wrong sign |
| 51 | Berkshire clone vs SPY | 0.839 | -0.99 | · | · | · | · | wrong sign |
| 56 | Small value, developed 2011→ (OOS) | 0.841 | -1.00 | · | · | · | · | wrong sign |
| 11 | Copper lead-lag | 0.995 | -2.60 | · | · | · | · | wrong sign |
| 20 | Short-term reversal after costs | 1.000 | -3.70 | · | · | · | · | wrong sign |

Pure chance would give ≈ 14 of 270 trials with p < 0.05; we observed 35 (plus unreported ones).

## B Deflated Sharpe ratio (probability the true Sharpe > 0)
Sharpe dispersion across trials is unknown → grid. Trials N = 56 (one per experiment) and N = 270 (every variant). Values > 0.95 = survives.

| strategy | Sharpe p.a. | years | N=56, σ(SR)=0.2 | N=56, σ(SR)=0.4 | N=270, σ(SR)=0.2 | N=270, σ(SR)=0.4 |
|---|--:|--:|--:|--:|--:|--:|
| Multi-asset trend long/short, long universe (#40) | 0.76 | 45 | 0.97 | 0.14 | 0.88 | 0.01 |
| Live portfolio rule 1994–2026 (#44) | 0.75 | 32 | 0.93 | 0.18 | 0.82 | 0.02 |
| Realistic trend, long universe (#41) | 0.54 | 45 | 0.69 | 0.01 | 0.42 | 0.00 |
| Buyback quintile excess (#50, t 3.01 over 17 y) | 0.73 | 17 | 0.86 | 0.21 | 0.74 | 0.05 |
| Buybacks ∩ quality excess (#50, t 2.76 over 17 y) | 0.67 | 17 | 0.80 | 0.15 | 0.65 | 0.03 |
| Small value after publication (#52, t 3.3 over 34 y) | 0.57 | 34 | 0.73 | 0.02 | 0.48 | 0.00 |

## C Probability of backtest overfitting (CSCV, 16 blocks)
PBO = share of in-sample/out-of-sample splits in which the in-sample WINNER ends in the bottom half out-of-sample. ≈ 50 % = picking the winner is no better than picking at random.

| family | strategies | months | PBO | Sharpe of IS winner: in-sample → out-of-sample | median OOS Sharpe of all |
|---|--:|--:|--:|--:|--:|
| S&P 500 trend-rule grid 1928→ (34 rules) | 34 | 1186 | **43%** | 0.74 → 0.58 | 0.60 |
| Factor candidates #56, developed 1990→ | 8 | 419 | **60%** | 0.85 → 0.70 | 0.70 |
| Factor candidates #56, USA 1963→ | 8 | 747 | **19%** | 0.91 → 0.86 | 0.87 |
| Control: 30 pure-noise strategies | 30 | 600 | **56%** | 0.78 → 0.34 | 0.37 |

Reading: a low PBO means the in-sample winner tends to stay good — the family has a real, stable ranking. A PBO near 50 % means 'the best backtest' is mostly luck.