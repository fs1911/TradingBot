# Experiment #37 — the volatility risk premium (2026-09-25 06:43 UTC)

Data: VIX ✅ 1990, GSPC ✅ 1989, SP500TR ✅ 1988, PUT ✅ 1996, BXM ❌, SVXY ✅ 2011.

## 1 — Does implied volatility exceed later realised volatility?
| Period | months | VIX − realised (vol pts) | % months positive | t | worst month (pts, date) |
|---|--:|--:|--:|--:|---|
| full | 440 | +3.97 | 84% | +12.63 | -54.3 (2020-03) |
| before 2003 | 157 | +4.52 | 86% | +11.18 | -16.8 (1997-10) |
| after 2003 | 283 | +3.66 | 83% | +8.45 | -54.3 (2020-03) |
| since 2018 | 104 | +3.53 | 83% | +4.16 | -54.3 (2020-03) |

## 2 — Harvesting the premium vs S&P 500 total return (monthly, common period)
| Series | from | CAGR | vol | Sharpe | max DD | worst month | skew | beta | alpha/y | alpha t | sig after haircut |
|---|---|--:|--:|--:|--:|---|--:|--:|--:|--:|:--:|
| PutWrite (^PUT) | 1996-09 | +8.6% | 10.5% | 0.84 | -33% | -18% (2008-10) | -1.70 | 0.58 | +2.32% | +2.22 | ❌ |
| ↳ S&P 500 TR, same months | 1996-09 | +10.5% | 15.4% | 0.73 | -51% | -17% (2008-10) | -0.55 | 1.00 | — | — | — |
| BuyWrite (^BXM) | — | no data | | | | | | | | | |
| SVXY short-vol ETF | 2011-11 | +11.2% | 50.7% | 0.60 | -94% | -90% (2018-02) | -1.46 | 2.30 | -4.32% | -0.40 | ❌ |
| ↳ S&P 500 TR, same months | 2011-11 | +15.0% | 13.9% | 1.08 | -24% | -12% (2020-03) | -0.41 | 1.00 | — | — | — |

---
**Summary:** VRP full +4.0 pts (t +12.6, 84% of months positive); after 2003 +3.7 pts (t +8.4); since 2018 +3.5 pts (t +4.2); post-publication size 81% of pre; harvesting alpha significant after haircut: PutWrite (^PUT) no, SVXY short-vol ETF no.