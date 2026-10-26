# Experiment #56 — can an implementable portfolio beat the MSCI World on return? (2026-10-26 13:34 UTC)

Files: dev_bm → Developed_6_Portfolios_ME_BE-ME_CSV.zip, dev_op → Developed_6_Portfolios_ME_OP_CSV.zip, dev_mom → Developed_6_Portfolios_ME_Prior_12_2_CSV.zip, dev_ff → Developed_5_Factors_CSV.zip, us_bm → 6_Portfolios_2x3_CSV.zip, us_op → 6_Portfolios_ME_OP_2x3_CSV.zip, us_mom → 6_Portfolios_ME_Prior_12_2_CSV.zip, us_ff → F-F_Research_Data_5_Factors_2x3_CSV.zip.
All returns NET of pre-registered costs (momentum 1.0 %, small momentum 1.5 %, small value 0.8 %, quality 0.5 %, market 0.15 % p.a.; factor momentum + 0.2 % per switch). Bonferroni α/270 → |t| ≳ 3.7. 'Worst lag' = deepest fall of the portfolio RELATIVE to the market; 'longest' = months below its previous relative high.

## A Developed markets (≈ MSCI World)
### A Developed markets (≈ MSCI World) — full (1990-11 → 2026-08)
| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | 5-y windows won | years won |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| P1 Momentum big | 430 | +9.7% | **+0.8%** | 0.80 | 0.50 | -53% | -34% / 318 M | 60% | 65% |
| P2 Quality big | 430 | +9.7% | **+0.9%** | 1.31 | 0.55 | -48% | -15% / 120 M | 64% | 59% |
| P3 Small value | 430 | +10.8% | **+1.9%** | 1.54 | 0.58 | -54% | -36% / 196 M | 49% | 59% |
| P4 Small momentum | 430 | +12.6% | **+3.8%** | 2.71 | 0.64 | -57% | -25% / 99 M | 58% | 59% |
| P5 Multi-factor 3 | 430 | +10.2% | **+1.4%** | 2.23 | 0.58 | -51% | -9% / 210 M | 65% | 65% |
| P6 Multi-factor 4 | 430 | +10.8% | **+2.0%** | 2.64 | 0.60 | -53% | -13% / 99 M | 65% | 68% |
| P7 Factor momentum | 418 | +12.0% | **+3.3%** | 2.80 | 0.65 | -53% | -24% / 72 M | 80% | 56% |
| Market (benchmark, net 0.15 %) | 430 | +8.9% | — | — | — | — | — | — | — |

### A Developed markets (≈ MSCI World) — in-sample ≤2010 (1990-11 → 2010-12)
| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | 5-y windows won | years won |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| P1 Momentum big | 242 | +8.8% | **+1.3%** | 0.83 | 0.38 | -53% | -34% / 130 M | 62% | 71% |
| P2 Quality big | 242 | +8.0% | **+0.6%** | 0.58 | 0.37 | -48% | -15% / 83 M | 46% | 57% |
| P3 Small value | 242 | +12.3% | **+4.9%** | 2.73 | 0.62 | -54% | -31% / 85 M | 60% | 71% |
| P4 Small momentum | 242 | +14.2% | **+6.7%** | 3.07 | 0.65 | -57% | -25% / 41 M | 70% | 67% |
| P5 Multi-factor 3 | 242 | +9.9% | **+2.4%** | 2.59 | 0.49 | -51% | -9% / 28 M | 76% | 81% |
| P6 Multi-factor 4 | 242 | +11.0% | **+3.5%** | 3.00 | 0.54 | -53% | -13% / 36 M | 75% | 76% |
| P7 Factor momentum | 230 | +12.7% | **+5.6%** | 3.01 | 0.60 | -53% | -24% / 47 M | 74% | 65% |
| Market (benchmark, net 0.15 %) | 242 | +7.4% | — | — | — | — | — | — | — |

### A Developed markets (≈ MSCI World) — OUT-OF-SAMPLE 2011→ (2011-01 → 2026-08)
| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | 5-y windows won | years won |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| P1 Momentum big | 188 | +10.9% | **+0.2%** | 0.18 | 0.67 | -27% | -17% / 72 M | 46% | 56% |
| P2 Quality big | 188 | +11.9% | **+1.2%** | 1.32 | 0.78 | -26% | -8% / 73 M | 61% | 62% |
| P3 Small value | 188 | +8.8% | **-2.0%** | -1.00 | 0.53 | -37% | -34% / 185 M | 13% | 44% |
| P4 Small momentum | 188 | +10.7% | **-0.1%** | 0.15 | 0.62 | -30% | -25% / 99 M | 22% | 50% |
| P5 Multi-factor 3 | 188 | +10.7% | **-0.0%** | -0.18 | 0.70 | -24% | -6% / 99 M | 27% | 44% |
| P6 Multi-factor 4 | 188 | +10.7% | **-0.0%** | -0.02 | 0.68 | -24% | -10% / 99 M | 23% | 56% |
| P7 Factor momentum | 188 | +11.2% | **+0.5%** | 0.35 | 0.72 | -22% | -14% / 72 M | 56% | 44% |
| Market (benchmark, net 0.15 %) | 188 | +10.7% | — | — | — | — | — | — | — |

