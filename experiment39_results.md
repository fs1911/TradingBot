# Experiment #39 — PutWrite + trend: really better, or only less risky? (2026-09-25 07:10 UTC)

Daily 1997-08-01 → 2026-09-24. Sharpe = excess over 13-week T-bill. Bootstrap: paired 20-day blocks, 5000 draws; haircut p < 0.00032.

## 1 — Sharpe-difference test (PutWrite + trend vs …)
| vs | Sharpe strat | Sharpe other | difference | 95% CI | p (one-sided) | sig after haircut |
|---|--:|--:|--:|---|--:|:--:|
| S&P 500 TR | 0.66 | 0.45 | +0.21 | [-0.12, +0.51] | 0.0902 | ❌ |
| PutWrite | 0.66 | 0.44 | +0.21 | [-0.14, +0.51] | 0.0806 | ❌ |
| S&P 500 TR + trend | 0.66 | 0.51 | +0.15 | [-0.05, +0.32] | 0.0438 | ❌ |

## 2 — Equal risk: levered strategy (financing T-bill + 1%/y) vs S&P 500 TR
| Portfolio | leverage | CAGR | vol | max DD |
|---|--:|--:|--:|--:|
| S&P 500 TR | 1.0× | +9.4% | 19.2% | -55% |
| PutWrite + trend | 1.00× | +6.9% | 7.2% | -16% |
| PutWrite + trend | 1.50× | +8.5% | 10.9% | -23% |
| PutWrite + trend | 2.00× | +10.1% | 14.5% | -31% |
| PutWrite + trend | 2.66× (= S&P vol) | +11.9% | 19.2% | -41% |

## 3 — Robustness: Sharpe (excess) strategy vs S&P 500 TR
| start | SMA150 d | SMA150 m | SMA200 d | SMA200 m | SMA250 d | SMA250 m | S&P |
|---|--:|--:|--:|--:|--:|--:|--:|
| 1997 | 0.51 | 0.73 | 0.63 | 0.64 | 0.59 | 0.61 | 0.46 |
| 2002 | 0.55 | 0.77 | 0.64 | 0.64 | 0.58 | 0.61 | 0.51 |
| 2007 | 0.54 | 0.73 | 0.64 | 0.57 | 0.55 | 0.52 | 0.56 |
| 2012 | 0.64 | 0.76 | 0.79 | 0.66 | 0.75 | 0.70 | 0.84 |

---
**Summary:** Sharpe difference significant after haircut in 0/3 comparisons. At equal volatility (2.66× leverage, financed at T-bill+1%) the strategy returns +11.9% vs +9.4% for the S&P with max DD -41% vs -55% → beats the S&P at equal risk. Robustness: strategy Sharpe > S&P in 15/24 parameter × start-year cells.