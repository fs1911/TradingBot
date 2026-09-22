# Experiment #23 — rebalancing premium (volatility harvesting) (2026-09-22 08:20 UTC)

Universe: 92 stocks, common span 2020-07-27 → 2026-09-21 (1546 days). Buy&hold equal-weight Sharpe = 0.96. EXCESS (rebalanced − buy&hold) through full rigor; haircut α/74.

> The excess isolates the pure rebalancing premium: beta and survivorship bias hit both legs equally and cancel. If the excess survives, systematic rebalancing adds a real, forecast-free return.

| Rebalance | cost | Rebal Sharpe | B&H Sharpe | Premium Sharpe | Premium OOS% | Premium p | sig | Verdict |
|---|--:|--:|--:|--:|--:|--:|:--:|---|
| weekly | 1bps | 0.95 | 0.96 | -0.25 | -11 | 0.7315 | n | ❌ |
| monthly | 1bps | 0.95 | 0.96 | -0.25 | -11 | 0.7315 | n | ❌ |
| monthly | 5bps | 0.95 | 0.96 | -0.25 | -11 | 0.732 | n | ❌ |
| quarterly | 5bps | 0.94 | 0.96 | -0.29 | -11 | 0.7595 | n | ❌ |

---
**Summary:** buy&hold Sharpe = 0.96. Rebalancing-premium survivors: 0; marginal: 0. Best premium Sharpe: -0.25 (p=0.7315). A tiny/insignificant premium means rebalancing is a risk-control tool here, not an added-return edge.