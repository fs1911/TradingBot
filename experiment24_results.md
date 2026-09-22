# Experiment #24 — crypto funding-rate carry [data: bybit] (2026-09-22 09:09 UTC)

Delta-neutral (long spot / short perp) carry from perpetual funding. Daily carry through the full rigor battery; cost scenarios (annual drag for hedge maintenance): 0%, 2%, 5%. Haircut α/78.

> ⚠️ A ✅ here means the carry was persistently positive IN-SAMPLE — NOT risk-free. The battery cannot see exchange/counterparty risk, short-leg liquidation, or funding-regime flips in a bear market. Also NOT tradeable on Alpaca (no perps) — research only.

## Per-coin carry
| Coin | days | funding<0 % | total carry% | maxDD% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|--:|:--:|---|
| BTC/USDT:USDT | 1401 | 16.7 | 31.8 | -0.6 | 6.9 | 0.0 | y | ✅ |
| ETH/USDT:USDT | 1401 | 18.7 | 31.9 | -0.4 | 7.0 | 0.0 | y | ✅ |
| SOL/USDT:USDT | 1380 | 27.1 | 20.4 | -5.6 | 1.18 | 0.111 | n | ❌ |
| XRP/USDT:USDT | 1401 | 19.8 | 38.1 | -0.6 | 6.23 | 0.0 | y | ⚠️ |
| DOGE/USDT:USDT | 1401 | 17.1 | 41.0 | -0.6 | 6.23 | 0.0 | y | ✅ |

## Diversified basket (equal-weight across coins), cost sweep
| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| basket carry @ 0%/yr | +10 | 9.25 | 21.8 | 0.0 | yes | 100% | 3/3 | ✅ survives full rigor |
| basket carry @ 2%/yr | +4 | 5.59 | 13.18 | 0.0 | yes | 79% | 2/3 | ⚠️ significant but not multiple-testing-proof / regime-fragile |
| basket carry @ 5%/yr | -5 | 0.11 | 0.25 | 0.451 | no | 47% | 2/3 | ❌ no robust edge |

---
**Summary:** 5 coins with usable funding history. Basket configs surviving rigor: 1/3. Remember: surviving rigor here = persistent positive carry in-sample, not a risk-free edge, and not executable on Alpaca. If it survives, the honest next step is a small-scale, real-cost feasibility study on a derivatives venue.