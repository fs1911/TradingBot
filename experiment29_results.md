# Experiment #29 — funding as a froth gauge (Finanzradar signal) [data: bybit] (2026-09-22 14:11 UTC)

Funding = how crowded leveraged longs are. Tests whether high funding predicts lower forward 30d returns (contrarian), and whether a 'step aside when hot' filter beats buy & hold. For Finanzradar, not a bot trade.

## Predictive: forward return by funding bucket
| Coin | low-funding fwd% | high-funding fwd% | contrarian? |
|---|--:|--:|:--:|
| BTC/USDT:USDT | +2.6 | +5.6 | ❌ no |
| ETH/USDT:USDT | +1.6 | +4.0 | ❌ no |
| SOL/USDT:USDT | -0.0 | +5.4 | ❌ no |
| XRP/USDT:USDT | -1.5 | +13.4 | ❌ no |
| DOGE/USDT:USDT | -3.8 | +0.8 | ❌ no |
| BNB/USDT:USDT | +9.4 | +6.0 | ✅ yes |

## Usable rule: 'step aside when funding hot' vs buy & hold
| Coin | B&H Sharpe | Filtered Sharpe | B&H ann% | Filtered ann% | better? |
|---|--:|--:|--:|--:|:--:|
| BTC/USDT:USDT | 0.65 | 0.47 | +26 | +17 | ❌ |
| ETH/USDT:USDT | 0.35 | 0.09 | +20 | +5 | ❌ |
| SOL/USDT:USDT | 0.38 | 0.32 | +25 | +20 | ❌ |
| XRP/USDT:USDT | 0.67 | 0.06 | +44 | +3 | ❌ |
| DOGE/USDT:USDT | 0.40 | 0.14 | +30 | +10 | ❌ |
| BNB/USDT:USDT | 0.73 | 0.67 | +32 | +27 | ❌ |

---
**Summary:** high funding is a contrarian froth signal in 1/6 coins; the 'step aside when hot' filter beats buy&hold (Sharpe) in 0/6. For Finanzradar: read annualised funding as a percentile — top quintile ≈ Überhitzt, middle ≈ Halten, negative/bottom ≈ Kaufen. This is a sentiment overlay, not a standalone forecast.