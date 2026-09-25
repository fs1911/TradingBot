# Experiment #33 — trend filter judged fairly (cash yield, dividends, robustness, savings plans) (2026-09-25 05:04 UTC)

Cash earns the 13-week US T-bill yield (^IRX, from 1970). For non-USD markets this is a proxy and flatters cash. Cells: CAGR / Sharpe / max drawdown. Rigor on (SMA200-with-cash − B&H).

## Timing rules vs buy & hold
| Asset | years | B&H | SMA200 daily | SMA200 monthly | SMA150 | SMA250 | rigor SMA200−B&H |
|---|--:|---|---|---|---|---|---|
| S&P 500 TR (mit Div.) | 39 | +11.4% / 0.70 / -55% | +9.9% / 0.86 / -21% | +10.4% / 0.86 / -24% | +8.6% / 0.77 / -31% | +9.7% / 0.83 / -24% | ❌ |
| S&P 500 (Preis) | 57 | +8.3% / 0.55 / -57% | +8.1% / 0.75 / -24% | +8.8% / 0.76 / -33% | +7.4% / 0.71 / -35% | +8.6% / 0.78 / -22% | ❌ |
| Nasdaq Comp. | 56 | +10.4% / 0.59 / -78% | +12.3% / 0.94 / -45% | +10.6% / 0.77 / -44% | +11.9% / 0.94 / -57% | +12.3% / 0.92 / -36% | ❌ |
| Dow Jones | 35 | +8.5% / 0.56 / -54% | +4.9% / 0.49 / -42% | +6.8% / 0.62 / -31% | +3.1% / 0.34 / -46% | +5.2% / 0.50 / -37% | ❌ |
| Russell 2000 | 39 | +8.1% / 0.47 / -60% | +5.8% / 0.49 / -41% | +5.8% / 0.46 / -41% | +5.5% / 0.46 / -36% | +5.9% / 0.49 / -42% | ❌ |
| DAX (TR) | 39 | +8.0% / 0.47 / -73% | +8.0% / 0.62 / -35% | +8.4% / 0.62 / -30% | +6.6% / 0.53 / -36% | +8.0% / 0.61 / -45% | ❌ |
| SMI | 36 | +6.3% / 0.44 / -56% | +5.7% / 0.57 / -40% | +6.7% / 0.64 / -32% | +5.9% / 0.60 / -30% | +5.2% / 0.51 / -38% | ❌ |
| Nikkei 225 | 55 | +6.6% / 0.41 / -82% | +7.6% / 0.62 / -31% | +7.4% / 0.58 / -38% | +7.5% / 0.62 / -36% | +7.2% / 0.59 / -38% | ❌ |

## Savings plans (monthly contribution 1) — final multiple / max drawdown
| Asset | plain DCA | trend-DCA light | trend-DCA full |
|---|---|---|---|
| S&P 500 TR (mit Div.) | 13.11× / -59% | 13.12× / -58% | 10.44× / -24% |
| S&P 500 (Preis) | 25.74× / -61% | 26.56× / -61% | 25.33× / -27% |
| Nasdaq Comp. | 68.69× / -77% | 72.15× / -77% | 52.62× / -41% |
| Dow Jones | 4.75× / -55% | 4.74× / -54% | 3.37× / -37% |
| Russell 2000 | 5.95× / -56% | 5.86× / -56% | 3.23× / -39% |
| DAX (TR) | 5.87× / -72% | 5.84× / -71% | 6.27× / -29% |
| SMI | 2.41× / -63% | 2.42× / -61% | 2.55× / -43% |
| Nikkei 225 | 6.37× / -86% | 6.37× / -86% | 9.68× / -51% |

---
**Summary timing (with cash yield):** SMA200 beat B&H on CAGR in 2/8, on Sharpe in 7/8, on max drawdown in 8/8; all four variants beat B&H Sharpe in 6/8; full rigor pass 0/8.
**Summary savings plans:** trend-DCA light beat plain DCA in 4/8; trend-DCA full beat plain DCA in 3/8 and had a smaller max drawdown in 8/8.