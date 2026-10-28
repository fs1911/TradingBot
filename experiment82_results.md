# Experiment #82 — fat tails and the 'best days' claim (2026-10-28 13:02 UTC)

## S&P 500 — 1928-01-03 → 2026-10-27, 24,822 days, price only

### A How often do extreme days happen?
| move beyond | observed (whole-sample σ) | observed (trailing 1-y σ) | expected if normal | normal says: once every … years |
|---|--:|--:|--:|--:|
| 3 σ | 411 | 384 | 67.01 | 1 |
| 4 σ | 193 | 130 | 1.57 | 63 |
| 5 σ | 103 | 61 | 0.01 | 6,922 |
| 7 σ | 37 | 17 | 0.00 | > 10 million |
| 10 σ | 6 | 3 | 0.00 | > 10 million |

### B Biggest days
Best: 1933-03-15 +16.6 %, 1929-10-30 +12.5 %, 1931-10-06 +12.4 %, 1939-09-05 +11.9 %, 1932-09-21 +11.8 %
Worst: 1987-10-19 -20.5 %, 1929-10-28 -12.9 %, 2020-03-16 -12.0 %, 1929-10-29 -10.2 %, 1935-04-16 -10.0 %
Of the 10 best days, **3** were within ±10 trading days of one of the 10 worst days.

### C 'Missing the best days'
| days removed | skip N best | skip N worst | skip both | out on N RANDOM days (median, 5–95 %) |
|---|--:|--:|--:|--:|
| none | +6.37 % | — | — | — |
| 5 | +5.71 % | +7.14 % | +6.47 % | +6.37 % (+6.33 … +6.41) |
| 10 | +5.18 % | +7.68 % | +6.48 % | +6.37 % (+6.30 … +6.44) |
| 20 | +4.25 % | +8.67 % | +6.51 % | +6.37 % (+6.28 … +6.46) |
| 50 | +2.08 % | +11.04 % | +6.57 % | +6.37 % (+6.23 … +6.51) |

## Bitcoin — 2014-09-18 → 2026-10-28, 4,424 days, price only

### A How often do extreme days happen?
| move beyond | observed (whole-sample σ) | observed (trailing 1-y σ) | expected if normal | normal says: once every … years |
|---|--:|--:|--:|--:|
| 3 σ | 81 | 87 | 11.94 | 1 |
| 4 σ | 26 | 32 | 0.28 | 63 |
| 5 σ | 11 | 10 | 0.00 | 6,922 |
| 7 σ | 2 | 2 | 0.00 | > 10 million |
| 10 σ | 1 | 1 | 0.00 | > 10 million |

### B Biggest days
Best: 2017-12-07 +25.2 %, 2017-07-20 +23.9 %, 2017-12-06 +19.9 %, 2021-02-08 +18.7 %, 2020-03-19 +18.2 %
Worst: 2020-03-12 -37.2 %, 2015-01-14 -21.1 %, 2017-09-14 -18.7 %, 2015-08-18 -18.2 %, 2018-01-16 -16.9 %
Of the 10 best days, **3** were within ±10 trading days of one of the 10 worst days.

### C 'Missing the best days'
| days removed | skip N best | skip N worst | skip both | out on N RANDOM days (median, 5–95 %) |
|---|--:|--:|--:|--:|
| none | +34.26 % | — | — | — |
| 5 | +27.15 % | +44.60 % | +36.94 % | +34.22 % (+33.30 … +35.10) |
| 10 | +21.82 % | +51.76 % | +37.70 % | +34.23 % (+32.77 … +35.73) |
| 20 | +13.35 % | +64.94 % | +39.28 % | +34.25 % (+32.39 … +36.38) |
| 50 | -5.37 % | +100.60 % | +41.47 % | +34.46 % (+31.57 … +37.59) |

Reading: extreme days are far more frequent than a normal distribution predicts — risk models, stop losses and leverage built on 'normal' volatility underestimate crashes. The best and worst days cluster in the same crises, so 'missing the best days' alone is an unrealistic scenario; a timer who is out on random days loses very little, a timer who is out in crises misses both.