# Experiment #94 — second-order chains (does the next link follow?) (2026-11-15 19:35 UTC)

46 symbols loaded, missing: none.

## 1 Primary: pooled slope of the follower's NEXT return on the leader's PAST return (vs SPY)
Control = follower's own past return. Placebo = leaders shuffled between chains. Holm over the 3 horizons.
| horizon | chain-periods | slope on leader | t (clustered) | placebo p | Holm p | without control: slope (t) |
|---|--:|--:|--:|--:|--:|--:|
| 1 M | 2,361 | +0.058 | +1.28 | +0.002 | +0.006 | +0.105 (+2.11) |
| 3 M | 781 | +0.090 | +1.06 | +0.008 | +0.016 | +0.121 (+1.39) |
| 6 M | 383 | +0.077 | +0.52 | +0.232 | +0.232 | +0.120 (+0.99) |

- Sanity check, SAME month (is the link real at all?): slope +0.422 (t +7.04).
- Halves (1 M): ≤ 2017 slope +0.116 (t +1.41); 2018 → +0.017 (t +0.33).

## 2 Per chain (1 M): follower next month vs SPY, after the leader was up / down
| chain | months | same-month slope | next-month slope (t) | next month if leader up & follower lagged | otherwise | difference (t) |
|---|--:|--:|--:|--:|--:|--:|
| AI chips → power producers | 202 | -0.13 | -0.025 (-0.26) | -0.3 % | +0.5 % | -0.8 % (-0.92) |
| AI chips → grid & electrical equipment | 202 | +0.30 | +0.034 (+0.34) | +1.0 % | +0.7 % | +0.2 % (+0.30) |
| AI chips → uranium / nuclear | 202 | +0.22 | -0.168 (-1.27) | -1.7 % | +0.2 % | -1.9 % (-1.35) |
| Nvidia → data-centre REITs | 202 | +0.02 | -0.015 (-0.43) | +0.1 % | +0.3 % | -0.2 % (-0.30) |
| TSMC → chip equipment | 202 | +0.53 | -0.159 (-1.93) | +1.0 % | +1.6 % | -0.7 % (-0.62) |
| Apple → Apple suppliers | 202 | +0.36 | +0.092 (+1.20) | +1.6 % | +0.9 % | +0.8 % (+0.74) |
| Tesla → lithium | 196 | +0.09 | -0.000 (-0.01) | -0.5 % | +0.1 % | -0.6 % (-0.52) |
| gold → gold miners | 202 | +1.33 | +0.111 (+0.84) | +3.7 % | -1.1 % | +4.7 % (+1.92) |
| oil → oil services | 202 | +0.42 | -0.001 (-0.01) | +0.6 % | -0.9 % | +1.6 % (+1.09) |
| bitcoin → crypto stocks | 145 | +0.81 | +0.402 (+2.42) | +10.8 % | +0.1 % | +10.7 % (+1.72) |
| homebuilders → building materials | 202 | +0.48 | -0.012 (-0.18) | +0.1 % | +0.2 % | -0.1 % (-0.07) |
| copper → copper miners | 202 | +1.16 | -0.031 (-0.23) | +2.9 % | -0.7 % | +3.5 % (+1.83) |

## 3 Rule: hold the lagging followers after the leader beat SPY, else SPY (monthly)
| portfolio | CAGR gross | net 0.10 %/side | net 0.50 %/side (≈ Yuh) | max drawdown | Sharpe | vs SPY per month (t) |
|---|--:|--:|--:|--:|--:|--:|
| follow the lagging link | +28.7 % | +26.5 % | +18.0 % | -41 % | +1.02 | +0.5 % (+1.15) net Yuh |
| all followers always | +18.4 % | +18.4 % | +18.3 % | -33 % | +0.83 | +0.4 % (+1.48) net Yuh |
| SPY | +14.3 % | — | — | -24 % | +1.01 | — |

