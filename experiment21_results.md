# Experiment #21 — momentum, done properly (2026-09-22 07:41 UTC)

Universe: 92 stocks. Span: 2018-04-25 → 2026-09-21 (1549 days). All monthly rebalanced, 5 bps costs, decile long/short (unless noted). Multiple-testing haircut α/66.

> ⚠️ Survivorship bias (today's large caps) inflates results — a failure here is a firm negative; a marginal winner is discounted.

| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| 1. Raw 12-1 (baseline) | -8 | 0.43 | 1.07 | 0.1505 | no | 33% | 2/3 | ❌ no robust edge |
| 2. Vol-scaled ranking | -12 | 0.32 | 0.79 | 0.2375 | no | 29% | 2/3 | ❌ no robust edge |
| 3. Residual (idiosyncratic) | -7 | 0.27 | 0.68 | 0.2865 | no | 29% | 1/3 | ❌ no robust edge |
| 4. Vol-managed (Barroso) | -4 | 0.42 | 1.04 | 0.1315 | no | 38% | 2/3 | ❌ no robust edge |
| 5. Regime-filtered (>200d) | -7 | 0.33 | 0.82 | 0.246 | no | 29% | 2/3 | ❌ no robust edge |
| 6. Long-only top decile | +106 | 0.72 | 1.79 | 0.0195 | no | 48% | 3/3 | ❌ no robust edge |

---
**Summary:** 6 momentum refinements on 92 stocks. Survive full rigor: 0 (none); marginal: 0 (none). Best Sharpe: 6. Long-only top decile = 0.72 (p=0.0195).