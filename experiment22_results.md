# Experiment #22 — long-only momentum: alpha or beta? (2026-09-22 07:59 UTC)

Universe: 92 stocks. Span: 2018-04-25 → 2026-09-21 (1549 days). Long-only, monthly, 5 bps. Equal-weight-universe benchmark Sharpe = 1.03. Rigor on EXCESS returns; haircut α/70.

> The excess (portfolio − equal-weight benchmark) series is market-neutral by construction: if IT survives rigor, the selection adds real alpha; if not, the raw long-only Sharpe was market beta.

| Selection | quantile | Port Sharpe | Bench Sharpe | Alpha Sharpe | Alpha OOS% | Alpha p | sig | Verdict |
|---|--:|--:|--:|--:|--:|--:|:--:|---|
| Raw 12-1 | top 10% | 0.72 | 1.03 | 0.31 | +34 | 0.2155 | n | ❌ |
| Raw 12-1 | top 20% | 0.73 | 1.03 | 0.01 | +12 | 0.468 | n | ❌ |
| Raw 12-1 | top 30% | 0.78 | 1.03 | -0.18 | +14 | 0.621 | n | ❌ |
| Residual | top 10% | 0.61 | 1.03 | 0.14 | +5 | 0.396 | n | ❌ |
| Vol-scaled | top 10% | 0.61 | 1.03 | 0.15 | +7 | 0.3825 | n | ❌ |

---
**Summary:** benchmark (equal-weight universe) Sharpe = 1.03. Excess-return survivors: 0; marginal: 0. Best alpha Sharpe: 0.31 (p=0.2155). If the alpha Sharpes are near 0 while the benchmark Sharpe is high, the long-only momentum result was market beta, not selection skill.