# Experiment #11 — batch of hypotheses under the STRONG rigor battery (2026-09-19 13:55 UTC)

Each strategy is causal and judged by: OOS return, Sharpe, t-stat, a block-bootstrap p-value with a multiple-testing haircut (α/20), walk-forward, and regime stability (all 3 thirds positive). Realistic costs.

| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| Seasonality UNG | -65 | -0.34 | -0.84 | 0.818 | no | 14% | 1/3 | ❌ no robust edge |
| Seasonality USO | +53 | 0.44 | 1.08 | 0.13 | no | 29% | 2/3 | ❌ no robust edge |
| Seasonality XLE | +54 | 0.68 | 1.67 | 0.044 | no | 38% | 3/3 | ❌ no robust edge |
| Seasonality GLD | +53 | 0.53 | 1.3 | 0.0845 | no | 52% | 2/3 | ❌ no robust edge |
| Seasonality SPY | +43 | 0.51 | 1.27 | 0.0795 | no | 62% | 2/3 | ❌ no robust edge |
| LeadLag CPER->SPY | -32 | -1.09 | -2.63 | 0.9965 | no | 0% | 0/3 | ❌ no robust edge |
| LeadLag CPER->XLI | -34 | -0.87 | -2.1 | 0.973 | no | 0% | 0/3 | ❌ no robust edge |
| TermStruct VXX/VIXM->SVXY | -44 | 0.14 | 0.35 | 0.356 | no | 30% | 1/3 | ❌ no robust edge |
| Weekday BTC/USD | +16 | 0.11 | 0.32 | 0.3345 | no | 37% | 1/3 | ❌ no robust edge |
| Weekday ETH/USD | -72 | -0.23 | -0.65 | 0.7415 | no | 17% | 1/3 | ❌ no robust edge |

**Summary:** 0 of 10 hypotheses survive the full rigor battery. None — all fail significance, walk-forward, or regime stability.