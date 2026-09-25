# Experiment #38 — volatility premium + trend insurance combined (2026-09-25 06:54 UTC)

Daily, 1997-05-21 → 2026-09-24 (7376 days). Cash = 13-week T-bill (^IRX); 5 bps per trend switch; 50/50 rebalanced daily.

## Overall
| Strategy | CAGR | vol | Sharpe | max DD | monthly skew | worst month |
|---|--:|--:|--:|--:|--:|---|
| S&P 500 TR | +9.8% | 19.2% | 0.58 | -55% | -0.55 | -17% (2008-10) |
| PutWrite | +8.3% | 15.4% | 0.60 | -37% | -1.68 | -18% (2008-10) |
| PutWrite + trend (daily) | +7.0% | 7.2% | 0.98 | -16% | -0.59 | -9% (2010-05) |
| PutWrite + trend (monthly) | +7.8% | 8.3% | 0.94 | -18% | -1.25 | -10% (1998-08) |
| S&P 500 TR + trend | +8.2% | 12.1% | 0.72 | -21% | -0.23 | -11% (2010-05) |
| 50/50 PutWrite + S&P | +9.2% | 16.4% | 0.62 | -46% | -0.97 | -17% (2008-10) |
| 50/50 PutWrite + trend-S&P | +8.6% | 11.5% | 0.77 | -24% | -0.63 | -10% (2010-05) |

## Crises (total return over the window)
| Strategy | 2000–02 dot-com | 2008–09 GFC | 2020 Covid | 2022 bear |
|---|--:|--:|--:|--:|
| S&P 500 TR | -47% | -55% | -33% | -24% |
| PutWrite | -22% | -35% | -29% | -14% |
| PutWrite + trend (daily) | +5% | -1% | -15% | -4% |
| PutWrite + trend (monthly) | +13% | +3% | -10% | -5% |
| S&P 500 TR + trend | -14% | -9% | -17% | -12% |
| 50/50 PutWrite + S&P | -36% | -45% | -30% | -19% |
| 50/50 PutWrite + trend-S&P | -18% | -22% | -21% | -13% |

## Rigor on the key differentials (daily, α/150)
| Differential | OOS ret% | Sharpe | p | sig | walk-fwd | regimes+ | verdict |
|---|--:|--:|--:|:--:|--:|:--:|---|
| PutWrite + trend (daily) − PutWrite | -37 | -0.15 | 0.8965 | ❌ | 8% | 0/3 | ❌ |
| PutWrite + trend (daily) − S&P 500 TR | -73 | -0.25 | 0.95 | ❌ | 13% | 0/3 | ❌ |
| 50/50 PutWrite + trend-S&P − S&P 500 TR | -53 | -0.21 | 0.915 | ❌ | 11% | 0/3 | ❌ |
| 50/50 PutWrite + trend-S&P − 50/50 PutWrite + S&P | -25 | -0.17 | 0.871 | ❌ | 9% | 0/3 | ❌ |

---
**Summary:** best Sharpe: PutWrite + trend (daily) (0.98, CAGR +7.0%, max DD -16%) vs S&P 500 TR (0.58, +9.8%, -55%). Differentials passing full rigor: 0/4.