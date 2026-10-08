# Experiment #46 — macro filters against false trend signals (2026-10-08 07:38 UTC)

Macro data: UNRATE ✗, BAA ✗, AAA ✗, GS10 ✗, TB3MS ✗, VIXCLS ✗, CAPE ✓. Haircut α/216 = 0.00023 (placebo p floor ≈ 1/200).
Rule: stress → follow the 3/6/12M trend score; no stress → fully invested. Costs 10 bps per unit turnover. US macro data are applied to non-US indices too.

## S&P 500 (seit 1928)

1928-12 → 2026-10. Stress share: F5 63%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +6.1% | -86% | 0.25 | 0.18 | 0.82 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +6.3% | -49% | 0.35 | 0.30 | 0.66 | 62% | 6.9 | +57% | — | — | — |
| F5 CAPE>median | +6.7% | -76% | 0.30 | 0.27 | 0.66 | 79% | 4.3 | +52% | -0.04 [-0.17, +0.08] | +0.05 [-0.04, +0.16] | 0.384 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 1973–74 | -46% | +6% | -35% |
| 1987 | -28% | -21% | -21% |
| 2000–02 | -46% | -6% | -6% |
| 2008–09 | -53% | -6% | -23% |
| 2020 | -20% | -16% | -16% |
| 2022 | -25% | -11% | -11% |

## S&P 500 Fonds (TR)

1981-01 → 2026-10. Stress share: F5 83%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +11.2% | -51% | 0.53 | 0.37 | 0.93 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +9.7% | -24% | 0.58 | 0.49 | 0.79 | 72% | 5.0 | +61% | — | — | — |
| F5 CAPE>median | +9.8% | -24% | 0.53 | 0.44 | 0.79 | 79% | 4.4 | +65% | -0.05 [-0.18, +0.06] | +0.01 [-0.16, +0.20] | 0.594 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 1987 | -27% | -20% | -20% |
| 2000–02 | -44% | -6% | -6% |
| 2008–09 | -51% | -7% | -24% |
| 2020 | -20% | -16% | -16% |
| 2022 | -24% | -12% | -12% |

## Nasdaq

1972-02 → 2026-10. Stress share: F5 72%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +10.4% | -75% | 0.37 | 0.23 | 0.92 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +10.0% | -36% | 0.45 | 0.32 | 0.89 | 66% | 5.5 | +60% | — | — | — |
| F5 CAPE>median | +10.3% | -41% | 0.42 | 0.31 | 0.89 | 78% | 4.6 | +64% | -0.03 [-0.20, +0.11] | +0.05 [-0.10, +0.22] | 0.486 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 1973–74 | -58% | +7% | -40% |
| 1987 | -30% | -25% | -25% |
| 2000–02 | -74% | -32% | -32% |
| 2008–09 | -52% | -14% | -25% |
| 2020 | -16% | -13% | -13% |
| 2022 | -32% | -14% | -14% |

## DAX

1988-12 → 2026-10. Stress share: F5 98%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +8.1% | -68% | 0.35 | 0.29 | 0.50 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +7.6% | -24% | 0.42 | 0.46 | 0.33 | 65% | 5.8 | +59% | — | — | — |
| F5 CAPE>median | +7.6% | -30% | 0.41 | 0.45 | 0.33 | 66% | 5.8 | +59% | -0.01 [-0.07, +0.04] | +0.06 [-0.14, +0.29] | 0.796 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 2000–02 | -64% | -12% | -12% |
| 2008–09 | -52% | -11% | -29% |
| 2020 | -23% | -13% | -13% |
| 2022 | -24% | -4% | -4% |

## SMI

1991-11 → 2026-10. Stress share: F5 98%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +6.3% | -50% | 0.32 | 0.32 | 0.33 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +5.8% | -27% | 0.36 | 0.59 | -0.09 | 62% | 7.1 | +68% | — | — | — |
| F5 CAPE>median | +5.7% | -27% | 0.34 | 0.56 | -0.09 | 63% | 7.1 | +68% | -0.02 [-0.08, +0.04] | +0.02 [-0.20, +0.28] | 0.893 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 2000–02 | -36% | -4% | -4% |
| 2008–09 | -48% | +0% | -15% |
| 2020 | -12% | -9% | -9% |
| 2022 | -20% | -11% | -11% |

## Nikkei 225

1966-01 → 2026-10. Stress share: F5 74%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +6.5% | -81% | 0.19 | 0.04 | 0.76 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +7.7% | -28% | 0.32 | 0.20 | 0.63 | 54% | 9.7 | +59% | — | — | — |
| F5 CAPE>median | +8.4% | -28% | 0.35 | 0.25 | 0.63 | 66% | 7.6 | +57% | +0.03 [-0.05, +0.12] | +0.15 [-0.01, +0.32] | 0.153 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 1973–74 | -24% | -3% | -14% |
| 1987 | -7% | -7% | -7% |
| 2000–02 | -54% | -14% | -14% |
| 2008–09 | -55% | +1% | -14% |
| 2020 | -18% | -12% | -12% |
| 2022 | -10% | -7% | -7% |

## Schwellenländer (EEM)

2004-04 → 2026-10. Stress share: F5 97%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +8.2% | -60% | 0.40 | 0.54 | 0.29 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +8.4% | -27% | 0.54 | 0.75 | 0.36 | 63% | 7.1 | +69% | — | — | — |
| F5 CAPE>median | +9.2% | -33% | 0.56 | 0.79 | 0.36 | 64% | 7.1 | +69% | +0.02 [-0.06, +0.12] | +0.16 [-0.12, +0.41] | 0.063 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 2008–09 | -60% | -22% | -33% |
| 2020 | -19% | -8% | -8% |
| 2022 | -28% | +1% | +1% |

## Hochzinsanl. (HYG)

2008-04 → 2026-10. Stress share: F5 97%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +4.9% | -29% | 0.38 | 0.50 | 0.36 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +4.0% | -9% | 0.55 | 1.10 | 0.29 | 71% | 7.0 | +69% | — | — | — |
| F5 CAPE>median | +4.5% | -12% | 0.51 | 0.90 | 0.29 | 73% | 6.5 | +67% | -0.04 [-0.17, +0.08] | +0.13 [-0.22, +0.28] | 0.887 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 2008–09 | -27% | -4% | -12% |
| 2020 | -11% | -8% | -8% |
| 2022 | -15% | -4% | -4% |

## Rohstoffe breit (DBC)

2007-02 → 2026-10. Stress share: F5 97%.

| Variant | CAGR | max DD | Sharpe | ≤2012 | >2012 | invested | exits/decade | false exits | ΔSharpe vs trend [95% CI] | ΔSharpe vs B&H [95% CI] | placebo p |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Buy & hold | +2.4% | -75% | 0.14 | 0.18 | 0.12 | 100% | 0.0 | — | — | — | — |
| Trend only (#45) | +4.8% | -44% | 0.32 | 0.18 | 0.40 | 51% | 10.1 | +55% | — | — | — |
| F5 CAPE>median | +5.2% | -39% | 0.34 | 0.26 | 0.40 | 53% | 10.1 | +55% | +0.02 [-0.04, +0.14] | +0.20 [-0.09, +0.48] | 0.123 |

| Crisis | Buy & hold | Trend only (#45) | F5 CAPE>median |
|---|--:|--:|--:|
| 2008–09 | -35% | +8% | -2% |
| 2020 | -23% | +0% | +0% |
| 2022 | +15% | +19% | +19% |