## 4 Case: the AI chains 2023–2024 (✔ = rule would hold the follower next month)
| month | chips vs SPY | power producers: past / signal / next | grid & electrical equipment: past / signal / next | uranium / nuclear: past / signal / next |
|---|--:|---|---|---|
| 2023-01 | +10.5 % | -5.0 % / ✔ / -4.2 % | -3.3 % / ✔ / +12.1 % | +12.8 % / · / -3.2 % |
| 2023-02 | +3.5 % | -4.2 % / ✔ / +2.4 % | +12.1 % / · / -7.1 % | -3.2 % / ✔ / -8.2 % |
| 2023-03 | +6.2 % | +2.4 % / ✔ / -1.4 % | -7.1 % / ✔ / +2.0 % | -8.2 % / ✔ / +1.1 % |
| 2023-04 | -7.7 % | -1.4 % / · / +0.1 % | +2.0 % / · / +10.8 % | +1.1 % / · / -0.1 % |
| 2023-05 | +16.3 % | +0.1 % / ✔ / +1.4 % | +10.8 % / ✔ / +11.2 % | -0.1 % / ✔ / +4.3 % |
| 2023-06 | -1.0 % | +1.4 % / · / +1.1 % | +11.2 % / · / -2.3 % | +4.3 % / · / +5.1 % |
| 2023-07 | +2.2 % | +1.1 % / ✔ / +4.8 % | -2.3 % / ✔ / +19.9 % | +5.1 % / · / +7.1 % |
| 2023-08 | -1.1 % | +4.8 % / · / +6.7 % | +19.9 % / · / -2.2 % | +7.1 % / · / +14.6 % |
| 2023-09 | -2.5 % | +6.7 % / · / +5.8 % | -2.2 % / · / -3.2 % | +14.6 % / · / +3.4 % |
| 2023-10 | -2.0 % | +5.8 % / · / -0.7 % | -3.2 % / · / +2.2 % | +3.4 % / · / +1.0 % |
| 2023-11 | +6.4 % | -0.7 % / ✔ / -0.6 % | +2.2 % / ✔ / +5.5 % | +1.0 % / ✔ / -6.9 % |
| 2023-12 | +5.1 % | -0.6 % / ✔ / +1.2 % | +5.5 % / · / +1.3 % | -6.9 % / ✔ / +8.6 % |
| 2024-01 | +4.7 % | +1.2 % / ✔ / +13.9 % | +1.3 % / ✔ / +13.7 % | +8.6 % / · / -17.5 % |
| 2024-02 | +8.8 % | +13.9 % / · / +13.5 % | +13.7 % / · / +8.2 % | -17.5 % / ✔ / +2.7 % |
| 2024-03 | +2.9 % | +13.5 % / · / +8.8 % | +8.2 % / · / +5.2 % | +2.7 % / ✔ / +6.6 % |
| 2024-04 | -0.8 % | +8.8 % / · / +12.0 % | +5.2 % / · / +0.5 % | +6.6 % / · / +11.8 % |
| 2024-05 | +7.3 % | +12.0 % / · / -11.1 % | +0.5 % / ✔ / -11.4 % | +11.8 % / · / -14.3 % |
| 2024-06 | +4.9 % | -11.1 % / ✔ / -3.6 % | -11.4 % / ✔ / -1.0 % | -14.3 % / ✔ / -6.0 % |
| 2024-07 | -6.5 % | -3.6 % / · / +5.2 % | -1.0 % / · / +0.6 % | -6.0 % / · / -11.8 % |
| 2024-08 | -3.8 % | +5.2 % / · / +19.2 % | +0.6 % / · / +8.7 % | -11.8 % / · / +11.6 % |
| 2024-09 | -1.3 % | +19.2 % / · / +2.1 % | +8.7 % / · / +3.6 % | +11.6 % / · / +9.3 % |
| 2024-10 | -0.6 % | +2.1 % / · / +4.6 % | +3.6 % / · / +7.2 % | +9.3 % / · / +3.7 % |
| 2024-11 | -5.8 % | +4.6 % / · / -9.0 % | +7.2 % / · / -7.5 % | +3.7 % / · / -11.9 % |
| 2024-12 | +2.9 % | -9.0 % / ✔ / +15.4 % | -7.5 % / ✔ / -2.8 % | -11.9 % / ✔ / -1.7 % |

Reading: the question is not whether AI → electricity is a true story (it is), but whether the follower reacts LATER than the leader in a way one could trade after costs.
Caveats: chain list chosen with today's knowledge (hindsight) — the placebo and the non-AI chains guard against that only partly; price returns without dividends; current tickers only (survivorship); several AI chains share the same leader (SMH), so they are not independent.