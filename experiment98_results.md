# Experiment #98 — bitcoin lead, weekly, new stocks (2026-11-20 08:56 UTC)

15 symbols loaded, missing: none; first week per stock: IREN 2021-11, CIFR 2020-10, WULF 2014-01, BTBT 2018-03, HIVE 2014-01, BTDR 2021-07, MARA 2014-01, RIOT 2016-03, COIN 2021-04, CLSK 2016-11, HUT 2018-03, MSTR 2014-01

## 1 Primary: slope of the stock's NEXT-week return on the leader's PAST-week return (vs SPY, own week controlled)
| test | stock-weeks | weeks | slope | t (clustered by week) | placebo p (shifted leader) | Holm p | ≤ 2023 slope (t) | 2024 → slope (t) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| A bitcoin → new stocks, next week | 2,451 | 634 | +0.008 | +0.19 | +0.251 | +0.503 | +0.036 (+0.79) | -0.092 (-0.79) |
| A bitcoin → new stocks, skip Monday | 2,452 | 634 | +0.046 | +1.25 | +0.078 | +0.234 | +0.056 (+1.51) | +0.004 (+0.04) |
| B ethereum → new stocks, next week | 2,127 | 470 | +0.008 | +0.19 | +0.335 | +0.503 | -0.002 (-0.05) | +0.034 (+0.38) |
| C bitcoin → #94/#95 stocks, next week (descriptive) | 2,457 | 463 | +0.090 | +0.95 | +0.040 | — | +0.139 (+1.23) | -0.118 (-1.03) |
| C bitcoin → #94/#95 stocks, skip Monday (descriptive) | 2,457 | 463 | +0.129 | +1.58 | +0.008 | — | +0.160 (+1.65) | -0.004 (-0.04) |

## 2 Per stock (bitcoin, next week): mean next-week return vs SPY after signal (bitcoin beat SPY, stock lagged) vs otherwise
| stock | weeks | after signal | otherwise | difference (t) |
|---|--:|--:|--:|--:|
| IREN (A) | 260 | -0.79 % | +1.57 % | -2.36 % (-1.15) |
| CIFR (A) | 316 | +1.19 % | +0.44 % | +0.75 % (+0.43) |
| WULF (A) | 634 | +0.97 % | +0.12 % | +0.84 % (+0.89) |
| BTBT (A) | 335 | +0.65 % | -0.04 % | +0.69 % (+0.33) |
| HIVE (A) | 630 | +0.52 % | +0.47 % | +0.05 % (+0.04) |
| BTDR (A) | 276 | -0.10 % | +0.60 % | -0.71 % (-0.42) |
| MARA (C) | 463 | +0.82 % | +1.06 % | -0.24 % (-0.11) |
| RIOT (C) | 463 | -0.41 % | +1.29 % | -1.70 % (-1.10) |
| COIN (C) | 291 | +1.99 % | -0.64 % | +2.63 % (+1.66) |
| CLSK (C) | 463 | +1.56 % | +0.53 % | +1.03 % (+0.60) |
| HUT (C) | 453 | +1.21 % | +1.18 % | +0.03 % (+0.02) |
| MSTR (C) | 324 | +0.25 % | +1.34 % | -1.09 % (-0.66) |

## 3 Rule: hold the group-A basket next week after bitcoin beat SPY and the basket lagged, else cash
| portfolio | weeks invested | CAGR | max drawdown | Sharpe |
|---|--:|--:|--:|--:|
| rule, bitcoin gross | 238 of 630 | +3.77 % | -61 % | +0.29 |
| rule, bitcoin net 0.10 %/side | 238 of 630 | +1.31 % | -63 % | +0.23 |
| rule, bitcoin net Yuh 1.45 %/side | 238 of 630 | -26.87 % | -98 % | -0.52 |
| rule, ethereum gross | 159 of 470 | +5.67 % | -65 % | +0.33 |
| rule, ethereum net 0.10 %/side | 159 of 470 | +3.17 % | -68 % | +0.28 |
| rule, ethereum net Yuh 1.45 %/side | 159 of 470 | -25.48 % | -93 % | -0.45 |
| group-A basket always (no costs) | 670 | +12.32 % | -88 % | +0.50 |
| SPY (same weeks) | 670 | +12.93 % | -32 % | +0.83 |

Reading: group A is the real test (stocks never looked at before). If its slope is not clearly positive, the #94/#95 hint was most likely chance. Group C only shows the old stocks at weekly frequency.
Caveats: young stocks (mostly 2021 →), very volatile; current tickers only (failed miners missing); bitcoin closes ≈ 3 h after US stocks even after alignment (the skip-Monday test removes that).