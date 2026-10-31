# Experiments #75 / #79 — post-earnings drift, dividends (2026-10-31 10:41 UTC)

## #75 Post-earnings drift (SUE from 10-Q EPS, from the filing date, next 60 trading days vs SPY)
62,380 quarterly events, 2,072 stocks, 2010Q3–2026Q3.
Prices ≥ $5 at the event, implausible moves (≤ −95 % / ≥ +300 % in 60 days) dropped, winsorised 1 %/99 %.
| SUE decile | events | 60-day return vs SPY (mean) | median |
|---|--:|--:|--:|
| 1 (worst surprise) | 6,263 | -0.47 % | -0.95 % |
| 2 | 6,229 | -0.42 % | -1.04 % |
| 3 | 6,227 | -0.18 % | -0.80 % |
| 4 | 6,230 | -0.31 % | -1.09 % |
| 5 | 6,235 | -0.11 % | -0.71 % |
| 6 | 6,217 | +0.07 % | -0.61 % |
| 7 | 6,222 | -0.26 % | -0.53 % |
| 8 | 6,235 | +0.01 % | -0.44 % |
| 9 | 6,222 | +0.37 % | -0.35 % |
| 10 (best surprise) | 6,251 | +0.39 % | -0.14 % |
- top − bottom decile, all: +0.93 % per 60 days (63 quarters, t +2.56); ≈ +3.8 %/yr before costs if traded every quarter
- top − bottom decile, ≤ 2015: +1.63 % per 60 days (20 quarters, t +2.86); ≈ +6.7 %/yr before costs if traded every quarter
- top − bottom decile, 2016 →: +0.60 % per 60 days (43 quarters, t +1.32); ≈ +2.4 %/yr before costs if traded every quarter

## #79 Dividends (groups at the end of June, next 12 months vs equal-weight universe)
22,387 stock-years, 2011–2025 (stocks with ≥ 6 years of history).
Price ≥ $5 at formation; 12-month returns capped at −95 % / +300 % (data errors).
| group | stock-years | avg per year | excess vs universe p.a. | t (across years) | years positive |
|---|--:|--:|--:|--:|--:|
| grower (5 y) | 5,715 | 381 | -1.3 % | -0.79 | 5/15 |
| raiser | 4,184 | 279 | +0.5 % | +0.68 | 8/15 |
| steady | 4,246 | 283 | -1.8 % | -1.67 | 6/15 |
| initiator | 348 | 23 | +0.6 % | +0.47 | 8/15 |
| cutter | 1,162 | 77 | -0.0 % | -0.01 | 4/15 |
| non-payer | 6,732 | 449 | +1.8 % | +1.08 | 9/15 |

Survivorship: Yahoo only has currently listed tickers — dividend cutters that later went bankrupt are missing (biases the 'cutter' group upwards).