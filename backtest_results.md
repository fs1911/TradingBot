# Grouped OOS Edge Test — 2026-08-14 12:47 UTC

Same honest out-of-sample test, run separately per asset class. A strategy earns live trading only if its edge survives OOS (PF > 1.15, positive expectancy) net of costs.

## EQUITIES
# Out-of-Sample Backtest — 2026-08-14 12:48 UTC

Timeframe 15Min · 14 symbols · net of 0.05% commission + 0.03% slippage
Symbols: SPY, QQQ, AAPL, MSFT, NVDA, AMZN, TSLA, META, GOOGL, JPM, V, WMT, COIN, PLTR

Each strategy run ALONE. In-Sample = first half, Out-of-Sample = unseen second half. A real edge survives OOS.

| Strategy | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| macd_momentum | 290 | 0.79 | -4537 | 265 | 0.79 | -4003 | 34% | ❌ no edge |
| vwap_reversion | 136 | 0.84 | -1487 | 115 | 0.82 | -1444 | 38% | ❌ no edge |
| supertrend | 244 | 0.85 | -2712 | 239 | 0.71 | -5449 | 27% | ❌ no edge |
| breakout_momentum | 332 | 0.87 | -3298 | 300 | 0.81 | -4497 | 30% | ❌ no edge |

PF = profit factor (gross win / gross loss; >1 = profitable). A strategy that is strong IS but weak OOS is curve-fit, not an edge.

## METALS
# Out-of-Sample Backtest — 2026-08-14 12:50 UTC

Timeframe 15Min · 7 symbols · net of 0.05% commission + 0.03% slippage
Symbols: GLD, SLV, GDX, PPLT, PALL, CPER, LIT

Each strategy run ALONE. In-Sample = first half, Out-of-Sample = unseen second half. A real edge survives OOS.

| Strategy | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| macd_momentum | 119 | 0.91 | -763 | 133 | 0.69 | -3159 | 32% | ❌ no edge |
| vwap_reversion | 33 | 0.34 | -1892 | 39 | 0.78 | -592 | 38% | ❌ no edge |
| supertrend | 116 | 0.62 | -3549 | 144 | 0.87 | -1399 | 32% | ❌ no edge |
| breakout_momentum | 105 | 0.83 | -1295 | 130 | 0.66 | -3468 | 28% | ❌ no edge |

PF = profit factor (gross win / gross loss; >1 = profitable). A strategy that is strong IS but weak OOS is curve-fit, not an edge.

## ENERGY
# Out-of-Sample Backtest — 2026-08-14 12:51 UTC

Timeframe 15Min · 4 symbols · net of 0.05% commission + 0.03% slippage
Symbols: USO, UNG, XLE, DBC

Each strategy run ALONE. In-Sample = first half, Out-of-Sample = unseen second half. A real edge survives OOS.

| Strategy | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| macd_momentum | 62 | 1.41 | +1566 | 70 | 0.85 | -739 | 36% | ❌ overfit (IS only) |
| vwap_reversion | 26 | 1.09 | +145 | 30 | 1.14 | +249 | 50% | ❌ no edge |
| supertrend | 78 | 0.78 | -1329 | 74 | 0.68 | -1926 | 26% | ❌ no edge |
| breakout_momentum | 89 | 0.76 | -1728 | 78 | 1.15 | +831 | 38% | ❌ no edge |

PF = profit factor (gross win / gross loss; >1 = profitable). A strategy that is strong IS but weak OOS is curve-fit, not an edge.

## CRYPTO
# Out-of-Sample Backtest — 2026-08-14 12:51 UTC

Timeframe 15Min · 8 symbols · net of 0.05% commission + 0.03% slippage
Symbols: BTC/USD, ETH/USD, SOL/USD, DOGE/USD, LINK/USD, AVAX/USD, LTC/USD, BCH/USD

Each strategy run ALONE. In-Sample = first half, Out-of-Sample = unseen second half. A real edge survives OOS.

| Strategy | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| macd_momentum | 407 | 0.99 | -374 | 375 | 0.84 | -4275 | 35% | ❌ no edge |
| vwap_reversion | 284 | 0.84 | -2957 | 246 | 0.74 | -4410 | 37% | ❌ no edge |
| supertrend | 356 | 0.67 | -9394 | 317 | 1.04 | +848 | 34% | ❌ no edge |
| breakout_momentum | 428 | 0.7 | -10370 | 420 | 0.67 | -10819 | 25% | ❌ no edge |

PF = profit factor (gross win / gross loss; >1 = profitable). A strategy that is strong IS but weak OOS is curve-fit, not an edge.
