# Experiment #30 — valuation gauges for Finanzradar (2026-09-23 03:51 UTC)

Contrarian valuation: does 'cheap' (deep drawdown / far below the 200d MA) predict higher forward 90-day returns? Native daily prices. A read for Finanzradar, not a bot trade.

## Drawdown from ATH — forward return by depth
| Asset | deepest-DD bucket fwd% | near-ATH bucket fwd% | contrarian? |
|---|--:|--:|:--:|
| SPY | +5.0 | +5.1 | ❌ no |
| QQQ | +7.5 | +4.6 | ✅ yes |
| DIA | +5.2 | +3.6 | ✅ yes |
| IWM | +6.0 | +9.3 | ❌ no |
| BTC/USD | +17.0 | -5.7 | ✅ yes |
| ETH/USD | +22.1 | +0.4 | ✅ yes |

## Distance from 200d MA — forward return by level
| Asset | far-below bucket fwd% | far-above bucket fwd% | contrarian? |
|---|--:|--:|:--:|
| SPY | +3.4 | +4.4 | ❌ no |
| QQQ | +2.7 | +3.9 | ❌ no |
| DIA | +4.9 | +0.9 | ✅ yes |
| IWM | +4.2 | +3.3 | ✅ yes |
| BTC/USD | -3.2 | +5.0 | ❌ no |
| ETH/USD | +14.7 | -6.9 | ✅ yes |

## Finanzradar bands (pooled drawdown, 9833 obs)
| Zustand | Drawdown-Band | Ø Folge-Rendite (90T) |
|---|---|--:|
| 🟢 Kaufen | ≤ −35% | +14.0% (n=2291) |
| 🟡 Halten | −35% … −10% | +2.4% (n=2788) |
| 🔴 Überhitzt | > −10% (nahe ATH) | +4.3% (n=4754) |

---
**Summary:** drawdown-from-ATH is contrarian (cheap → higher forward return) in 4/6 assets; distance-from-200d-MA in 3/6. The bands above are a usable Finanzradar overlay — deep drawdowns historically preceded better forward returns.