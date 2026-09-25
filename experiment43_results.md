# Experiment #43 — Buffett factors: value, quality, low volatility (2026-09-25 12:00 UTC)

French files loaded: 10/10 (ff5, mom, var, beta, op, bm, eu5, eumom, dx5, dxmom). Project trial count for haircut: 190.

## Part A — Kenneth French data (survivorship-free)

US data 1963-07 → 2026-07. Market excess: mean 7.2% p.a., Sharpe 0.47. Bonferroni α/190 = 0.00026 (two-sided t).

### A1 — Long-short factors (US)
| Factor | mean p.a. | t | p | sig | Sharpe | CAPM α p.a. (t) | pub. | mean before | mean after | Sharpe after | 2010+ mean (t) |
|---|--:|--:|--:|:--:|--:|--:|--:|--:|--:|--:|--:|
| SMB (size) | +2.2% | 1.71 | 0.0881 | ❌ | 0.21 | +0.9% (0.7) | 1981 | +6.6% | +0.4% | 0.04 | -0.8% (-0.4) |
| HML (value) | +3.6% | 2.77 | 0.0056 | ❌ | 0.35 | +4.6% (3.6) | 1992 | +5.1% | +2.3% | 0.20 | -0.4% (-0.1) |
| RMW (quality/profitability) | +3.1% | 3.10 | 0.0019 | ❌ | 0.39 | +3.8% (3.8) | 2013 | +3.2% | +2.6% | 0.30 | +2.2% (1.1) |
| CMA (investment) | +3.0% | 3.27 | 0.0011 | ❌ | 0.41 | +4.2% (4.9) | 2015 | +3.5% | +0.1% | 0.01 | +0.4% (0.2) |
| UMD (momentum) | +7.4% | 4.55 | 0.0000 | ✅ | 0.46 | +8.4% (4.6) | 1993 | +8.8% | +4.5% | 0.27 | +3.3% (1.1) |
| Low-var − high-var quintile | +1.6% | 0.54 | 0.5905 | ❌ | 0.07 | +8.1% (3.5) | 2006 | +2.5% | -0.6% | -0.02 | -2.0% (-0.3) |
| Low-beta − high-beta quintile | -3.3% | -1.27 | 0.2039 | ❌ | -0.16 | +2.8% (1.4) | 1972 | -4.5% | -3.0% | -0.14 | -8.0% (-1.4) |

### A2 — Long-only tilts a private investor can buy (value-weighted US quintiles)
| Portfolio | CAGR | vol | excess Sharpe | max DD | CAPM α p.a. (t) | β | ΔSharpe vs market [95% CI] | p | sig | 2010+ ΔSharpe |
|---|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|
| Market | 10.9% | 15.4% | 0.47 | -50% | — | 1.00 | — | — | | — |
| Low variance quintile | 11.3% | 12.1% | 0.58 | -42% | +2.1% (2.9) | 0.70 | +0.12 [-0.01, +0.23] | 0.0213 | ❌ | +0.17 |
| Low beta quintile | 10.5% | 12.1% | 0.53 | -43% | +1.6% (2.0) | 0.66 | +0.06 [-0.07, +0.20] | 0.1890 | ❌ | +0.02 |
| High profitability quintile | 12.0% | 15.4% | 0.53 | -50% | +1.3% (2.5) | 0.97 | +0.07 [-0.01, +0.15] | 0.0420 | ❌ | +0.06 |
| High book/market (value) quintile | 13.6% | 27.6% | 0.59 | -88% | +3.6% (2.9) | 1.05 | +0.13 [-0.05, +0.29] | 0.0613 | ❌ | -0.21 |
| Buffett mix (low-var + profitable + value, 1/3 each) | 12.4% | 25.8% | 0.61 | -88% | +2.3% (4.8) | 0.90 | +0.15 [+0.05, +0.23] | 0.0027 | ❌ | +0.03 |
| Low variance levered to market vol (≤2.5×, T-bill+1%) | 12.7% | 15.2% | 0.58 | -51% | +2.5% (2.8) | 0.87 | +0.11 [-0.00, +0.22] | 0.0240 | ❌ | +0.18 |

