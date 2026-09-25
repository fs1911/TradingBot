# Experiment #41 — hardening multi-asset trend following (2026-09-25 08:43 UTC)

Cash = 13-week T-bill (^IRX); haircut α/165.

## Universe: breit (ETFs, ~2006+)

Evaluated 1994-02-09 → 2026-09-24. Equity (SPY) excess Sharpe 0.51.

### 1 — Signal horizon (5 bps, no borrow fee, gross ≤ 3)
| Signal | CAGR | Sharpe (excess) | max DD | p | sig |
|---|--:|--:|--:|--:|:--:|
| 1m | +3.3% | 0.13 | -33% | 0.2265 | ❌ |
| 3m | +5.2% | 0.31 | -18% | 0.0385 | ❌ |
| 6m | +6.2% | 0.42 | -21% | 0.009 | ❌ |
| 12m | +7.5% | 0.56 | -14% | 0.0 | ✅ |
| blend 3/6/12 | +7.4% | 0.51 | -23% | 0.0005 | ❌ |
| blend 1/3/12 | +6.5% | 0.43 | -19% | 0.007 | ❌ |

### 2 — Costs (12m signal, gross ≤ 3): Sharpe (excess) / CAGR
| turnover cost \ borrow | 0% | 2% | 5% |
|---|---|---|---|
| 5 bps | 0.56 / +7.5% | 0.40 / +5.9% | 0.15 / +3.5% |
| 10 bps | 0.52 / +7.1% | 0.36 / +5.5% | 0.11 / +3.1% |
| 20 bps | 0.44 / +6.3% | 0.27 / +4.7% | 0.03 / +2.3% |

### 3 — Leverage cap (12m, 10 bps, 2% borrow)
| gross cap | CAGR | vol | Sharpe (excess) | max DD |
|---|--:|--:|--:|--:|
| 1.0× | +4.4% | 6.6% | 0.31 | -14% |
| 1.5× | +4.7% | 7.4% | 0.33 | -14% |
| 2.0× | +5.1% | 8.1% | 0.35 | -15% |
| 3.0× | +5.5% | 9.3% | 0.36 | -21% |

### 4 — Realistic version (blend 3/6/12, 10 bps, 2% borrow, gross ≤ 2)
| Portfolio | CAGR | vol | Sharpe (excess) | max DD | Sharpe ≤2012 | Sharpe >2012 |
|---|--:|--:|--:|--:|--:|--:|
| TSMOM realistic | +5.0% | 8.8% | 0.31 | -23% | 0.45 | 0.03 |
| SPY | +10.9% | 18.8% | 0.51 | -55% | 0.34 | 0.81 |
| 60/40 equity + TSMOM | +9.1% | 11.6% | 0.59 | -28% | 0.47 | 0.81 |

Rigor (TSMOM realistic excess): p=0.035, sig after haircut ❌, walk-fwd 47%, regimes+ 2/3, ❌ no robust edge. 60/40 Sharpe gain +0.08 [-0.03, +0.18], p=0.0647 ❌.

### 5 — Dry spells
| Portfolio | longest under water | worst 3y return | % of 3y windows < 0 | worst 3y Sharpe |
|---|--:|--:|--:|--:|
| TSMOM realistic | 3.9 y | -20% | 8% | -1.46 |
| SPY | 6.6 y | -43% | 17% | -0.88 |
| 60/40 equity + TSMOM | 3.3 y | -20% | 7% | -0.83 |

### 6 — Placebo (100 random-sign runs, identical machinery, 12m, 5 bps)
Real trend Sharpe 0.56; placebo median -0.19, 95th pct 0.05, max 0.27; share of placebo ≥ real: 0.00.

**Summary breit (ETFs, ~2006+):** horizons significant 1/6; cost cells with positive excess Sharpe 9/9; realistic version sig no; placebo p=0.00.

## Universe: lang (Fonds, ~1987+)

Evaluated 1981-01-14 → 2026-09-24. Equity (VFINX) excess Sharpe 0.47.

### 1 — Signal horizon (5 bps, no borrow fee, gross ≤ 3)
| Signal | CAGR | Sharpe (excess) | max DD | p | sig |
|---|--:|--:|--:|--:|:--:|
| 1m | +7.9% | 0.41 | -26% | 0.006 | ❌ |
| 3m | +9.1% | 0.51 | -18% | 0.0005 | ❌ |
| 6m | +10.6% | 0.65 | -23% | 0.0005 | ❌ |
| 12m | +12.2% | 0.77 | -28% | 0.0 | ✅ |
| blend 3/6/12 | +12.1% | 0.75 | -30% | 0.0 | ✅ |
| blend 1/3/12 | +11.5% | 0.70 | -21% | 0.0 | ✅ |

### 2 — Costs (12m signal, gross ≤ 3): Sharpe (excess) / CAGR
| turnover cost \ borrow | 0% | 2% | 5% |
|---|---|---|---|
| 5 bps | 0.77 / +12.2% | 0.63 / +10.6% | 0.44 / +8.3% |
| 10 bps | 0.73 / +11.7% | 0.59 / +10.1% | 0.39 / +7.8% |
| 20 bps | 0.64 / +10.7% | 0.51 / +9.1% | 0.31 / +6.8% |

### 3 — Leverage cap (12m, 10 bps, 2% borrow)
| gross cap | CAGR | vol | Sharpe (excess) | max DD |
|---|--:|--:|--:|--:|
| 1.0× | +6.3% | 5.2% | 0.46 | -17% |
| 1.5× | +7.5% | 7.3% | 0.50 | -24% |
| 2.0× | +8.7% | 8.9% | 0.54 | -29% |
| 3.0× | +10.1% | 10.7% | 0.59 | -30% |

### 4 — Realistic version (blend 3/6/12, 10 bps, 2% borrow, gross ≤ 2)
| Portfolio | CAGR | vol | Sharpe (excess) | max DD | Sharpe ≤2012 | Sharpe >2012 |
|---|--:|--:|--:|--:|--:|--:|
| TSMOM realistic | +8.9% | 9.4% | 0.54 | -30% | 0.60 | 0.38 |
| VFINX | +11.2% | 17.9% | 0.47 | -55% | 0.33 | 0.81 |
| 60/40 equity + TSMOM | +10.8% | 11.5% | 0.61 | -30% | 0.51 | 0.86 |

Rigor (TSMOM realistic excess): p=0.001, sig after haircut ❌, walk-fwd 52%, regimes+ 3/3, ⚠️ significant but not multiple-testing-proof / regime-fragile. 60/40 Sharpe gain +0.15 [+0.03, +0.26], p=0.0067 ❌.

### 5 — Dry spells
| Portfolio | longest under water | worst 3y return | % of 3y windows < 0 | worst 3y Sharpe |
|---|--:|--:|--:|--:|
| TSMOM realistic | 4.0 y | -15% | 6% | -1.06 |
| VFINX | 6.1 y | -44% | 12% | -0.92 |
| 60/40 equity + TSMOM | 3.3 y | -23% | 6% | -0.98 |

### 6 — Placebo (100 random-sign runs, identical machinery, 12m, 5 bps)
Real trend Sharpe 0.77; placebo median -0.15, 95th pct 0.11, max 0.36; share of placebo ≥ real: 0.00.

**Summary lang (Fonds, ~1987+):** horizons significant 3/6; cost cells with positive excess Sharpe 9/9; realistic version sig no; placebo p=0.00.
