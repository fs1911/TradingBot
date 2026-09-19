# Pairs Stat-Arb Stress Test — 2026-09-19 07:30 UTC

Economically-sensible pairs only (within index / banks / big-tech / metals / crypto).

**6 pairs:** SPY/XLY(28.0d), QQQ/XLY(37.4d), XLK/XLY(49.0d), DIA/XLY(58.1d), NVDA/AMD(58.6d), XLF/XLY(58.9d)

## Cost sensitivity — where does the edge die?
| Scenario | comm/slip/borrow | OOS ret% | OOS MAR | Walk-fwd (MAR>0.5) |
|---|---|--:|--:|:--:|
| optimistic | 0.02/0.02/0.0% | +12 | 1.08 | 4/12 (33%) |
| base | 0.05/0.03/1.0% | +10 | 0.81 | 4/12 (33%) |
| realistic | 0.05/0.08/3.0% | +6 | 0.44 | 4/12 (33%) |
| harsh | 0.1/0.15/8.0% | -2 | -0.1 | 1/12 (8%) |

## Robustness — is it driven by one lucky pair? (realistic costs)
Full portfolio OOS MAR (realistic costs): **0.44**

| Pair | its OOS ret% | portfolio OOS MAR without it |
|---|--:|--:|
| SPY/XLY | -0 | 0.56 |
| QQQ/XLY | +1 | 0.49 |
| XLK/XLY | -8 | 0.52 |
| DIA/XLY | +11 | 0.35 |
| NVDA/AMD | +33 | -0.11 |
| XLF/XLY | -12 | 0.76 |

If removing any single pair collapses the MAR, the 'edge' rests on one pair (fragile).

Verdict rule: a real, tradeable edge stays positive at REALISTIC costs, keeps a decent walk-forward %, and does not depend on a single pair.