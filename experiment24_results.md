# Experiment #24 — crypto funding-rate carry [data: bybit] (2026-09-22 08:56 UTC)

Delta-neutral (long spot / short perp) carry from perpetual funding. Daily carry through the full rigor battery; cost scenarios (annual drag for hedge maintenance): 0%, 2%, 5%. Haircut α/78.

> ⚠️ A ✅ here means the carry was persistently positive IN-SAMPLE — NOT risk-free. The battery cannot see exchange/counterparty risk, short-leg liquidation, or funding-regime flips in a bear market. Also NOT tradeable on Alpaca (no perps) — research only.

## Per-coin carry
| Coin | days | funding<0 % | total carry% | maxDD% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|--:|:--:|---|
| BTC/USDT:USDT | 67 | — | — | — | — | — | — | no/short data |
| ETH/USDT:USDT | 67 | — | — | — | — | — | — | no/short data |
| SOL/USDT:USDT | 67 | — | — | — | — | — | — | no/short data |
| XRP/USDT:USDT | 67 | — | — | — | — | — | — | no/short data |
| DOGE/USDT:USDT | 67 | — | — | — | — | — | — | no/short data |

---
**Summary:** 0 coins with usable funding history. Basket configs surviving rigor: 0/0. Remember: surviving rigor here = persistent positive carry in-sample, not a risk-free edge, and not executable on Alpaca. If it survives, the honest next step is a small-scale, real-cost feasibility study on a derivatives venue.