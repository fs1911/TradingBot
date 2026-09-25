# Experiment #34 — Shiller CAPE over ~150 years (2026-09-25 05:47 UTC)

Source: https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv. Months with price/CPI: 1868, with CAPE: 1713 (1881-01 → 2023-09). All returns REAL (after inflation), dividends reinvested.

## 1 — Does high CAPE predict lower real returns?
| Horizon | cheapest-quintile fwd | dearest-quintile fwd | corr (non-overl.) | t | n | corr pre-1950 / post-1950 |
|---|--:|--:|--:|--:|--:|---|
| 1y | +15.5%/y | +4.5%/y | -0.19 | -2.33 | 142 | -0.29 / -0.21 |
| 3y | +12.4%/y | +3.4%/y | -0.29 | -2.01 | 47 | -0.52 / -0.25 |
| 10y | +10.9%/y | +3.0%/y | -0.48 | -1.89 | 14 | -0.58 / -0.68 |

## 2 — Does the 10-month trend filter help more when CAPE is high?
| CAPE regime (causal, top third vs rest) | months | trend − stocks, %/y | t |
|---|--:|--:|--:|
| CAPE high (top third) | 766 | +1.14 | +1.13 |
| CAPE normal/low | 826 | +1.91 | +1.25 |

## 3 — Allocation rules (real, from 1891-02)
| Rule | real CAGR | Sharpe | max DD | vs 100% stocks: p | sig after haircut | better in both halves |
|---|--:|--:|--:|--:|:--:|:--:|
| 100% stocks | +6.65% | 0.51 | -77% | — | — | — |
| 60/40 stocks/bonds | +4.90% | 0.56 | -50% | 1.000 | ❌ | ❌ |
| CAPE-scaled (30–100% stocks) | +5.01% | 0.50 | -55% | 0.998 | ❌ | ❌ |
| Trend filter (10m SMA) | +8.81% | 0.84 | -44% | 0.059 | ❌ | ✅ |
| CAPE-gated trend (filter only if CAPE top third) | +7.37% | 0.59 | -74% | 0.145 | ❌ | ✅ |

---
**Summary:** 10y: corr -0.48 (t -1.9), pre/post-1950 -0.58/-0.68. 1y: corr -0.19 (t -2.3). Trend filter excess when CAPE high +1.14%/y vs otherwise +1.91%/y. Allocation rules significant vs 100% stocks after haircut: 0/4; positive in both halves: 2/4.