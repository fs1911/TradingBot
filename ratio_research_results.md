# Commodity-Ratio Research — 2026-09-19 10:23 UTC

Mean reversion of economically-linked commodity ratios (fixed 1:1 legs, market-neutral). Net of costs incl. short borrow. A real edge survives OOS, most walk-forward windows, AND realistic costs.

## GLD / SLV
| Scenario | comm/slip/borrow | OOS ret% | OOS MAR | Walk-fwd | Verdict |
|---|---|--:|--:|:--:|---|
| optimistic | 0.02/0.02/0.0% | +4 | 0.18 | 7/21 (33%) | ❌ no robust edge |
| base | 0.05/0.03/1.0% | +2 | 0.07 | 7/21 (33%) | ❌ no robust edge |
| realistic | 0.05/0.08/3.0% | -3 | -0.1 | 4/21 (19%) | ❌ no robust edge |
| harsh | 0.1/0.15/8.0% | -12 | -0.42 | 1/21 (5%) | ❌ no robust edge |

## PPLT / PALL
| Scenario | comm/slip/borrow | OOS ret% | OOS MAR | Walk-fwd | Verdict |
|---|---|--:|--:|:--:|---|
| optimistic | 0.02/0.02/0.0% | +48 | 5.62 | 10/19 (53%) | ⚠️ marginal / regime-dependent |
| base | 0.05/0.03/1.0% | +46 | 5.22 | 9/19 (47%) | ⚠️ marginal / regime-dependent |
| realistic | 0.05/0.08/3.0% | +41 | 4.58 | 9/19 (47%) | ⚠️ marginal / regime-dependent |
| harsh | 0.1/0.15/8.0% | +31 | 2.79 | 7/19 (37%) | ❌ no robust edge |

## GLD / USO
| Scenario | comm/slip/borrow | OOS ret% | OOS MAR | Walk-fwd | Verdict |
|---|---|--:|--:|:--:|---|
| optimistic | 0.02/0.02/0.0% | -38 | -0.88 | 4/21 (19%) | ❌ no robust edge |
| base | 0.05/0.03/1.0% | -39 | -0.88 | 3/21 (14%) | ❌ no robust edge |
| realistic | 0.05/0.08/3.0% | -42 | -0.9 | 3/21 (14%) | ❌ no robust edge |
| harsh | 0.1/0.15/8.0% | -47 | -0.92 | 3/21 (14%) | ❌ no robust edge |

## GLD / GDX
| Scenario | comm/slip/borrow | OOS ret% | OOS MAR | Walk-fwd | Verdict |
|---|---|--:|--:|:--:|---|
| optimistic | 0.02/0.02/0.0% | +26 | 2.95 | 16/21 (76%) | ✅ survives |
| base | 0.05/0.03/1.0% | +23 | 2.54 | 14/21 (67%) | ✅ survives |
| realistic | 0.05/0.08/3.0% | +18 | 1.92 | 11/21 (52%) | ⚠️ marginal / regime-dependent |
| harsh | 0.1/0.15/8.0% | +7 | 0.66 | 4/21 (19%) | ❌ no robust edge |

## SLV / GDX
| Scenario | comm/slip/borrow | OOS ret% | OOS MAR | Walk-fwd | Verdict |
|---|---|--:|--:|:--:|---|
| optimistic | 0.02/0.02/0.0% | +7 | 0.37 | 8/21 (38%) | ❌ no robust edge |
| base | 0.05/0.03/1.0% | +5 | 0.23 | 7/21 (33%) | ❌ no robust edge |
| realistic | 0.05/0.08/3.0% | +0 | 0.01 | 7/21 (33%) | ❌ no robust edge |
| harsh | 0.1/0.15/8.0% | -10 | -0.39 | 6/21 (29%) | ❌ no robust edge |

---
**Summary:** no ratio survived at realistic costs across the walk-forward.