# Experiment #10 — GLD/GDX robustness + Dollar ratios (2026-09-19 10:31 UTC)

## Part A — GLD/GDX parameter robustness (overfit check)
**base costs:** 15/27 parameter combos survive (OOS+, WF≥50%) · median OOS MAR 1.01 → ⚠️ works only in part of the grid
**realistic costs:** 5/27 parameter combos survive (OOS+, WF≥50%) · median OOS MAR 0.67 → ❌ overfit (lucky params only)

| z-win | entry | exit | OOS ret% | OOS MAR | Walk-fwd |
|--:|--:|--:|--:|--:|:--:|
| 40 | 1.5 | 0.0 | +11 | 1.0 | 9/21 (43%) |
| 40 | 1.5 | 0.5 | +10 | 0.86 | 9/21 (43%) |
| 40 | 1.5 | 1.0 | +1 | 0.06 | 5/21 (24%) |
| 40 | 2.0 | 0.0 | +15 | 1.41 | 9/21 (43%) |
| 40 | 2.0 | 0.5 | +15 | 1.37 | 8/21 (38%) |
| 40 | 2.0 | 1.0 | +6 | 0.56 | 11/21 (52%) |
| 40 | 2.5 | 0.0 | -9 | -0.6 | 5/21 (24%) |
| 40 | 2.5 | 0.5 | -9 | -0.72 | 8/21 (38%) |
| 40 | 2.5 | 1.0 | -9 | -0.7 | 12/21 (57%) |
| 60 | 1.5 | 0.0 | +20 | 1.45 | 8/21 (38%) |
| 60 | 1.5 | 0.5 | +11 | 0.99 | 8/21 (38%) |
| 60 | 1.5 | 1.0 | +0 | 0.02 | 8/21 (38%) |
| 60 | 2.0 | 0.0 | +20 | 1.54 | 8/21 (38%) |
| 60 | 2.0 | 0.5 | +18 | 1.92 | 11/21 (52%) |
| 60 | 2.0 | 1.0 | +18 | 1.89 | 12/21 (57%) |
| 60 | 2.5 | 0.0 | +1 | 0.06 | 9/21 (43%) |
| 60 | 2.5 | 0.5 | +0 | 0.01 | 9/21 (43%) |
| 60 | 2.5 | 1.0 | -1 | -0.16 | 11/21 (52%) |
| 90 | 1.5 | 0.0 | +13 | 0.8 | 6/21 (29%) |
| 90 | 1.5 | 0.5 | +17 | 1.39 | 7/21 (33%) |
| 90 | 1.5 | 1.0 | +4 | 0.33 | 9/21 (43%) |
| 90 | 2.0 | 0.0 | +11 | 0.67 | 8/21 (38%) |
| 90 | 2.0 | 0.5 | +21 | 2.22 | 13/21 (62%) |
| 90 | 2.0 | 1.0 | +11 | 1.14 | 12/21 (57%) |
| 90 | 2.5 | 0.0 | -7 | -0.41 | 5/21 (24%) |
| 90 | 2.5 | 0.5 | +0 | 0.02 | 6/21 (29%) |
| 90 | 2.5 | 1.0 | +2 | 0.25 | 10/21 (48%) |

## Part B — Dollar-index ratios (commodity vs USD strength)
_Note: GLD etc. are already priced in USD, so 'X/USD' is a directional bet. The real market-neutral 'vs dollar' spread uses the dollar-index ETF (UUP)._

| Ratio | Scenario | OOS ret% | OOS MAR | Walk-fwd | Verdict |
|---|---|--:|--:|:--:|---|
| GLD/UUP | optimistic | -12 | -0.55 | 4/21 (19%) | ❌ no robust edge |
| GLD/UUP | base | -15 | -0.61 | 3/21 (14%) | ❌ no robust edge |
| GLD/UUP | realistic | -19 | -0.69 | 2/21 (10%) | ❌ no robust edge |
| GLD/UUP | harsh | -27 | -0.81 | 0/21 (0%) | ❌ no robust edge |
| SLV/UUP | optimistic | -0 | -0.01 | 11/21 (52%) | ❌ no robust edge |
| SLV/UUP | base | -3 | -0.07 | 11/21 (52%) | ❌ no robust edge |
| SLV/UUP | realistic | -7 | -0.17 | 11/21 (52%) | ❌ no robust edge |
| SLV/UUP | harsh | -16 | -0.37 | 11/21 (52%) | ❌ no robust edge |
| USO/UUP | optimistic | -8 | -0.26 | 10/21 (48%) | ❌ no robust edge |
| USO/UUP | base | -11 | -0.32 | 8/21 (38%) | ❌ no robust edge |
| USO/UUP | realistic | -14 | -0.43 | 7/21 (33%) | ❌ no robust edge |
| USO/UUP | harsh | -22 | -0.65 | 4/21 (19%) | ❌ no robust edge |
| GDX/UUP | optimistic | +16 | 0.54 | 8/21 (38%) | ❌ no robust edge |
| GDX/UUP | base | +12 | 0.41 | 8/21 (38%) | ❌ no robust edge |
| GDX/UUP | realistic | +7 | 0.21 | 8/21 (38%) | ❌ no robust edge |
| GDX/UUP | harsh | -6 | -0.17 | 7/21 (33%) | ❌ no robust edge |

Verdict rule: GLD/GDX is only real if it survives across MOST of the parameter grid at realistic costs — not just at the single combo used in experiment #9.