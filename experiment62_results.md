# Experiment #62 — machine learning on company data (2026-10-28 08:33 UTC)

Panel: 25,341 firm-years, 2009–2025 (formation June of the following year), 1471 firms per year. Features ranked per year; walk-forward, expanding window ≥ 5 years. Bonferroni α/300 → |t| ≳ 3.7.

| model | test years | rank IC (mean) | IC t | years IC > 0 | top quintile − universe p.a. | t | years top beats universe |
|---|--:|--:|--:|--:|--:|--:|--:|
| H1 buybacks | 11 | +0.049 | +3.08 | 9/11 | +2.8 % | +2.68 | 11/12 |
| H2 quality | 11 | -0.000 | -0.00 | 5/11 | +0.5 % | +0.33 | 6/12 |
| H3 human rule | 11 | +0.027 | +0.73 | 7/11 | -1.3 % | -0.74 | 6/12 |
| M1 ridge | 11 | -0.002 | -0.05 | 6/11 | -1.5 % | -1.09 | 4/12 |
| M2 boosted trees | 11 | +0.021 | +0.68 | 7/11 | -0.0 % | -0.03 | 5/12 |
| P placebo (shuffled) | 11 | -0.001 | -0.05 | 6/11 | -1.2 % | -1.01 | 5/12 |

Boosted trees − human rule, rank IC difference: -0.006 (t -0.15, 4/11 years better).

Rank IC = correlation between a model's ranking and the realised 12-month return ranking (0 = no information; +0.05 is already considered useful in practice). The placebo shows what fitting noise looks like out-of-sample.