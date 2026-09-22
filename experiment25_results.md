# Experiment #25 — funding carry, net of realistic costs [data: bybit] (2026-09-22 09:32 UTC)

Delta-neutral carry NET of a concrete fee model (Bybit taker 0.055% / maker 0.020% per leg), assumed hedge-leg annual vol 60%. Sweeps rotation frequency and fee tier. Target income: 3,650 CHF/yr.

> This converts the big Sharpe into francs. Net annual return × your capital = your income; the last column is the capital needed to hit the target. Counterparty/liquidation/basis risk are still NOT priced.

Basket of 4 coins (BTC/USDT:USDT, ETH/USDT:USDT, XRP/USDT:USDT, DOGE/USDT:USDT). Gross carry ≈ 7.9%/yr, vol ≈ 0.6%/yr, gross Sharpe ≈ 13.5.

| Fee tier | Rotation | Exec drag | Rehedge drag | Net return/yr | Net Sharpe | Capital for target |
|---|--:|--:|--:|--:|--:|--:|
| taker | 7d | 11.5% | 0.9% | -4.4% | -7.5 | ∞ (net ≤ 0) |
| taker | 30d | 2.7% | 0.9% | +4.4% | 7.5 | 82,760 CHF |
| taker | 90d | 0.9% | 0.9% | +6.2% | 10.6 | 58,920 CHF |
| maker | 7d | 4.2% | 0.3% | +3.5% | 5.9 | 105,442 CHF |
| maker | 30d | 1.0% | 0.3% | +6.7% | 11.3 | 54,807 CHF |
| maker | 90d | 0.3% | 0.3% | +7.3% | 12.4 | 49,941 CHF |

---
**Summary:** net carry stays positive under some cost settings — a real but modest, capital-hungry return; compare it honestly against ~4-5% risk-free cash for the operational and counterparty risk taken on.