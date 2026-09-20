# Experiment #12 — documented anomalies under the strong rigor battery (2026-09-20 07:24 UTC)

Causal strategies, realistic costs, multiple-testing haircut α/30.

| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| TurnOfMonth SPY | +4 | 0.48 | 1.19 | 0.2025 | no | 33% | 2/3 | ❌ no robust edge |
| Overnight SPY | -55 | -2.13 | -5.27 | 1.0 | no | 0% | 0/3 | ❌ no robust edge |
| RSI2 SPY | +27 | 1.15 | 2.84 | 0.001 | yes | 81% | 3/3 | ✅ survives full rigor |
| TurnOfMonth QQQ | +11 | 0.24 | 0.6 | 0.265 | no | 38% | 2/3 | ❌ no robust edge |
| Overnight QQQ | -47 | -1.96 | -4.86 | 1.0 | no | 0% | 0/3 | ❌ no robust edge |
| RSI2 QQQ | +38 | 0.96 | 2.38 | 0.001 | yes | 76% | 3/3 | ✅ survives full rigor |
| TurnOfMonth IWM | -10 | 0.09 | 0.22 | 0.414 | no | 29% | 2/3 | ❌ no robust edge |
| Overnight IWM | -55 | -1.83 | -4.53 | 1.0 | no | 5% | 0/3 | ❌ no robust edge |
| RSI2 IWM | +21 | 0.29 | 0.72 | 0.1655 | no | 29% | 1/3 | ❌ no robust edge |
| LowVol universe | -5 | 0.2 | 0.49 | 0.2955 | no | 38% | 2/3 | ❌ no robust edge |

**Summary:** 2/10 survive the full battery. RSI2 SPY, RSI2 QQQ