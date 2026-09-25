# Experiment #42 — chart-technical rules under a placebo test (2026-09-25 11:37 UTC)

Markets usable: 44/44. Cash = ^IRX ok. Rules: 13; Bonferroni α/13 = 0.0038 on the pooled placebo p (project total trials now ≈178).
Markets: Anleihen: US-Staatsanl. 20J+, US-Staatsanl. 7-10J, Unternehmensanl., Hochzinsanl. (Fonds); Einzelaktien: AAPL, MSFT, JPM, XOM, KO, IBM, GE, INTC, Nestlé, Novartis, UBS, SAP, Siemens; Indizes: S&P 500, Dow Jones, Nasdaq Comp., Russell 2000, DAX, SMI, FTSE 100, CAC 40, Nikkei 225, Hang Seng, Euro Stoxx 50; Krypto: Bitcoin, Ethereum; Rohstoffe: Gold, Silber, Rohöl WTI, Erdgas, Kupfer, Mais, Weizen, Soja; Waehrungen: EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, EUR/CHF

Timing edge = real Σ pos·(r − cash) minus the average over circular shifts of the SAME position series (same exposure, trades, holding times; timing destroyed). Units: % per year of excess return, averaged over markets.

| Rule | exposure | trades/yr | win rate | avg trade | timing edge | placebo p | sig | markets > own 95% | Sharpe net vs B&H (median Δ) | markets net Sharpe > B&H |
|---|--:|--:|--:|--:|--:|--:|:--:|--:|--:|--:|
| Fibonacci 38.2% (120d swing) | 35% | 3.6 | 34% | +0.93% | -0.72% | 0.943 | ❌ | 0/44 | -0.19 | 7/44 |
| Fibonacci 50% (120d swing) | 27% | 3.3 | 27% | +0.75% | -0.72% | 0.950 | ❌ | 0/44 | -0.21 | 5/44 |
| Fibonacci 61.8% (120d swing) | 20% | 3.0 | 22% | +0.61% | -0.55% | 0.915 | ❌ | 0/44 | -0.27 | 7/44 |
| Fibonacci 61.8% (60d swing) | 19% | 3.9 | 22% | +0.38% | -0.62% | 0.947 | ❌ | 1/44 | -0.25 | 8/44 |
| Support bounce (60d low) | 35% | 3.6 | 45% | +0.74% | -0.99% | 0.992 | ❌ | 2/44 | -0.19 | 8/44 |
| Support bounce (250d low) | 15% | 1.3 | 42% | +0.88% | -0.44% | 0.945 | ❌ | 4/44 | -0.26 | 3/44 |
| Breakout 20/10 (Donchian) | 42% | 5.7 | 43% | +1.09% | +0.91% | 0.016 | ❌ | 6/44 | -0.13 | 14/44 |
| Breakout 55/20 (Turtle) | 38% | 2.6 | 44% | +2.12% | +0.51% | 0.107 | ❌ | 4/44 | -0.17 | 15/44 |
| Breakout 52-week high | 33% | 0.8 | 49% | +5.68% | +0.46% | 0.119 | ❌ | 5/44 | -0.09 | 14/44 |
| RSI(14) <30 → >50 | 12% | 1.5 | 69% | +1.28% | +0.54% | 0.036 | ❌ | 12/44 | -0.17 | 13/44 |
| MACD 12/26/9 cross | 51% | 10.0 | 39% | +0.67% | +0.52% | 0.124 | ❌ | 6/44 | -0.13 | 10/44 |
| Bollinger 20/2 lower band → mid | 22% | 4.1 | 69% | +0.58% | +0.44% | 0.124 | ❌ | 9/44 | -0.15 | 9/44 |
| Golden cross 50/200 | 61% | 0.7 | 47% | +18.61% | +0.27% | 0.267 | ❌ | 1/44 | -0.08 | 11/44 |

By chance about 5% of markets beat their own 95th placebo percentile (≈2.2 of 44).

### Timing edge by asset class (% p.a.; * = class-pooled placebo p < 0.05, ** = < α/rules)
| Rule | Anleihen | Einzelaktien | Indizes | Krypto | Rohstoffe | Waehrungen |
|---|--:|--:|--:|--:|--:|--:|
| Fibonacci 38.2% (120d swing) | +0.10 | -0.98 | -0.30 | -9.32 | +0.57 | -0.31 |
| Fibonacci 50% (120d swing) | +0.04 | -1.37 | -0.45 | -3.66 | +0.21 | -0.58 |
| Fibonacci 61.8% (120d swing) | +0.16 | -0.91 | -0.36 | -5.37 | +0.46 | -0.33 |
| Fibonacci 61.8% (60d swing) | -0.04 | -1.25 | -0.69 | -5.94 | +0.97 | +0.17 |
| Support bounce (60d low) | -0.08 | -0.95 | -0.96 | -13.77 | +0.66 | +0.33 |
| Support bounce (250d low) | -0.11 | +0.46 | -0.58 | -4.40 | -0.84 | -0.50 |
| Breakout 20/10 (Donchian) | +1.46** | +0.14 | +0.18 | +21.24** | -0.97 | -0.72 |
| Breakout 55/20 (Turtle) | +0.78* | -1.23 | +0.02 | +16.35** | +0.57 | -0.36 |
| Breakout 52-week high | +0.27 | -0.64 | -0.09 | +11.37* | +0.77 | -0.06 |
| RSI(14) <30 → >50 | -0.75 | +2.18** | +0.64* | -2.15 | -0.87 | +0.43 |
| MACD 12/26/9 cross | +0.66 | -0.55 | +1.13* | +13.40* | -0.89 | -0.80 |
| Bollinger 20/2 lower band → mid | -1.31 | +2.15** | +0.52 | -10.58 | +1.06 | +0.59* |
| Golden cross 50/200 | -0.44 | -1.44 | -0.12 | +12.61* | +1.06 | +0.01 |

### Timing edge by era (% p.a.; Brock/Lakonishok/LeBaron published 1992)
| Rule | ≤1991 | 1992–2007 | 2008+ |
|---|--:|--:|--:|
| Fibonacci 38.2% (120d swing) | -2.77 | -0.10 | -0.41 |
| Fibonacci 50% (120d swing) | -2.43 | -0.34 | -0.51 |
| Fibonacci 61.8% (120d swing) | -1.61 | -0.04 | -0.42 |
| Fibonacci 61.8% (60d swing) | -1.58 | -0.76 | -0.26 |
| Support bounce (60d low) | -1.98 | -0.58 | -0.16 |
| Support bounce (250d low) | -0.17 | +0.22 | -0.31 |
| Breakout 20/10 (Donchian) | +4.25 | -0.51 | +0.05 |
| Breakout 55/20 (Turtle) | +2.05 | -0.75 | -0.19 |
| Breakout 52-week high | +0.97 | +0.15 | -0.70 |
| RSI(14) <30 → >50 | -1.83 | +1.02 | +1.19 |
| MACD 12/26/9 cross | +2.30 | +0.44 | +0.06 |
| Bollinger 20/2 lower band → mid | -1.89 | +0.80 | +1.26 |
| Golden cross 50/200 | -1.31 | -0.72 | -0.15 |

**Summary:** 0/13 rules show a timing edge beyond the placebo after the Bonferroni haircut. A high win rate alone says nothing: the placebo has the same exposure and trade structure. Survivorship: single stocks are today's large caps.