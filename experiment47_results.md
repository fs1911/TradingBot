# Experiment #47 — market signal applied to single stocks (2026-10-08 08:55 UTC)

Macro sources: UNRATE: DBnomics (BLS); credit: Yahoo VWEHX/VFITX (high-yield vs Treasury fund, proxy); curve: Yahoo ^TNX/^IRX; VIX: Yahoo ^VIX.
Variants: B&H; own 3/6/12M trend (#45); home-index trend applied to the stock; index trend only under macro stress (≥2 of unemployment/credit/curve, #46). Monthly, 10 bps. Survivorship: today's constituents.

## USA (92 Large Caps)

92 stocks; market invested 71% (trend) / 84% (trend+macro) of months.

| Variant | median CAGR | median max DD | median Sharpe | Sharpe ≤2012 | Sharpe >2012 | stocks with smaller DD than B&H | stocks with higher Sharpe than B&H |
|---|--:|--:|--:|--:|--:|--:|--:|
| B&H | +13.9% | -67% | 0.53 | 0.48 | 0.56 | — | — |
| Own trend | +9.4% | -41% | 0.45 | 0.44 | 0.44 | 90/92 | 26/92 |
| Market trend | +10.4% | -49% | 0.48 | 0.50 | 0.46 | 81/92 | 28/92 |
| Market + macro | +13.5% | -53% | 0.54 | 0.56 | 0.50 | 74/92 | 64/92 |

Equal-weight portfolio of these stocks:
| Variant | CAGR | max DD | Sharpe | 2000–02 | 2008–09 | 2011 | 2018 Q4 | 2020 | 2022 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| B&H | +19.5% | -46% | 1.02 | -21% | -46% | -16% | -13% | -19% | -23% |
| Own trend | +13.3% | -14% | 1.12 | -8% | -14% | -8% | -8% | -10% | -10% |
| Market trend | +14.4% | -18% | 1.08 | +2% | -5% | -10% | -10% | -15% | -9% |
| Market + macro | +18.1% | -23% | 1.13 | +2% | -5% | -16% | -13% | -15% | -23% |

Placebo (market weights shifted, same k for all stocks): median Sharpe gain vs B&H market trend -0.036 (p=0.250), market+macro +0.030 (p=0.010).

## Schweiz (SMI)

24 stocks; market invested 62% (trend) / 83% (trend+macro) of months.

| Variant | median CAGR | median max DD | median Sharpe | Sharpe ≤2012 | Sharpe >2012 | stocks with smaller DD than B&H | stocks with higher Sharpe than B&H |
|---|--:|--:|--:|--:|--:|--:|--:|
| B&H | +9.6% | -66% | 0.44 | 0.43 | 0.50 | — | — |
| Own trend | +9.6% | -33% | 0.47 | 0.51 | 0.49 | 24/24 | 15/24 |
| Market trend | +7.8% | -37% | 0.41 | 0.66 | 0.29 | 24/24 | 13/24 |
| Market + macro | +10.6% | -47% | 0.51 | 0.69 | 0.41 | 22/24 | 21/24 |

Equal-weight portfolio of these stocks:
| Variant | CAGR | max DD | Sharpe | 2000–02 | 2008–09 | 2011 | 2018 Q4 | 2020 | 2022 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| B&H | +13.5% | -51% | 0.68 | -30% | -51% | -21% | -14% | -15% | -26% |
| Own trend | +10.3% | -20% | 0.79 | +3% | -16% | -10% | -7% | -10% | -12% |
| Market trend | +9.7% | -25% | 0.67 | +1% | -2% | -8% | -8% | -11% | -13% |
| Market + macro | +13.2% | -33% | 0.81 | +8% | -2% | -21% | -14% | -11% | -26% |

Placebo (market weights shifted, same k for all stocks): median Sharpe gain vs B&H market trend +0.010 (p=0.100), market+macro +0.087 (p=<0.010 (floor)).

## Deutschland (DAX)

30 stocks; market invested 65% (trend) / 84% (trend+macro) of months.

| Variant | median CAGR | median max DD | median Sharpe | Sharpe ≤2012 | Sharpe >2012 | stocks with smaller DD than B&H | stocks with higher Sharpe than B&H |
|---|--:|--:|--:|--:|--:|--:|--:|
| B&H | +6.8% | -75% | 0.32 | 0.31 | 0.39 | — | — |
| Own trend | +6.1% | -42% | 0.33 | 0.33 | 0.32 | 30/30 | 20/30 |
| Market trend | +7.0% | -47% | 0.35 | 0.40 | 0.28 | 30/30 | 18/30 |
| Market + macro | +9.1% | -56% | 0.41 | 0.50 | 0.29 | 26/30 | 27/30 |

Equal-weight portfolio of these stocks:
| Variant | CAGR | max DD | Sharpe | 2000–02 | 2008–09 | 2011 | 2018 Q4 | 2020 | 2022 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| B&H | +11.1% | -58% | 0.53 | -41% | -57% | -24% | -14% | -26% | -19% |
| Own trend | +8.8% | -19% | 0.72 | -9% | -13% | -11% | -3% | -11% | -5% |
| Market trend | +9.0% | -21% | 0.65 | +4% | -12% | -15% | -1% | -14% | -0% |
| Market + macro | +11.9% | -27% | 0.70 | +5% | -12% | -24% | -14% | -14% | -19% |

Placebo (market weights shifted, same k for all stocks): median Sharpe gain vs B&H market trend +0.034 (p=0.060), market+macro +0.073 (p=0.030).

**Summary:** USA (92 Large Caps): market trend ΔSharpe -0.04 (p 0.250), +macro +0.03 (p 0.010); Schweiz (SMI): market trend ΔSharpe +0.01 (p 0.100), +macro +0.09 (p 0.010); Deutschland (DAX): market trend ΔSharpe +0.03 (p 0.060), +macro +0.07 (p 0.030).