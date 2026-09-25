# Experiment #36 — calendar anomalies over ~95 years, before vs after publication (2026-09-25 06:19 UTC)

S&P 500 daily, 1928-01-03 → 2026-09-24 (24798 days, price index). Values: mean daily return in the window vs outside (basis points). Haircut: two-sided p < 0.00037 (α/135).

| Anomaly | published | BEFORE: in / out bp, t | AFTER: in / out bp, t | LAST 20y: in / out bp, t | after pub. sig? |
|---|--:|---|---|---|:--:|
| turn-of-month (last+first 3 days) | 1987 | +15.2 / -0.5, +6.26 | +8.5 / +3.1, +1.86 | +5.0 / +4.0, +0.23 | ❌ |
| monday (weekend effect) | 1980 | -12.9 / +5.8, -6.05 | +2.0 / +4.6, -0.88 | +2.2 / +4.6, -0.51 | ❌ |
| january | 1976 | +6.5 / +1.8, +1.31 | +4.1 / +4.0, +0.03 | +0.9 / +4.5, -0.63 | ❌ |
| pre-holiday | 1988 | +33.5 / +1.2, +6.43 | +10.4 / +3.9, +1.28 | +14.6 / +3.8, +1.53 | ❌ |
| halloween (Nov–Apr) | 2002 | +4.1 / +1.9, +1.28 | +5.1 / +3.6, +0.51 | +5.1 / +3.3, +0.54 | ❌ |

## Strategy: invested only inside the window (5 bps/switch, 0% cash) vs buy & hold
| Rule | period | time invested | CAGR | Sharpe | max DD |
|---|---|--:|--:|--:|--:|
| buy & hold | full | 100% | +6.4% | 0.42 | -86% |
| turn-of-month (last+first 3 days) | full | 19% | +4.7% | 0.60 | -33% |
| monday (weekend effect) | full | 19% | -8.0% | -0.82 | -100% |
| january | full | 8% | +1.0% | 0.23 | -26% |
| pre-holiday | full | 4% | +1.4% | 0.42 | -16% |
| halloween (Nov–Apr) | full | 49% | +4.4% | 0.40 | -72% |
| buy & hold | since 2007 | 100% | +9.0% | 0.54 | -57% |
| turn-of-month (last+first 3 days) | since 2007 | 19% | +0.9% | 0.14 | -21% |
| monday (weekend effect) | since 2007 | 19% | -4.1% | -0.39 | -66% |
| january | since 2007 | 8% | -0.0% | 0.02 | -22% |
| pre-holiday | since 2007 | 4% | +0.4% | 0.15 | -12% |
| halloween (Nov–Apr) | since 2007 | 49% | +5.3% | 0.43 | -38% |

---
**Summary:** significant AFTER publication (same sign, haircut): 0/5 (none). Post-publication effect size as % of pre-publication: turn-of-month 34%, monday 14%, january 2%, pre-holiday 20%, halloween 69%.