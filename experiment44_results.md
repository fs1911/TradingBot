# Experiment #44 — backtest of the exact live trend-portfolio rule (2026-09-30 12:44 UTC)

Assets with data: 23/23 (missing: —). Cash = BIL ok.
Evaluated 1994-03-05 → 2026-09-29; monthly rebalance; costs 5 bps ETF / 25 bps crypto per unit turnover; cash = BIL.

| Portfolio | CAGR | vol | Sharpe (excess) | max DD | worst year | Sharpe ≤2012 | Sharpe >2012 | avg invested | turnover/yr |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Live rule (ETFs + BTC/ETH) | +5.4% | 6.1% | 0.75 | -17% | -4% (2023) | 0.97 | 0.54 | 72% | 399% |
| Live rule without crypto | +5.0% | 6.0% | 0.70 | -18% | -6% (2023) | 0.97 | 0.42 | 72% | 399% |
| EW buy & hold (ETFs, daily rebal.) | +7.0% | 12.3% | 0.55 | -38% | -13% (2002) | 0.69 | 0.25 | 100% | — |
| SPY buy & hold | +10.9% | 18.8% | 0.60 | -55% | -37% (2008) | 0.47 | 0.82 | 100% | 0% |
| 60/40 SPY/IEF | +8.6% | 10.8% | 0.72 | -31% | -17% (2008) | 0.63 | 0.80 | 100% | — |

### Crises (total return)
| Crisis | Live rule (ETFs + BTC/ETH) | Live rule without crypto | EW buy & hold (ETFs, daily rebal.) | SPY buy & hold | 60/40 SPY/IEF |
|---|--:|--:|--:|--:|--:|
| 2008–09 GFC | +9% | +9% | -20% | -55% | -31% |
| 2020 Covid | -5% | -5% | -17% | -33% | -19% |
| 2022 bear | -0% | +1% | -9% | -24% | -21% |

### Sensitivity of the live rule (Sharpe excess / max DD / CAGR)
| variant | Sharpe | max DD | CAGR |
|---|--:|--:|--:|
| target vol 8% | 0.78 | -13% | +5.2% |
| target vol 15% | 0.71 | -21% | +5.5% |
| crypto cap 5% | 0.74 | -17% | +5.3% |
| crypto cap 20% | 0.75 | -17% | +5.4% |
| 12-month signal only | 0.62 | -21% | +4.2% |

**Summary:** live rule CAGR +5.4% vs SPY +10.9%, max DD -17% vs -55%, Sharpe 0.75 vs 0.60; since 2013 0.54 vs 0.82.