# Experiment #97 — stock-market Fear & Greed index, rebuilt (2026-11-20 06:38 UTC)

18 Yahoo series loaded, missing: CNN (<HTTPError 418: 'Unknown Error'>); CNN history: 0 days.

Index history: long version (4 ingredients) from 2003-02-26, full version (7) from 2007-11-05.
CNN's own series could not be downloaded — no direct check.
**Latest (2026-11-19): 17** — momentum 1, strength 5, breadth 86, options 1, volatility 1, safe haven 2, junk bonds 24
Lowest in the last 60 days: 17 on 2026-11-19.

## 1 After entering extreme fear (< 25) / extreme greed (> 75) — vs all days (entry next day)
| index | zone | asset | events | 1 M mean (all days) / beat-all p | 3 M mean (all days) / beat-all p | 12 M mean (all days) / beat-all p |
|---|---|---|--:|---|---|---|
| long | fear < 25 | SPY | 60 | +1.3 % (+1.0 %) / +0.652 | +3.8 % (+3.1 %) / +0.473 | +12.5 % (+12.3 %) / +0.944 |
| long | fear < 25 | QQQ | 60 | +1.3 % (+1.4 %) / +0.919 | +4.4 % (+4.2 %) / +0.898 | +16.7 % (+16.9 %) / +0.909 |
| long | fear < 25 | SMH | 60 | +1.6 % (+1.7 %) / +0.974 | +5.7 % (+5.2 %) / +0.779 | +19.5 % (+21.1 %) / +0.706 |
| long | greed > 75 | SPY | 58 | +1.4 % (+1.0 %) / +0.493 | +3.4 % (+3.1 %) / +0.764 | +13.8 % (+12.3 %) / +0.459 |
| long | greed > 75 | QQQ | 58 | +2.2 % (+1.4 %) / +0.232 | +4.4 % (+4.2 %) / +0.862 | +19.3 % (+16.9 %) / +0.361 |
| long | greed > 75 | SMH | 58 | +3.6 % (+1.7 %) / +0.058 | +6.2 % (+5.2 %) / +0.590 | +24.3 % (+21.1 %) / +0.461 |
| full | fear < 25 | SPY | 53 | +1.3 % (+1.0 %) / +0.638 | +3.3 % (+3.0 %) / +0.789 | +9.2 % (+13.3 %) / +0.070 |
| full | fear < 25 | QQQ | 53 | +1.2 % (+1.4 %) / +0.847 | +4.3 % (+4.3 %) / +0.997 | +14.5 % (+19.0 %) / +0.109 |
| full | fear < 25 | SMH | 53 | +1.8 % (+1.9 %) / +0.898 | +6.9 % (+6.0 %) / +0.612 | +19.3 % (+26.9 %) / +0.098 |
| full | greed > 75 | SPY | 47 | +1.4 % (+1.0 %) / +0.525 | +3.4 % (+3.0 %) / +0.728 | +14.7 % (+13.3 %) / +0.564 |
| full | greed > 75 | QQQ | 47 | +2.2 % (+1.4 %) / +0.303 | +5.4 % (+4.3 %) / +0.419 | +22.4 % (+19.0 %) / +0.266 |
| full | greed > 75 | SMH | 47 | +2.4 % (+1.9 %) / +0.629 | +6.5 % (+6.0 %) / +0.775 | +28.7 % (+26.9 %) / +0.706 |

Primary (long index, SPY), Holm over 4: fear < 25 3 M: +3.8 % vs +3.1 %, p +0.473, Holm +1.000; fear < 25 12 M: +12.5 % vs +12.3 %, p +0.944, Holm +1.000; greed > 75 3 M: +3.4 % vs +3.1 %, p +0.764, Holm +1.000; greed > 75 12 M: +13.8 % vs +12.3 %, p +0.459, Holm +1.000

Extreme-fear entries (long index) and SPY afterwards: 2020-10-28 (+14.5 % 3 M), 2021-06-18 (+3.5 % 3 M), 2021-11-26 (-7.1 % 3 M), 2022-04-22 (-8.4 % 3 M), 2022-09-15 (+1.1 % 3 M), 2023-09-21 (+10.3 % 3 M), 2024-04-17 (+10.3 % 3 M), 2024-07-24 (+7.7 % 3 M), 2024-11-04 (+4.5 % 3 M), 2024-12-18 (-1.2 % 3 M), 2025-11-18 (+3.3 % 3 M), 2026-03-05 (+10.0 % 3 M), 2026-06-10 (+3.9 % 3 M), 2026-09-10 (— 3 M), 2026-10-19 (— 3 M)

## 2 Month-end index quintile → next-month SPY return (non-overlapping)
| quintile | index range | months | next month mean | positive |
|---|---|--:|--:|--:|
| Q1 (fear) | 0–24 | 57 | +2.0 % | 65 % |
| Q2  | 24–46 | 57 | +0.5 % | 61 % |
| Q3  | 46–60 | 56 | +0.9 % | 68 % |
| Q4  | 60–69 | 57 | +0.4 % | 65 % |
| Q5 (greed) | 69–91 | 57 | +1.2 % | 68 % |
- Q1 − Q5: +0.7 % per month (t +0.77)

## 3 Rules on SPY (long index; net of 0.50 % per switch side ≈ Yuh; out of market earns BIL)
| rule | CAGR | max drawdown | Sharpe | switches |
|---|--:|--:|--:|--:|
| buy & hold | +11.5 % | -55 % | +0.68 | — |
| static 70 % | +8.7 % | -41 % | +0.71 | — |
| S1 avoid greed (out > 75, in < 50) | +4.5 % | -55 % | +0.34 | — |
| S2 buy fear (70 % → 100 % when < 25, back > 50) | +8.5 % | -51 % | +0.57 | — |

Reading: the index shows fear AFTER prices fell — so it cannot warn before a crash. The only useful question is whether buying in extreme fear (or leaving in extreme greed) paid off over many cases.
Caveats: rebuilt index (proxies, not CNN's exact formula); few independent events (crashes cluster); SPY/QQQ/SMH price returns; Yahoo history only.