### A Developed markets (≈ MSCI World) — 2016→ (2016-01 → 2026-08)
| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | 5-y windows won | years won |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| P1 Momentum big | 128 | +12.0% | **-0.2%** | -0.05 | 0.67 | -27% | -17% / 72 M | 24% | 55% |
| P2 Quality big | 128 | +13.6% | **+1.4%** | 1.10 | 0.80 | -26% | -8% / 31 M | 54% | 64% |
| P3 Small value | 128 | +10.7% | **-1.5%** | -0.53 | 0.58 | -37% | -32% / 115 M | 9% | 45% |
| P4 Small momentum | 128 | +11.2% | **-1.1%** | -0.30 | 0.58 | -30% | -25% / 99 M | 5% | 45% |
| P5 Multi-factor 3 | 128 | +12.3% | **+0.0%** | -0.02 | 0.72 | -24% | -6% / 99 M | 19% | 45% |
| P6 Multi-factor 4 | 128 | +12.1% | **-0.2%** | -0.18 | 0.69 | -24% | -10% / 99 M | 5% | 55% |
| P7 Factor momentum | 128 | +12.7% | **+0.4%** | 0.21 | 0.74 | -22% | -14% / 72 M | 38% | 45% |
| Market (benchmark, net 0.15 %) | 128 | +12.3% | — | — | — | — | — | — | — |

P7 factor momentum switched 3.4 legs per year on average.

## B USA (robustness)
### B USA (robustness) — full (1963-07 → 2026-08)
| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | 5-y windows won | years won |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| P1 Momentum big | 758 | +12.3% | **+1.5%** | 1.94 | 0.52 | -49% | -30% / 218 M | 62% | 58% |
| P2 Quality big | 758 | +11.5% | **+0.8%** | 1.44 | 0.51 | -48% | -27% / 332 M | 64% | 55% |
| P3 Small value | 758 | +14.1% | **+3.4%** | 2.75 | 0.55 | -62% | -57% / 245 M | 55% | 61% |
| P4 Small momentum | 758 | +15.5% | **+4.8%** | 3.80 | 0.59 | -55% | -41% / 245 M | 59% | 56% |
| P5 Multi-factor 3 | 758 | +12.9% | **+2.2%** | 4.23 | 0.57 | -49% | -18% / 196 M | 70% | 62% |
| P6 Multi-factor 4 | 758 | +13.6% | **+2.9%** | 4.36 | 0.58 | -51% | -22% / 245 M | 63% | 62% |
| P7 Factor momentum | 746 | +15.6% | **+5.0%** | 4.72 | 0.66 | -52% | -23% / 166 M | 74% | 65% |
| Market (benchmark, net 0.15 %) | 758 | +10.7% | — | — | — | — | — | — | — |

### B USA (robustness) — in-sample ≤2010 (1963-07 → 2010-12)
| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | 5-y windows won | years won |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| P1 Momentum big | 570 | +12.2% | **+2.5%** | 2.53 | 0.45 | -49% | -21% / 150 M | 77% | 60% |
| P2 Quality big | 570 | +10.4% | **+0.7%** | 1.03 | 0.38 | -48% | -27% / 332 M | 59% | 50% |
| P3 Small value | 570 | +15.4% | **+5.8%** | 3.80 | 0.56 | -62% | -35% / 105 M | 67% | 69% |
| P4 Small momentum | 570 | +16.6% | **+6.9%** | 4.42 | 0.58 | -55% | -32% / 102 M | 69% | 62% |
| P5 Multi-factor 3 | 570 | +12.9% | **+3.2%** | 5.20 | 0.50 | -49% | -9% / 32 M | 84% | 73% |
| P6 Multi-factor 4 | 570 | +13.9% | **+4.2%** | 5.25 | 0.54 | -51% | -13% / 68 M | 76% | 71% |
| P7 Factor momentum | 558 | +16.2% | **+6.7%** | 5.28 | 0.62 | -52% | -23% / 59 M | 81% | 70% |
| Market (benchmark, net 0.15 %) | 570 | +9.7% | — | — | — | — | — | — | — |

### B USA (robustness) — OUT-OF-SAMPLE 2011→ (2011-01 → 2026-08)
| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | 5-y windows won | years won |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| P1 Momentum big | 188 | +12.6% | **-1.4%** | -0.74 | 0.75 | -25% | -21% / 185 M | 9% | 50% |
| P2 Quality big | 188 | +15.1% | **+1.2%** | 1.15 | 0.96 | -25% | -9% / 86 M | 60% | 69% |
| P3 Small value | 188 | +10.2% | **-3.7%** | -0.73 | 0.50 | -47% | -52% / 185 M | 7% | 38% |
| P4 Small momentum | 188 | +12.4% | **-1.6%** | -0.17 | 0.61 | -34% | -35% / 150 M | 13% | 38% |
| P5 Multi-factor 3 | 188 | +12.9% | **-1.0%** | -0.92 | 0.78 | -25% | -17% / 185 M | 9% | 31% |
| P6 Multi-factor 4 | 188 | +12.8% | **-1.1%** | -0.57 | 0.74 | -26% | -20% / 185 M | 8% | 38% |
| P7 Factor momentum | 188 | +13.9% | **-0.0%** | 0.07 | 0.81 | -22% | -18% / 98 M | 36% | 50% |
| Market (benchmark, net 0.15 %) | 188 | +13.9% | — | — | — | — | — | — | — |

