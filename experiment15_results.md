# Experiment #15 — machine learning (walk-forward logistic regression) (2026-09-21 04:16 UTC)

A logistic-regression classifier trained walk-forward on past data only, predicting next-day direction from 11 features, trading long/flat. Judged by the full rigor battery (multiple-testing haircut α/35).

| Symbol | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| SPY | +38 | 0.54 | 1.33 | 0.0975 | no | 45% | 2/3 | ❌ no robust edge |
| QQQ | +64 | 0.71 | 1.73 | 0.0295 | no | 55% | 2/3 | ⚠️ significant but not multiple-testing-proof / regime-fragile |
| IWM | +25 | 0.1 | 0.25 | 0.3695 | no | 20% | 2/3 | ❌ no robust edge |
| GLD | +50 | 0.65 | 1.58 | 0.062 | no | 60% | 2/3 | ❌ no robust edge |
| BTC/USD | -2 | -0.04 | -0.11 | 0.5725 | no | 31% | 1/3 | ❌ no robust edge |
| ETH/USD | +6 | 0.08 | 0.21 | 0.432 | no | 28% | 1/3 | ❌ no robust edge |

**Average feature weights (what the model used):** d_sma20 -0.15, rsi2 -0.15, r3 +0.11, r10 +0.10, r1 +0.08, r2 -0.08, rsi14 +0.05, vol20 -0.05, d_sma50 -0.04, vol10 -0.03, r5 -0.01

**Summary:** 0/6 symbols survive the full battery. None — the learned models do not generalise out-of-sample (as expected for price-only ML).