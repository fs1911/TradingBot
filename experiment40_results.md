# Experiment #40 — trend following across asset classes (2026-09-25 07:47 UTC)

Monthly rebalancing, total-return prices, cash = 13-week T-bill (^IRX), 5 bps per unit turnover. Haircut α/160. Published: MOP 2012.

## Universe: breit (ETFs, ~2006+)

Assets (first date): SPY 1993, EFA 2001, EEM 2003, IWM 2000, VNQ 2004, SHY 2002, IEF 2002, TLT 2002, LQD 2002, HYG 2007, TIP 2003, GLD 2004, SLV 2006, DBC 2006, USO 2006, UNG 2007, DBA 2007, UUP 2007, FXE 2005, FXY 2007, FXF 2006.

Evaluated 1994-02-09 → 2026-09-24.

| Strategy | CAGR | vol | Sharpe (excess) | max DD | corr w/ equity | avg gross |
|---|--:|--:|--:|--:|--:|--:|
| EW buy & hold | +6.8% | 12.5% | 0.39 | -41% | +0.80 | 0.99 |
| Faber GTAA (10m SMA) | +7.0% | 8.9% | 0.53 | -19% | +0.53 | 0.66 |
| TSMOM long/short (10% vol) | +7.5% | 9.3% | 0.56 | -14% | +0.09 | 2.07 |
| TSMOM long-only | +5.3% | 6.5% | 0.44 | -20% | +0.47 | 0.81 |
| SPY buy & hold | +10.9% | 18.8% | 0.51 | -55% | +1.00 | 1.00 |
| 60/40 equity + TSMOM L/S | +10.1% | 12.2% | 0.65 | -31% | +0.95 | — |

| Crisis | EW buy & hold | Faber GTAA (10m SMA) | TSMOM long/short (10% vol) | TSMOM long-only | SPY buy & hold | 60/40 equity + TSMOM L/S |
|---|--:|--:|--:|--:|--:|--:|
| 2000–02 dot-com | -41% | -8% | +16% | -3% | -47% | -26% |
| 2008–09 GFC | -20% | +6% | +29% | +7% | -55% | -28% |
| 2020 Covid | -17% | -4% | -1% | -5% | -33% | -21% |
| 2022 bear | -9% | +1% | +31% | -1% | -24% | -5% |

| Sharpe (excess) | before 2013 | after 2012 |
|---|--:|--:|
| EW buy & hold | 0.47 | 0.25 |
| Faber GTAA (10m SMA) | 0.62 | 0.41 |
| TSMOM long/short (10% vol) | 0.62 | 0.48 |
| TSMOM long-only | 0.64 | 0.06 |
| SPY buy & hold | 0.34 | 0.81 |
| 60/40 equity + TSMOM L/S | 0.50 | 0.90 |

| Test | result |
|---|---|
| TSMOM L/S excess return > 0 | p=0.0, sig after haircut ✅, walk-fwd 54%, regimes+ 3/3, ⚠️ significant but not multiple-testing-proof / regime-fragile |
| Faber GTAA − EW buy & hold | p=0.5545, sig after haircut ❌, walk-fwd 17%, regimes+ 1/3, ❌ no robust edge |
| 60/40 Sharpe − equity Sharpe (bootstrap) | +0.13, 95% CI [+0.03, +0.24], p=0.0047, sig after haircut ❌ |

## Universe: lang (Fonds, ~1987+)

Assets (first date): VFINX 1980, VWIGX 1981, VUSTX 1986, VFITX 1991, VWEHX 1980, VGPMX 1984, VGENX 1984, FRESX 1986.

Evaluated 1981-01-14 → 2026-09-24.

| Strategy | CAGR | vol | Sharpe (excess) | max DD | corr w/ equity | avg gross |
|---|--:|--:|--:|--:|--:|--:|
| EW buy & hold | +9.4% | 10.8% | 0.53 | -45% | +0.79 | 1.00 |
| Faber GTAA (10m SMA) | +8.9% | 6.7% | 0.73 | -18% | +0.55 | 0.72 |
| TSMOM long/short (10% vol) | +12.3% | 10.9% | 0.76 | -33% | +0.15 | 2.26 |
| TSMOM long-only | +8.6% | 6.9% | 0.66 | -30% | +0.47 | 0.90 |
| VFINX buy & hold | +11.2% | 17.9% | 0.47 | -55% | +1.00 | 1.00 |
| 60/40 equity + TSMOM L/S | +12.1% | 12.2% | 0.68 | -30% | +0.93 | — |

| Crisis | EW buy & hold | Faber GTAA (10m SMA) | TSMOM long/short (10% vol) | TSMOM long-only | VFINX buy & hold | 60/40 equity + TSMOM L/S |
|---|--:|--:|--:|--:|--:|--:|
| 1987 crash | -19% | -15% | -26% | -27% | -33% | -30% |
| 2000–02 dot-com | +4% | +14% | +33% | +22% | -47% | -22% |
| 2008–09 GFC | -39% | -0% | +34% | +5% | -55% | -28% |
| 2020 Covid | -25% | -9% | -24% | -15% | -34% | -30% |
| 2022 bear | -19% | -3% | +21% | -8% | -24% | -8% |

| Sharpe (excess) | before 2013 | after 2012 |
|---|--:|--:|
| EW buy & hold | 0.55 | 0.49 |
| Faber GTAA (10m SMA) | 0.76 | 0.66 |
| TSMOM long/short (10% vol) | 0.84 | 0.57 |
| TSMOM long-only | 0.71 | 0.54 |
| VFINX buy & hold | 0.33 | 0.81 |
| 60/40 equity + TSMOM L/S | 0.60 | 0.87 |

| Test | result |
|---|---|
| TSMOM L/S excess return > 0 | p=0.0, sig after haircut ✅, walk-fwd 58%, regimes+ 3/3, ⚠️ significant but not multiple-testing-proof / regime-fragile |
| Faber GTAA − EW buy & hold | p=0.7885, sig after haircut ❌, walk-fwd 18%, regimes+ 0/3, ❌ no robust edge |
| 60/40 Sharpe − equity Sharpe (bootstrap) | +0.22, 95% CI [+0.09, +0.35], p=0.0003, sig after haircut ❌ |
