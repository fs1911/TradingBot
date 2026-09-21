# Experiment #16 — volume signals + stocks/bonds dual momentum (2026-09-21 04:19 UTC)

New categories: volume as a primary signal, and a defensive stocks-vs-bonds allocation. Full rigor battery, multiple-testing haircut α/40.

| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| VolCapitulation SPY | +2 | 0.29 | 0.72 | 0.119 | no | 57% | 3/3 | ❌ no robust edge |
| OBVtrend SPY | +24 | 0.52 | 1.29 | 0.0965 | no | 62% | 3/3 | ❌ no robust edge |
| VolCapitulation QQQ | +8 | 0.06 | 0.14 | 0.475 | no | 33% | 1/3 | ❌ no robust edge |
| OBVtrend QQQ | +39 | 0.53 | 1.3 | 0.104 | no | 62% | 3/3 | ❌ no robust edge |
| VolCapitulation IWM | +15 | 0.45 | 1.12 | 0.068 | no | 43% | 2/3 | ❌ no robust edge |
| OBVtrend IWM | -14 | -0.47 | -1.15 | 0.8605 | no | 10% | 0/3 | ❌ no robust edge |
| VolCapitulation BTC/USD | +1 | 0.27 | 0.79 | 0.224 | no | 60% | 2/3 | ❌ no robust edge |
| OBVtrend BTC/USD | +72 | 0.35 | 1.0 | 0.189 | no | 33% | 2/3 | ❌ no robust edge |
| DualMom SPY/TLT | +44 | 0.59 | 1.46 | 0.06 | no | 57% | 3/3 | ❌ no robust edge |

**Summary:** 0/9 survive the full battery. None — volume and allocation signals add no robust edge either.