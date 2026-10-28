# Experiments #67 / #68 — currency hedging and home bias for a CHF investor (2026-10-28 13:49 UTC)

Sources: CHF per USD: DBnomics BIS/WS_XRU/M.CH.CHF.A; EUR per USD: DBnomics BIS/WS_XRU/M.XM.EUR.A; CH policy rate: DBnomics BIS/WS_CBPOL/M.CH; US policy rate: DBnomics BIS/WS_CBPOL/M.US; EA policy rate: DBnomics BIS/WS_CBPOL/M.XM.

## #67 Hedge the currency or not? (returns in CHF)
| asset | period | unhedged CAGR | hedged CAGR | unhedged vol | hedged vol | unhedged max DD | hedged max DD | 10-y windows hedging won |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| S&P 500 TR (USD) | 1980-02–2025-06 | +9.5 % | +8.4 % | 17 % | 15 % | -62 % | -51 % | 46 % |
| … in local currency | | +11.1 % | | 15 % | | -51 % | | |
| DAX (EUR) | 1999-02–2025-06 | +3.8 % | +4.7 % | 21 % | 20 % | -71 % | -70 % | 87 % |
| … in local currency | | +6.0 % | | 20 % | | -68 % | | |

Hedged ≈ local return + (CHF rate − foreign rate): the CHF usually had LOWER rates, so hedging costs roughly that gap every year; unhedged, the investor carries the currency moves instead.

## #68 Home bias: Swiss stocks (SPI TR) vs US stocks unhedged in CHF
2013-04–2025-06, monthly rebalanced; Sharpe vs Swiss policy rate.
| share Switzerland | CAGR (CHF) | vol | Sharpe | max DD | 1st half Sharpe | 2nd half Sharpe |
|---|--:|--:|--:|--:|--:|--:|
| 0 % | +12.4 % | 15 % | 0.85 | -22 % | 1.21 | 0.64 |
| 20 % | +11.4 % | 14 % | 0.85 | -20 % | 1.19 | 0.64 |
| 40 % | +10.3 % | 13 % | 0.84 | -20 % | 1.14 | 0.64 |
| 50 % | +9.8 % | 13 % | 0.83 | -20 % | 1.11 | 0.63 |
| 60 % | +9.3 % | 12 % | 0.81 | -20 % | 1.07 | 0.61 |
| 80 % | +8.1 % | 12 % | 0.74 | -20 % | 0.96 | 0.57 |
| 100 % | +7.0 % | 12 % | 0.65 | -20 % | 0.83 | 0.50 |

Best mix in the first half: 0 % Switzerland (Sharpe 1.21); in the second half it reached 0.64. Correlation CH vs US (in CHF): +0.72.