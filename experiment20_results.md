# Experiment #20 — cross-sectional long/short over individual stocks (2026-09-22 06:30 UTC)

Universe: 92 stocks with ≥2y history. Span: 2018-04-25 → 2026-09-21 (1549 trading days). Dollar-neutral, decile long/short, equal weight. Multiple-testing haircut α/60.

> ⚠️ Survivorship bias: the universe is *today's* large caps, which INFLATES back-tested returns. A strategy that fails even here is a firm negative; a marginal winner must be discounted for the bias.

## Short-term reversal (5d, daily rebal)
| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| Short-term reversal (5d, daily rebal) @ 1bps | -10 | -0.27 | -0.66 | 0.776 | no | 19% | 0/3 | ❌ no robust edge |
| Short-term reversal (5d, daily rebal) @ 5bps | -46 | -0.81 | -2.0 | 0.985 | no | 0% | 0/3 | ❌ no robust edge |
| Short-term reversal (5d, daily rebal) @ 10bps | -71 | -1.49 | -3.69 | 1.0 | no | 0% | 0/3 | ❌ no robust edge |

## Cross-sectional momentum (12-1, monthly rebal)
| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| Cross-sectional momentum (12-1, monthly rebal) @ 1bps | -6 | 0.44 | 1.09 | 0.144 | no | 33% | 2/3 | ❌ no robust edge |
| Cross-sectional momentum (12-1, monthly rebal) @ 5bps | -8 | 0.43 | 1.07 | 0.1505 | no | 33% | 2/3 | ❌ no robust edge |
| Cross-sectional momentum (12-1, monthly rebal) @ 10bps | -10 | 0.42 | 1.04 | 0.1595 | no | 33% | 2/3 | ❌ no robust edge |

---
**Summary:** 6 portfolio configs tested on 92 stocks. Survive full rigor: 0 (none); marginal: 0 (none). Note the survivorship bias above — real, tradeable results would be weaker.