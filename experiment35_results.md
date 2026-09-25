# Experiment #35 — trend filter: real edge or averaging artefact? (2026-09-25 06:09 UTC)

Months: 1149 (1928-01 → 2023-09). Daily closes from 1927-12-30. Real returns, Shiller dividends, 10y-bond proxy; 10-month SMA signal, lagged one month.

## The artefact, measured
| Price series | lag-1 autocorrelation of monthly returns |
|---|--:|
| A: monthly averages (Shiller) | +0.265 |
| B: true month-end closes | +0.082 |

## Head to head (real)
| Series / rule | real CAGR | Sharpe | max DD | p vs own B&H | sig after haircut | both halves |
|---|--:|--:|--:|--:|:--:|:--:|
| A · 100% stocks (averages) | +6.66% | 0.49 | -77% | — | — | — |
| A · trend filter (averages) | +8.58% | 0.80 | -44% | 0.146 | ❌ | ✅ |
| B · 100% stocks (month-end) | +6.59% | 0.44 | -79% | — | — | — |
| B · trend filter (month-end, bonds) | +7.24% | 0.61 | -56% | 0.559 | ❌ | ❌ |
| B · trend filter (month-end, 0% cash) | +4.82% | 0.45 | -57% | 0.971 | ❌ | ❌ |

## Month-end version by era (trend − 100% stocks)
| Era | months | excess %/y | stocks max DD | trend max DD |
|---|--:|--:|--:|--:|
| 1928–1949 | 264 | -2.78 | -79% | -56% |
| 1950–1989 | 480 | +0.56 | -52% | -33% |
| 1990–end | 405 | +0.33 | -54% | -23% |

---
**Summary:** autocorrelation +0.27 (averages) vs +0.08 (month-end). Trend-filter CAGR advantage +1.92 pp with averages vs +0.65 pp with true month-end closes — 34% of the #34 edge survives. Month-end version: p=0.559, significant after haircut: no, positive in both halves: no, positive in 2/3 eras.