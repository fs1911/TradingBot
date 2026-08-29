# Volatility Risk-Premium Edge Test — 2026-08-29 10:30 UTC

Harvest the vol premium via a short-VIX ETF. The premium is REAL but is compensation for crash risk — watch 'worst day' and maxDD. MAR = return/|maxDD|. The trend-filtered variant tries to step aside before blow-ups.

Instrument: **SVXY** (short-vol) · 1531 daily bars 2020-07 → 2026-08

| Strategy | total ret% | maxDD% | MAR | worst 1-day% | %inMkt |
|---|--:|--:|--:|--:|--:|
| Short-vol naive | +87 | -70 | 1.24 | -49.5 | 100% |
| Short-vol trend>50d | -41 | -67 | -0.61 | -49.5 | 68% |
| Hold SPY | +183 | -25 | 7.22 | -5.8 |  |

**Walk-forward (trend short-vol vs SPY):** beat in **5/21 windows (24%)** → ❌ not robust

| Window | Vol ret% | Vol MAR | Vol worstDay% | SPY ret% | SPY MAR | wins? |
|---|--:|--:|--:|--:|--:|:--:|
| 2020-07 → 2021-07 | -2 | -0.07 | -10.6 | +62 | 6.37 | — |
| 2020-10 → 2021-10 | -10 | -0.42 | -10.6 | +31 | 5.74 | — |
| 2021-01 → 2022-01 | -27 | -0.91 | -14.2 | +14 | 1.74 | — |
| 2021-04 → 2022-04 | -39 | -0.95 | -14.2 | +3 | 0.21 | — |
| 2021-07 → 2022-07 | -31 | -0.85 | -14.2 | -11 | -0.49 | — |
| 2021-10 → 2022-10 | -28 | -0.83 | -14.2 | -16 | -0.65 | — |
| 2022-01 → 2023-01 | +4 | 0.17 | -6.6 | -9 | -0.4 | ✅ |
| 2022-04 → 2023-04 | +28 | 2.98 | -5.3 | -6 | -0.33 | ✅ |
| 2022-07 → 2023-07 | +64 | 6.97 | -5.3 | +16 | 0.93 | ✅ |
| 2022-10 → 2023-10 | +50 | 3.81 | -6.2 | +10 | 1.17 | ✅ |
| 2023-01 → 2024-01 | +46 | 3.54 | -6.2 | +22 | 2.12 | ✅ |
| 2023-04 → 2024-04 | -27 | -0.51 | -49.5 | +26 | 2.5 | — |
| 2023-07 → 2024-07 | -48 | -0.86 | -49.5 | +20 | 1.99 | — |
| 2023-10 → 2024-10 | -43 | -0.77 | -49.5 | +39 | 4.6 | — |
| 2024-01 → 2025-01 | -60 | -0.96 | -49.5 | +23 | 2.79 | — |
| 2024-04 → 2025-04 | -26 | -0.88 | -8.6 | +9 | 0.48 | — |
| 2024-07 → 2025-07 | -14 | -0.51 | -8.6 | +16 | 0.84 | — |
| 2024-10 → 2025-10 | -13 | -0.45 | -8.6 | +19 | 0.99 | — |
| 2025-01 → 2026-01 | +6 | 0.42 | -6.4 | +15 | 0.79 | — |
| 2025-05 → 2026-05 | +6 | 0.43 | -6.4 | +30 | 3.29 | — |
| 2025-08 → 2026-08 | +11 | 0.79 | -6.4 | +20 | 2.18 | — |

The vol premium is real, but a big negative 'worst day' / maxDD is the crash risk you are paid to carry. An edge must beat buy-and-hold on MAR across MOST windows AND keep the tail survivable.