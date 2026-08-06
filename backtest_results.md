# Out-of-Sample Backtest — 2026-08-06 14:35 UTC

Timeframe 15Min · 8 symbols · net of 0.05% commission + 0.03% slippage
Symbols: BTC/USD, ETH/USD, SOL/USD, DOGE/USD, LINK/USD, AVAX/USD, LTC/USD, BCH/USD

Each strategy run ALONE. In-Sample = first half, Out-of-Sample = unseen second half. A real edge survives OOS.

| Strategy | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| macd_momentum | 403 | 0.89 | -3046 | 357 | 0.94 | -1474 | 37% | ❌ no edge |
| vwap_reversion | 246 | 0.72 | -4825 | 284 | 0.79 | -4113 | 38% | ❌ no edge |
| supertrend | 321 | 0.71 | -7413 | 323 | 0.9 | -2307 | 31% | ❌ no edge |
| breakout_momentum | 420 | 0.82 | -5867 | 417 | 0.57 | -13665 | 23% | ❌ no edge |

PF = profit factor (gross win / gross loss; >1 = profitable). A strategy that is strong IS but weak OOS is curve-fit, not an edge.