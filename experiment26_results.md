# Experiment #26 — broader / smarter structural carry [data: bybit] (2026-09-22 09:57 UTC)

23 coins with usable funding history (BTC/USDT:USDT, ETH/USDT:USDT, SOL/USDT:USDT, XRP/USDT:USDT, DOGE/USDT:USDT, BNB/USDT:USDT, ADA/USDT:USDT, AVAX/USDT:USDT, LINK/USDT:USDT, DOT/USDT:USDT, LTC/USDT:USDT, TRX/USDT:USDT, ATOM/USDT:USDT, UNI/USDT:USDT, NEAR/USDT:USDT, APT/USDT:USDT, FIL/USDT:USDT, ARB/USDT:USDT, OP/USDT:USDT, AAVE/USDT:USDT, INJ/USDT:USDT, SUI/USDT:USDT, SEI/USDT:USDT). Span 2022-11-22 → 2026-09-22. Each variant's daily carry through the full rigor battery; haircut α/84.

> Same honesty as #24: ✅ = persistent in-sample carry, NOT risk-free (counterparty/liquidation/basis unmodeled). The spread variant also shorts low-funding perps — more legs, more cost, more exposure.

| Variant | ann.return% | Sharpe | p-value | sig | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|:--:|:--:|:--:|---|
| 1. Broad basket (equal-weight) | 5.8 | 7.05 | 0.0 | y | 79% | 3/3 | ✅ |
| 2. Carry-weighted (tilt to high funding) | 8.6 | 11.15 | 0.0 | y | 100% | 3/3 | ✅ |
| 3. Cross-sectional spread (dispersion) | 6.3 | 14.78 | 0.0 | y | 100% | 3/3 | ✅ |

---
**Summary:** Carry-weighting lifts the annual return (5.8%→8.6%) — tilting toward high-funding coins helps. Breadth may steady the drip, but the same cost-fragility and unpriced tail risks from #25 still bound how tradeable this is.