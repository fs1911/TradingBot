# Experiment #19 — broad-universe scan (2026-09-21 07:00 UTC)

All asset classes, daily data. Per symbol: Hurst (<0.45 mean-reverting, >0.55 trending), variance ratio, and RSI(2) mean-reversion through the full rigor battery (multiple-testing haircut α/60, realistic costs).

## Indizes
| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|:--:|---|
| SPY | 0.42 | 0.93 | +27 | 1.15 | 0.001 | n | ⚠️ |
| QQQ | 0.45 | 0.92 | +38 | 0.96 | 0.001 | n | ⚠️ |
| DIA | 0.41 | 0.97 | +4 | 0.64 | 0.0225 | n | ⚠️ |
| IWM | 0.46 | 0.95 | +21 | 0.29 | 0.1655 | n | ❌ |
| MDY | 0.42 | 0.94 | +1 | 0.09 | 0.3495 | n | ❌ |
| EFA | 0.42 | 1.03 | +2 | 0.2 | 0.2575 | n | ❌ |
| EEM | 0.43 | 0.89 | +17 | 0.28 | 0.2165 | n | ❌ |

## Sektoren
| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|:--:|---|
| XLK | 0.50 | 0.95 | +15 | 0.63 | 0.0165 | n | ⚠️ |
| XLF | 0.44 | 1.02 | +9 | 0.58 | 0.0395 | n | ⚠️ |
| XLE | 0.46 | 1.00 | -3 | 0.04 | 0.4405 | n | ❌ |
| XLV | 0.44 | 1.00 | +3 | 0.26 | 0.2235 | n | ❌ |
| XLY | 0.48 | 1.00 | +17 | 0.72 | 0.0175 | n | ⚠️ |
| XLI | 0.43 | 1.02 | +13 | 0.59 | 0.0365 | n | ⚠️ |
| XLP | 0.41 | 0.99 | -4 | 0.14 | 0.3435 | n | ❌ |
| XLU | 0.49 | 1.05 | -1 | -0.46 | 0.856 | n | ❌ |
| XLB | 0.43 | 1.06 | -10 | -0.49 | 0.895 | n | ❌ |
| XLRE | 0.44 | 1.03 | -2 | -0.1 | 0.5365 | n | ❌ |

## Edelmetalle
| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|:--:|---|
| GLD | 0.48 | 0.95 | +14 | 0.15 | 0.329 | n | ❌ |
| SLV | 0.46 | 0.88 | -5 | -0.13 | 0.669 | n | ❌ |
| PPLT | 0.52 | 1.06 | -89 | -0.34 | 0.686 | n | ❌ |
| PALL | 0.48 | 0.86 | -16 | -0.38 | 0.8405 | n | ❌ |
| GDX | 0.47 | 1.04 | +24 | 0.02 | 0.507 | n | ❌ |
| SIL | 0.43 | 1.00 | +28 | 0.04 | 0.4825 | n | ❌ |

## Industriemetalle/Rohstoffe
| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|:--:|---|
| CPER | 0.42 | 0.86 | +1 | 0.3 | 0.1805 | n | ❌ |
| LIT | 0.53 | 0.98 | -4 | 0.37 | 0.1105 | n | ❌ |
| URA | 0.47 | 1.04 | +14 | 0.16 | 0.2995 | n | ❌ |
| DBC | 0.48 | 1.09 | -5 | 0.14 | 0.3395 | n | ❌ |
| DBB | 0.47 | 0.84 | -5 | -0.19 | 0.667 | n | ❌ |
| USO | 0.32 | 0.97 | -3 | 0.51 | 0.0615 | n | ❌ |
| UNG | 0.47 | 0.88 | -17 | -0.01 | 0.5075 | n | ❌ |
| XOP | 0.44 | 0.92 | +9 | 0.26 | 0.2455 | n | ❌ |

## Agrar
| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|:--:|---|
| CORN | 0.49 | 0.78 | -5 | -0.07 | 0.554 | n | ❌ |
| WEAT | 0.49 | 0.96 | -14 | -0.06 | 0.5355 | n | ❌ |
| SOYB | 0.47 | 0.53 | -5 | 0.22 | 0.274 | n | ❌ |
| DBA | 0.41 | 0.98 | -8 | 0.17 | 0.274 | n | ❌ |

## Waehrungen
| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|:--:|---|
| UUP | 0.51 | 0.99 | -8 | -0.02 | 0.4795 | n | ❌ |
| FXE | 0.49 | 0.61 | -4 | 0.24 | 0.2655 | n | ❌ |
| FXY | 0.52 | 0.77 | +2 | 0.53 | 0.041 | n | ⚠️ |
| FXB | 0.48 | 0.59 | -2 | -0.01 | 0.5065 | n | ❌ |
| FXF | 0.45 | 0.68 | +2 | 0.33 | 0.2015 | n | ❌ |
| FXC | 0.44 | 0.80 | -9 | -1.36 | 0.9995 | n | ❌ |
| FXA | 0.43 | 0.80 | -2 | -0.27 | 0.717 | n | ❌ |

## Anleihen
| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|:--:|---|
| TLT | 0.50 | 0.82 | -5 | -0.04 | 0.5445 | n | ❌ |
| IEF | 0.51 | 0.88 | -2 | -0.36 | 0.8765 | n | ❌ |
| SHY | 0.50 | 0.83 | -3 | -1.16 | 1.0 | n | ❌ |
| HYG | 0.43 | 0.96 | +2 | 0.35 | 0.1365 | n | ❌ |
| LQD | 0.53 | 0.92 | -1 | -0.2 | 0.704 | n | ❌ |
| TIP | 0.51 | 0.88 | -1 | -0.27 | 0.78 | n | ❌ |

## Krypto
| Symbol | Hurst | VarRatio | RSI2 OOS ret% | Sharpe | p-value | sig | Verdict |
|---|--:|--:|--:|--:|--:|:--:|---|
| BTC/USD | 0.52 | 0.95 | +41 | 0.47 | 0.03 | n | ❌ |
| ETH/USD | 0.51 | 0.99 | +10 | 0.19 | 0.203 | n | ❌ |
| SOL/USD | 0.56 | 0.99 | +8 | 0.15 | 0.2665 | n | ❌ |
| LTC/USD | 0.44 | 0.88 | +58 | 0.37 | 0.135 | n | ❌ |
| BCH/USD | 0.49 | 1.00 | +10 | 0.2 | 0.223 | n | ❌ |
| AVAX/USD | 0.55 | 1.15 | -11 | -0.04 | 0.5465 | n | ❌ |
| LINK/USD | 0.47 | 0.91 | -11 | -0.16 | 0.724 | n | ❌ |

---
**Summary:** 55 symbols scanned. RSI(2) survives full rigor on 0 (none); marginal on 8 (SPY, QQQ, DIA, XLK, XLF, XLY, XLI, FXY). With 55 tests, expect ~3 false positives at p<0.05 by chance — judge survivors against that.