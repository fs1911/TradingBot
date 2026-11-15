# Experiment #92 — backtest of the Yuh scanner colour (US stocks) (2026-11-15 12:34 UTC)

Universe: 2,583 SEC large caps, 2,348 with share data, 2,304 with Yahoo prices.

202 months 2010-01–2026-10, 2,296 stocks, 345,722 stock-months. Colour share: 🟢 18 %, 🟡 37 %, 🔴 45 %.

## 1 What happened after each colour (vs SPY; disaster = 12 M ≤ −40 % absolute, or 3 M ≤ −20 % vs SPY)
| colour | stock-months | 1 M mean | 3 M mean | 12 M mean / median | 12 M beat SPY | disaster 12 M | disaster 3 M |
|---|--:|--:|--:|--:|--:|--:|--:|
| 🟢 | 62,619 | +0.19 % | +0.27 % | +1.0 % / -3.1 % | 45 % | 4.3 % | 7.9 % |
| 🟡 | 126,608 | -0.07 % | -0.04 % | -0.7 % / -3.3 % | 45 % | 3.7 % | 6.5 % |
| 🔴 | 156,495 | -0.04 % | -0.32 % | -0.7 % / -5.7 % | 43 % | 8.2 % | 12.1 % |

- 🟢 − 🔴 next month: +0.21 %/month (t +1.07, 169 months); ≤ 2017 +0.06 % (t +0.24); 2018 → +0.35 % (t +1.16)
- 🟢 vs SPY next month: +0.25 %/month (t +1.39)

## 2 Monthly portfolios (equal weight, rebalanced monthly)
| portfolio | CAGR gross | CAGR net 0.10 %/side | CAGR net 0.50 %/side (≈ Yuh) | max drawdown (gross) |
|---|--:|--:|--:|--:|
| 🟢 only | +11.9 % | +11.0 % | +7.2 % | -21 % |
| 🔴 only | +13.3 % | +12.4 % | +8.9 % | -33 % |
| whole universe | +14.1 % | +14.0 % | +13.8 % | -32 % |
| SPY (buy & hold) | +14.4 % | — | — | -24 % |

Reading: 'trifft' is not the goal — the question is whether 🟢 stocks did better and 🔴 stocks crashed more often, over many cases, after costs.
Caveats: survivorship (only stocks still listed have Yahoo prices); US large caps only; market rule = SPY above its 200-day average; Yuh costs (0.5 %/side + 0.95 % FX for USD) make monthly trading expensive.