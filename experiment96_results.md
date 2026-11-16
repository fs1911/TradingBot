# Experiment #96 — all big 13F filers: newly bought vs sold stocks (2026-11-16 22:38 UTC)

54 13F data sets, 0 failed; 54 quarters; 17,855 CUSIPs needed, 10,662 mapped to tickers, 6,859 with prices.

## A hedge-fund proxy (≤ 150 positions)
52 quarters 2013-09 → 2026-06; managers per quarter median 676; stocks in universe median 1319; conviction-buy stocks per quarter median 75.

| portfolio (3 M after formation, vs SPY) | mean per quarter | t | ≤ 2017 | 2018 → | CAGR gross | CAGR net ≈ Yuh |
|---|--:|--:|--:|--:|--:|--:|
| Q1 most sold (Δbreadth lowest) | -0.88 % | -1.92 | -0.48 % | -1.08 % | +9.30 % | +5.62 % |
| Q2 | -0.67 % | -1.35 | +0.03 % | -1.04 % | +10.17 % | +6.33 % |
| Q3 | -0.55 % | -1.17 | +0.01 % | -0.85 % | +10.74 % | +7.02 % |
| Q4 | -0.68 % | -1.60 | +0.34 % | -1.23 % | +10.25 % | +6.52 % |
| Q5 most newly bought | -0.51 % | -1.37 | +0.10 % | -0.83 % | +11.02 % | +7.30 % |
| whole universe | -0.66 % | -1.57 | -0.00 % | -1.01 % | +10.32 % | +9.62 % |
| C conviction buys (≥ 3 new ≥ 1 % positions) | -0.41 % | -0.79 | +0.36 % | -0.82 % | +11.12 % | +7.63 % |
| SPY | — | — | — | — | +13.33 % | — |

| test | mean per quarter | t | p | Holm p | ≤ 2017 (t) | 2018 → (t) |
|---|--:|--:|--:|--:|--:|--:|
| Q5 − Q1 spread | +0.36 % | +1.11 | +0.27 | +0.66 | +0.58 % (+1.74) | +0.25 % (+0.53) |
| Q1 − universe (sell warning) | -0.22 % | -1.22 | +0.22 | +0.66 | -0.48 % (-2.37) | -0.08 % (-0.31) |
| C − universe | +0.25 % | +0.49 | +0.62 | +0.66 | +0.36 % (+0.90) | +0.19 % (+0.25) |

## B all filers ≥ $1bn
52 quarters 2013-09 → 2026-06; managers per quarter median 1290; stocks in universe median 3218; conviction-buy stocks per quarter median 114.

| portfolio (3 M after formation, vs SPY) | mean per quarter | t | ≤ 2017 | 2018 → | CAGR gross | CAGR net ≈ Yuh |
|---|--:|--:|--:|--:|--:|--:|
| Q1 most sold (Δbreadth lowest) | -0.77 % | -1.33 | -0.16 % | -1.10 % | +9.53 % | +5.90 % |
| Q2 | -0.87 % | -1.70 | -0.56 % | -1.03 % | +9.52 % | +5.82 % |
| Q3 | -1.01 % | -2.15 | -0.37 % | -1.35 % | +8.89 % | +5.31 % |
| Q4 | -0.82 % | -1.75 | -0.02 % | -1.25 % | +9.67 % | +5.92 % |
| Q5 most newly bought | -0.54 % | -1.11 | +0.40 % | -1.04 % | +10.77 % | +7.33 % |
| whole universe | -0.80 % | -1.72 | -0.14 % | -1.15 % | +9.72 % | +9.35 % |
| C conviction buys (≥ 3 new ≥ 1 % positions) | -0.37 % | -0.90 | +0.29 % | -0.72 % | +11.52 % | +8.28 % |
| SPY | — | — | — | — | +13.33 % | — |

| test | mean per quarter | t | p | Holm p | ≤ 2017 (t) | 2018 → (t) |
|---|--:|--:|--:|--:|--:|--:|
| Q5 − Q1 spread | +0.23 % | +0.61 | +0.54 | +1.00 | +0.56 % (+1.30) | +0.06 % (+0.11) |
| Q1 − universe (sell warning) | +0.03 % | +0.12 | +0.91 | +1.00 | -0.02 % (-0.07) | +0.05 % (+0.15) |
| C − universe | +0.44 % | +0.94 | +0.35 | +1.00 | +0.44 % (+0.99) | +0.44 % (+0.65) |

Reading: group A is the primary test (closest to 'hedge funds'); Holm over its 3 tests. Group B shows whether it is just the whole institutional market.
Caveats: survivorship (delisted stocks have no Yahoo prices — biases sold stocks upward); CUSIP→ticker via OpenFIGI; 13F = long US positions only, up to 50 days late.