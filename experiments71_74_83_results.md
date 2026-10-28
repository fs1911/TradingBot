# Experiments #71 / #74 / #83 — mixes & rebalancing, number of stocks, market regimes (2026-10-28 13:54 UTC)

## #71 Stock/bond mix and rebalancing (US, real, Shiller)
1871-02 → 2023-09.
| stocks/bonds | rebalancing | real CAGR | vol | max DD | worst 10 y p.a. | longest under water |
|---|---|--:|--:|--:|--:|--:|
| 100/0 | never (drifts) | +6.92 % | 14 % | -77 % | -5.9 % | 13 y |
| 80/20 | yearly | +6.27 % | 11 % | -65 % | -4.2 % | 12 y |
| 80/20 | monthly | +6.17 % | 12 % | -66 % | -4.2 % | 12 y |
| 80/20 | ±5 pt band | +6.31 % | 12 % | -65 % | -4.1 % | 12 y |
| 80/20 | ±10 pt band | +6.41 % | 12 % | -64 % | -4.4 % | 12 y |
| 80/20 | never (drifts) | +6.76 % | 13 % | -75 % | -5.9 % | 13 y |
| 60/40 | yearly | +5.48 % | 9 % | -48 % | -4.0 % | 12 y |
| 60/40 | monthly | +5.34 % | 9 % | -50 % | -4.2 % | 12 y |
| 60/40 | ±5 pt band | +5.49 % | 9 % | -48 % | -4.0 % | 12 y |
| 60/40 | ±10 pt band | +5.56 % | 9 % | -49 % | -4.1 % | 12 y |
| 60/40 | never (drifts) | +6.56 % | 13 % | -71 % | -5.9 % | 13 y |
| 40/60 | yearly | +4.57 % | 7 % | -43 % | -4.4 % | 12 y |
| 40/60 | monthly | +4.43 % | 7 % | -43 % | -4.5 % | 12 y |
| 40/60 | ±5 pt band | +4.59 % | 7 % | -43 % | -4.4 % | 12 y |
| 40/60 | ±10 pt band | +4.66 % | 7 % | -43 % | -4.5 % | 12 y |
| 40/60 | never (drifts) | +6.28 % | 12 % | -65 % | -5.9 % | 13 y |
| 20/80 | yearly | +3.54 % | 6 % | -45 % | -5.3 % | 12 y |
| 20/80 | monthly | +3.44 % | 6 % | -46 % | -5.4 % | 14 y |
| 20/80 | ±5 pt band | +3.51 % | 6 % | -45 % | -5.3 % | 12 y |
| 20/80 | ±10 pt band | +3.67 % | 6 % | -45 % | -5.3 % | 12 y |
| 20/80 | never (drifts) | +5.80 % | 10 % | -51 % | -5.7 % | 13 y |

## #74 How many single stocks? (20 years, simulated market as in #58)
Market (= all stocks) ×3.8. Math: with idiosyncratic σ 40 % and market σ ~16 %, portfolio σ ≈ √(16² + 40²/n): 1 stock 43 %, 5 → 24 %, 20 → 18 %, 50 → 17 %.
| stocks held | 5 % worst | median | 95 % best | trails the market by > 30 % | loses money |
|---|--:|--:|--:|--:|--:|
| 1 | ×0.0 | ×0.5 | ×15.4 | 78 % | 61 % |
| 2 | ×0.0 | ×1.0 | ×14.2 | 72 % | 50 % |
| 5 | ×0.2 | ×1.8 | ×12.3 | 64 % | 32 % |
| 10 | ×0.5 | ×2.3 | ×11.9 | 56 % | 17 % |
| 20 | ×0.9 | ×2.7 | ×10.6 | 49 % | 6 % |
| 30 | ×1.2 | ×2.9 | ×9.6 | 44 % | 2 % |
| 50 | ×1.5 | ×3.1 | ×8.5 | 37 % | 0 % |
| 100 | ×1.9 | ×3.4 | ×7.3 | 26 % | 0 % |

Real US stocks (705 survivors, 10 years):
- 1 stocks: 5 % ×0.0, median ×1.9, 95 % ×9.2, trails the average stock by > 30 %: 51 %
- 5 stocks: 5 % ×0.9, median ×2.5, 95 % ×5.7, trails the average stock by > 30 %: 32 %
- 10 stocks: 5 % ×1.4, median ×2.7, 95 % ×4.8, trails the average stock by > 30 %: 22 %
- 20 stocks: 5 % ×1.7, median ×2.8, 95 % ×4.2, trails the average stock by > 30 %: 12 %
- 50 stocks: 5 % ×2.1, median ×2.8, 95 % ×3.6, trails the average stock by > 30 %: 2 %

## #83 Market regimes (2-state hidden Markov model, S&P monthly)
Full-sample fit: calm state mean +12.3 %/yr, vol 10 %; turbulent mean -20.7 %/yr, vol 25 %; stay probability calm 0.97, turbulent 0.85 (average duration 33 / 7 months).
Walk-forward 1901-02–2023-09 (refit yearly on past data only):
| strategy | real CAGR | vol | max DD | invested |
|---|--:|--:|--:|--:|
| Buy & hold | +6.49 % | 15 % | -77 % | 100 % |
| HMM: invested when P(calm) > 50 % | +6.96 % | 12 % | -51 % | 83 % |
| 10-month trend rule | +8.16 % | 10 % | -45 % | 66 % |

Note: Shiller monthly averages smooth prices (#35) — regime and trend results are slightly flattered.