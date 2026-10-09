# Experiment #49 — quality score for single stocks (SEC fundamentals) (2026-10-09 04:34 UTC)

SEC frames years: 17; failed requests: 11 (e.g. RevenueFromContractWithCustomerExcludingAssessedTax CY2009: <HTTPError 404: 'Not Found'>); ticker map: 8,017 CIKs.
Universe (Assets ≥ $1bn, scored, mapped to a current ticker): 458–1956 companies per year; with Yahoo prices: 2,436 tickers.
Portfolios 2010-07 → 2026-10 (196 months), annual rebalance end of June.

### A — Quintiles (Q5 = highest quality), equal-weight
| Portfolio | CAGR | vol | max DD | Sharpe (raw) | vs universe p.a. (t) |
|---|--:|--:|--:|--:|--:|
| Q1 | +12.3% | 19.7% | -37% | 0.69 | -0.7% (-0.43) |
| Q2 | +12.8% | 18.7% | -32% | 0.74 | -0.5% (-0.73) |
| Q3 | +13.7% | 18.1% | -32% | 0.80 | +0.2% (0.29) |
| Q4 | +14.0% | 18.3% | -33% | 0.81 | +0.5% (0.61) |
| Q5 | +14.2% | 17.2% | -31% | 0.86 | +0.5% (0.42) |
| universe | +13.5% | 17.9% | -33% | 0.80 | — (nan) |
| SPY | +15.1% | 14.1% | -24% | 1.07 | +0.8% (0.40) |

### B — Significance
- Q5 − Q1 (long-short, descriptive): +1.2% p.a., t=0.46
- **Q5 − universe (long-only, what you can buy): +0.5% p.a., t=0.42, one-sided p=0.3384 ❌ (α/230)**; placebo (random scores, 200 runs): p=0.140
- Q5 − universe ≤2015: +0.9% (t 0.59); >2015: +0.3% (t 0.17)
- Hit rate: Q5 beat the universe in 53% of months; in 9/17 calendar years

### C — Single components (Q5 − universe of a 1-component sort, p.a. (t))
- gross_profitability: -0.2% (-0.19)
- roe: +1.5% (1.42)
- low_accruals: +1.9% (1.44)
- low_leverage: -1.5% (-1.21)

### D — Crises and combination with the market regime (#47: S&P trend + macro stress)
| Portfolio | CAGR | max DD | Sharpe | 2011 | 2015–16 | 2018 Q4 | 2020 | 2022 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Q5 quality | +14.2% | -31% | 0.86 | -16% | -8% | -17% | -28% | -25% |
| Universe | +13.5% | -33% | 0.80 | -23% | -11% | -17% | -30% | -22% |
| SPY | +15.1% | -24% | 1.07 | -16% | -7% | -14% | -19% | -24% |
| Q5 + market regime | +11.2% | -32% | 0.77 | -16% | -8% | -17% | -22% | -25% |
| Universe + market regime | +10.9% | -31% | 0.73 | -23% | -11% | -17% | -23% | -22% |

**Summary:** Q5 − universe +0.5% p.a. (t 0.42, placebo p 0.140); Q5 − Q1 +1.2% (t 0.46). Survivorship (current tickers only) biases against the low-quality quintile's true losses.