# Experiment #27 — cross-exchange funding differential [venues: bybit,binance,okx] (2026-09-22 10:10 UTC)

Perp-vs-perp across venues (long low-funding venue, short high-funding venue): market-neutral, ~no spot leg, harvests the funding DIFFERENTIAL. Combined series through full rigor; α/90.

> Honesty: the differential is small and arbitraged; needs collateral on ≥2 exchanges, cross-venue transfers, and dual liquidation risk — unpriced here. A ✅ = persistent in-sample differential, not free money.

| Coin | venues | avg differential%/yr | days |
|---|--:|--:|--:|
| BTC/USDT:USDT | 2 | +1.29 | 1391 |
| ETH/USDT:USDT | 2 | +1.19 | 1391 |
| SOL/USDT:USDT | 2 | +2.18 | 1370 |
| XRP/USDT:USDT | 2 | +1.94 | 1391 |
| DOGE/USDT:USDT | 2 | +1.11 | 1391 |

---
**Combined (5 coins):** ~+1.55%/yr, Sharpe 5.53, p=0.0, walk-fwd 100%, verdict: ✅ survives full rigor.

**Summary:** the differential is tiny (<3%/yr gross) — after two-venue fees, transfers and dual liquidation risk it is not a real edge; the level carry (#24-26) remains the only worthwhile version.