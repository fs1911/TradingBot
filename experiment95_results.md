# Experiment #95 — commodity → producer: does the producer follow later? (2026-11-16 19:09 UTC)

45 symbols loaded, missing: BITF, CTRA.

## 1 Primary: slope of the producer's NEXT month on the commodity's PAST month (vs SPY, own momentum controlled)
| group | timing | chain-months | slope | t (clustered) | placebo p | Holm p | same-month slope (t) | ≤ 2017 slope (t) | 2018 → slope (t) |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| A new commodities | next month | 1,152 | +0.063 | +1.13 | +0.194 | +0.236 | +0.62 (+11.55) | +0.003 (+0.04) | +0.082 (+1.17) |
| A new commodities | skip 1st day | 1,152 | +0.056 | +1.04 | +0.118 | +0.236 | +0.62 (+11.55) | -0.001 (-0.02) | +0.074 (+1.09) |
| B replication, new stocks | next month | 478 | +0.415 | +2.39 | +0.002 | +0.008 | +1.19 (+12.67) | -0.032 (-0.10) | +0.494 (+2.47) |
| B replication, new stocks | skip 1st day | 478 | +0.401 | +2.32 | +0.002 | +0.008 | +1.19 (+12.67) | -0.054 (-0.17) | +0.485 (+2.44) |
| C #94 chains re-measured | next month | 549 | +0.266 | +1.69 | +0.002 | descriptive | +0.87 (+5.49) | +0.383 (+1.58) | +0.179 (+0.92) |
| C #94 chains re-measured | skip 1st day | 549 | +0.283 | +1.98 | +0.002 | descriptive | +0.87 (+5.49) | +0.371 (+1.82) | +0.220 (+1.15) |

## 2 Per chain: producer next month vs SPY after the commodity beat SPY and the producer lagged
| chain | months | same-month slope | next-month slope (t) | after signal | otherwise | difference (t) | skip-1st-day difference |
|---|--:|--:|--:|--:|--:|--:|--:|
| silver → silver miners | 202 | +1.10 | +0.078 (+0.83) | +3.9 % | -0.5 % | +4.4 % (+1.80) | +4.2 % (+1.73) |
| natural gas → gas producers | 202 | +0.34 | +0.018 (+0.24) | +2.7 % | -0.6 % | +3.3 % (+0.85) | +3.1 % (+0.81) |
| Brent oil → oil producers | 196 | +0.52 | -0.008 (-0.08) | +0.8 % | -0.6 % | +1.4 % (+1.08) | +1.2 % (+1.02) |
| grains → fertiliser & farm machinery | 202 | +0.32 | +0.091 (+0.81) | +0.0 % | -0.0 % | +0.0 % (+0.04) | -0.0 % (-0.03) |
| platinum/palladium → PGM miners | 201 | +1.36 | +0.111 (+0.66) | +4.3 % | -0.6 % | +4.8 % (+1.56) | +5.5 % (+1.78) |
| aluminium → aluminium smelters | 149 | +0.79 | +0.232 (+0.99) | +7.0 % | -0.9 % | +7.9 % (+2.44) | +7.2 % (+2.21) |
| gold → royalty companies | 202 | +1.26 | +0.069 (+0.52) | +3.9 % | -0.1 % | +4.0 % (+1.71) | +3.6 % (+1.61) |
| copper → other copper miners | 202 | +1.04 | -0.091 (-0.72) | +1.2 % | +0.2 % | +1.1 % (+0.70) | +1.5 % (+1.01) |
| bitcoin → treasury & other miners | 74 | +1.20 | +0.377 (+1.93) | +15.5 % | +2.9 % | +12.6 % (+1.68) | +13.7 % (+1.85) |
| #94 gold → gold miners | 202 | +1.33 | +0.111 (+0.85) | +3.7 % | -1.1 % | +4.7 % (+1.92) | +4.3 % (+1.86) |
| #94 copper → copper miners | 202 | +1.17 | -0.031 (-0.23) | +2.9 % | -0.7 % | +3.5 % (+1.84) | +3.5 % (+1.90) |
| #94 bitcoin → crypto stocks | 145 | +0.79 | +0.394 (+2.40) | +9.4 % | +0.6 % | +8.8 % (+1.45) | +9.7 % (+1.65) |

## 3 Rule (groups A + B): hold lagging producers after the commodity beat SPY, else SPY
| portfolio | CAGR gross | net 0.50 %/side (≈ Yuh) | max drawdown | Sharpe | vs SPY per month net (t) |
|---|--:|--:|--:|--:|--:|
| follow the lagging producer | +27.7 % | +15.5 % | -52 % | +0.85 | +0.5 % (+0.83) |
| all producers always | +15.9 % | +15.9 % | -49 % | +0.61 | +0.5 % (+0.87) |
| SPY | +14.1 % | — | -24 % | +1.00 | — |

Reading: group A is the real test (commodities not looked at before). Group B uses the #94 leaders with stocks not used in #94. Group C only shows whether the #94 hints survive the trading-day alignment.
Caveats: price returns without dividends; current tickers only (survivorship: bankrupt gas/coal/miners missing → biases producers upwards); futures (ALI=F, HG=F) are front-month continuation series with roll jumps; bitcoin closes ≈ 3 h after US stocks even after alignment.