# Daily Trend-Following Edge Test — 2026-08-14 13:03 UTC

Timeframe 1Day · long/flat · net of 0.05% commission + 0.03% slippage. IS = first half of history, OOS = unseen second half. A real trend edge survives OOS (PF > 1.15, positive expectancy).

## EQUITIES
14 symbols with ≥400 daily bars: SPY, QQQ, AAPL, MSFT, NVDA, AMZN, TSLA, META, GOOGL, JPM, V, WMT, COIN, PLTR

| System | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| MA20/100+ATR3 | 165 | 1.31 | +25577 | 188 | 1.65 | +46407 | 47% | ✅ edge survives OOS |
| Faber SMA200 | 136 | 2.26 | +46498 | 110 | 3.34 | +75087 | 32% | ✅ edge survives OOS |

## METALS
7 symbols with ≥400 daily bars: GLD, SLV, GDX, PPLT, PALL, CPER, LIT

| System | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| MA20/100+ATR3 | 103 | 0.45 | -20411 | 114 | 2.45 | +38298 | 54% | ✅ edge survives OOS |
| Faber SMA200 | 95 | 0.26 | -18967 | 56 | 2.52 | +29151 | 18% | ✅ edge survives OOS |

## ENERGY
4 symbols with ≥400 daily bars: USO, UNG, XLE, DBC

| System | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| MA20/100+ATR3 | 55 | 1.64 | +12994 | 55 | 0.64 | -9899 | 35% | ❌ overfit (IS only) |
| Faber SMA200 | 30 | 2.72 | +11314 | 68 | 0.49 | -11037 | 7% | ❌ overfit (IS only) |

## CRYPTO
8 symbols with ≥400 daily bars: BTC/USD, ETH/USD, SOL/USD, DOGE/USD, LINK/USD, AVAX/USD, LTC/USD, BCH/USD

| System | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| MA20/100+ATR3 | 70 | 1.17 | +13964 | 85 | 1.77 | +41662 | 35% | ✅ edge survives OOS |
| Faber SMA200 | 56 | 1.95 | +33072 | 60 | 3.05 | +42284 | 23% | ✅ edge survives OOS |

PF = profit factor (gross win / gross loss; >1 = profitable). Trend systems trade rarely, so OOS trade counts are small — treat marginal PFs as noise.