# Experiment #17 — regime-conditional RSI(2) mean reversion (2026-09-21 04:23 UTC)

Apply the known RSI(2) reversal only in a volatility regime (high vs low), where theory says reversal is strongest. Can conditioning rescue the real-but-weak effect? Full rigor battery, multiple-testing haircut α/45.

| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|:--:|:--:|:--:|---|
| RSI2-highvol SPY | +24 | 0.6 | 1.49 | 0.016 | no | 57% | 3/3 | ⚠️ significant but not multiple-testing-proof / regime-fragile |
| RSI2-lowvol SPY | +16 | 1.02 | 2.52 | 0.001 | yes | 62% | 3/3 | ✅ survives full rigor |
| RSI2-highvol QQQ | +37 | 0.63 | 1.56 | 0.0075 | no | 62% | 3/3 | ⚠️ significant but not multiple-testing-proof / regime-fragile |
| RSI2-lowvol QQQ | +13 | 0.87 | 2.15 | 0.004 | no | 81% | 3/3 | ⚠️ significant but not multiple-testing-proof / regime-fragile |
| RSI2-highvol IWM | +15 | 0.3 | 0.74 | 0.1515 | no | 48% | 2/3 | ❌ no robust edge |
| RSI2-lowvol IWM | +12 | 0.21 | 0.53 | 0.2435 | no | 29% | 2/3 | ❌ no robust edge |
| RSI2-highvol XLK | +46 | 0.79 | 1.95 | 0.0015 | no | 67% | 3/3 | ⚠️ significant but not multiple-testing-proof / regime-fragile |
| RSI2-lowvol XLK | +11 | 0.76 | 1.88 | 0.0045 | no | 67% | 3/3 | ⚠️ significant but not multiple-testing-proof / regime-fragile |

**Summary:** 1/8 survive the full battery. RSI2-lowvol SPY