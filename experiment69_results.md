# Experiments #69 / #81 — leverage and Kelly (2026-10-28 13:02 UTC)

S&P 500 daily 1928-01-03 → 2026-10-27 incl. dividends; borrowing at cash + 0.5 %, fund fee 0.9 % p.a. for leveraged versions (typical leveraged ETF).

## #69 Daily leverage (like leveraged ETFs)
| leverage | CAGR | volatility | max drawdown | worst 10 years p.a. | ever −90 %? | 20-y windows beating 1× | 20-y windows with a LOSS | ×final |
|---|--:|--:|--:|--:|:-:|--:|--:|--:|
| 1× | +10.3 % | 19 % | -84 % | -1.4 % | no | — | 0 % | 15,008 |
| 1.5× | +10.9 % | 28 % | -95 % | -7.9 % | yes | 63 % of 79 | 1 % | 27,475 |
| 2× | +11.6 % | 38 % | -98 % | -16.4 % | yes | 65 % of 79 | 3 % | 49,620 |
| 3× | +9.8 % | 57 % | -100 % | -37.7 % | yes | 57 % of 79 | 5 % | 10,050 |
| 2× monthly reset (no fund fee) | +12.6 % | 40 % | -99 % | -17.2 % | yes | 78 % of 79 | 3 % | 118,072 |

- from 1950-01: 1× +11.7 % (DD -55 %), 2× +15.2 % (DD -88 %), 3× +16.7 % (DD -98 %)
- from 1990-01: 1× +10.9 % (DD -55 %), 2× +14.3 % (DD -88 %), 3× +15.0 % (DD -98 %)
- from 2009-03: 1× +16.4 % (DD -34 %), 2× +27.7 % (DD -59 %), 3× +36.9 % (DD -77 %)

## #81 Kelly: the growth-optimal leverage — in hindsight and in real time
Whole sample: excess return μ − r = 7.9 %/yr, σ = 18.5 % → hindsight Kelly L* = 2.32. Growth g(L) ≈ L·(μ−r) − L²σ²/2 + r: at L* the growth is maximal; above 2·L* it is BELOW cash (volatility drag).
Real-time Kelly from the trailing 10 years ranged -2.2 … 10.0 (median 3.2); share of months it said > 2×: 71 %, < 0 (short!): 8 %.
Following the real-time Kelly estimate (capped 0–3×, monthly) 1938-01–2026-10: CAGR +18.4 % vs 1× +11.4 %, max DD -89 % vs -51 %.

Reading: leverage multiplies volatility, and volatility costs growth (≈ σ²/2 per unit² of leverage). Whether 2× pays off depends on the period; the growth-optimal leverage is only known in hindsight, and estimating it in real time swings wildly.