### A3 — International replication (long-short factors)
| Region | Factor | mean p.a. | t | Sharpe | 2010+ mean (t) |
|---|---|--:|--:|--:|--:|
| Europe (1990-07→) | SMB | +0.1% | 0.12 | 0.02 | +0.5% (0.3) |
| Europe (1990-07→) | HML | +4.2% | 2.83 | 0.47 | +1.5% (0.6) |
| Europe (1990-07→) | RMW | +3.6% | 3.89 | 0.65 | +2.4% (1.8) |
| Europe (1990-07→) | CMA | +1.7% | 1.66 | 0.28 | -0.2% (-0.2) |
| Europe (1990-11→) | UMD | +10.3% | 4.68 | 0.78 | +10.2% (3.9) |
| Developed ex-US (1990-07→) | SMB | +0.5% | 0.43 | 0.07 | -0.0% (-0.0) |
| Developed ex-US (1990-07→) | HML | +5.0% | 3.72 | 0.62 | +3.3% (1.6) |
| Developed ex-US (1990-07→) | RMW | +3.2% | 4.07 | 0.68 | +2.0% (1.9) |
| Developed ex-US (1990-07→) | CMA | +2.0% | 1.98 | 0.33 | +1.1% (1.0) |
| Developed ex-US (1990-11→) | UMD | +7.9% | 4.03 | 0.67 | +8.5% (3.7) |

**Part A summary:** US long-short factors significant after haircut: 1; long-only tilts with significant Sharpe gain vs market: 0; international factors with t > 2: 6/10.

## Part B — own single-stock test (Yahoo, today's large caps → survivorship-biased)

| Region | Score | months | low-quintile CAGR | EW universe CAGR | low β | ΔSharpe low vs EW [95% CI] | placebo p | BAB mean p.a. (t) | sig |
|---|---|--:|--:|--:|--:|--:|--:|--:|:--:|
| USA (92 Large Caps) (1991-01→) | low volatility | 429 | 13.0% | 19.9% | 0.66 | -0.16 [-0.43, +0.10] | 0.93 | -2.9% (-0.7) | ❌ |
| USA (92 Large Caps) (1991-01→) | low beta | 429 | 13.7% | 19.9% | 0.54 | -0.17 [-0.44, +0.10] | 0.94 | +8.4% (1.7) | ❌ |
| USA (92 Large Caps) (1991-01→) | low MAX (no lottery) | 429 | 16.1% | 19.9% | 0.77 | -0.02 [-0.19, +0.21] | 0.28 | -1.8% (-0.6) | ❌ |
| Schweiz (SMI) (1996-08→) | low volatility | 362 | 13.5% | 13.9% | 0.67 | +0.08 [-0.29, +0.42] | 0.01 | -1.5% (-0.3) | ❌ |
| Schweiz (SMI) (1996-08→) | low beta | 362 | 14.1% | 13.9% | 0.50 | +0.01 [-0.20, +0.28] | 0.08 | +26.7% (3.6) | ❌ |
| Schweiz (SMI) (1996-08→) | low MAX (no lottery) | 362 | 14.1% | 13.9% | 0.74 | +0.02 [-0.25, +0.29] | 0.06 | -3.4% (-0.5) | ❌ |
| Deutschland (DAX) (1997-12→) | low volatility | 346 | 10.8% | 11.1% | 0.62 | -0.00 [-0.21, +0.19] | 0.20 | +4.4% (0.8) | ❌ |
| Deutschland (DAX) (1997-12→) | low beta | 346 | 12.1% | 11.1% | 0.49 | +0.02 [-0.22, +0.28] | 0.08 | +7.7% (0.9) | ❌ |
| Deutschland (DAX) (1997-12→) | low MAX (no lottery) | 346 | 7.9% | 11.1% | 0.73 | -0.12 [-0.34, +0.10] | 0.77 | +0.4% (0.1) | ❌ |

**Part B summary:** 0 region/score cells with a Sharpe gain that beats the random-quintile placebo and has a CI above zero. Placebo p floor = 1/100.