### B USA (robustness) — 2016→ (2016-01 → 2026-08)
| Portfolio | months | CAGR (net) | vs market p.a. | t | Sharpe | max DD | worst lag vs market / longest | 5-y windows won | years won |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| P1 Momentum big | 128 | +13.2% | **-1.7%** | -0.67 | 0.69 | -25% | -19% / 127 M | 2% | 55% |
| P2 Quality big | 128 | +16.5% | **+1.6%** | 1.23 | 0.93 | -25% | -8% / 30 M | 54% | 73% |
| P3 Small value | 128 | +11.4% | **-3.4%** | -0.39 | 0.50 | -47% | -51% / 116 M | 6% | 36% |
| P4 Small momentum | 128 | +12.8% | **-2.0%** | -0.21 | 0.57 | -34% | -30% / 66 M | 19% | 36% |
| P5 Multi-factor 3 | 128 | +14.1% | **-0.8%** | -0.47 | 0.75 | -25% | -14% / 99 M | 11% | 36% |
| P6 Multi-factor 4 | 128 | +13.8% | **-1.0%** | -0.36 | 0.71 | -26% | -17% / 96 M | 12% | 36% |
| P7 Factor momentum | 128 | +15.8% | **+0.9%** | 0.39 | 0.84 | -18% | -18% / 50 M | 44% | 55% |
| Market (benchmark, net 0.15 %) | 128 | +14.9% | — | — | — | — | — | — | — |

P7 factor momentum switched 3.5 legs per year on average.

## Blind selection (pre-registered)
Best in 1990–2010: **P4 Small momentum** (+6.7% p.a. vs market). Its out-of-sample 2011→ result: **-0.1% p.a.** (t 0.15), CAGR +10.7% vs market +10.7%.
Robust (beats market ≤2010 AND 2011→ AND in the US, after costs): P1 Momentum big (≤2010 +1.3%, 2011→ +0.2%, US +1.5%); P2 Quality big (≤2010 +0.6%, 2011→ +1.2%, US +0.8%); P7 Factor momentum (≤2010 +5.6%, 2011→ +0.5%, US +5.0%).

## C Reality check with real ETFs (fees included, adjusted closes)
### EUR listings (Xetra) vs iShares Core MSCI World
| ETF | from | CAGR | benchmark CAGR | difference p.a. | max DD | years won |
|---|---|--:|--:|--:|--:|--:|
| World Momentum (IS3R) | 2014-11 | +11.9% | +12.1% | **-0.2%** | -17% | 62% |
| World Quality (IS3Q) | 2014-11 | +9.9% | +12.1% | **-2.2%** | -17% | 54% |
| World Value (IS3S) | 2014-11 | +11.0% | +12.1% | **-1.1%** | -25% | 31% |
| World Small Cap (IUSN) | 2018-05 | +9.3% | +13.3% | **-4.0%** | -28% | 11% |
| US Small Cap Value (ZPRV) | 2015-03 | +10.0% | +11.0% | **-1.0%** | -37% | 33% |
| Nasdaq-100 (EQQQ, hindsight control) | 2009-02 | +20.4% | +12.6% | **+7.8%** | -30% | 83% |

Equal-weight ETF mix (World Momentum (IS3R), World Quality (IS3Q), US Small Cap Value (ZPRV)), monthly rebalanced, from 2015-03: CAGR +11.5% vs +11.0% → **+0.5% p.a.** (t 0.57), max DD -22%, years won 58%.

### USD listings vs iShares MSCI World
| ETF | from | CAGR | benchmark CAGR | difference p.a. | max DD | years won |
|---|---|--:|--:|--:|--:|--:|
| S&P 500 (SPY) | 2000-02 | +14.6% | +11.9% | **+2.7%** | -24% | 73% |
| US Momentum (MTUM) | 2013-05 | +15.0% | +11.3% | **+3.7%** | -30% | 64% |
| US Quality (QUAL) | 2013-08 | +13.5% | +11.2% | **+2.3%** | -28% | 79% |
| US Small Value (IJS) | 2000-08 | +10.6% | +11.9% | **-1.3%** | -40% | 40% |
| US Small Value (AVUV) | 2019-10 | +15.3% | +13.9% | **+1.4%** | -42% | 50% |

Equal-weight ETF mix (US Momentum (MTUM), US Quality (QUAL), US Small Value (IJS)), monthly rebalanced, from 2013-08: CAGR +12.9% vs +11.2% → **+1.6% p.a.** (t 1.23), max DD -25%, years won 86%.

Note: Nasdaq-100 is shown only as a hindsight control — choosing it today because it won is exactly the bias this test is built to avoid.