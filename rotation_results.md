# Basket Rotation Edge Test — 2026-08-29 05:28 UTC

Monthly rotation of a tiny basket vs holding each asset alone and equal-weight. Net of costs. MAR = return/|maxDD|. The rotation must beat EVERY hold on MAR, out-of-sample AND in most walk-forward windows, to count as an edge.

## BTC_Gold_Dollar
3 assets: BTC/USD, GLD, UUP · common window 2021-01 → 2026-08 (1418 days)

| Strategy | OOS ret% | OOS maxDD% | OOS MAR | beats all holds? |
|---|--:|--:|--:|:--:|
| Rotation top1 | +174 | -35 | 4.91 | ✅ |
| Rotation dual | +174 | -35 | 4.91 | ✅ |
| Hold BTC/USD | +125 | -53 | 2.35 |  |
| Hold GLD | +122 | -26 | 4.63 |  |
| Hold UUP | -6 | -14 | -0.45 |  |
| Hold equal-weight | +82 | -20 | 4.15 |  |

**Walk-forward top1:** beat all holds in **3/19 windows (16%)** → ❌ not robust
**Walk-forward dual:** beat all holds in **3/19 windows (16%)** → ❌ not robust

A rotation that doesn't beat simply holding the best single asset on MAR isn't an edge — it's a more complicated way to underperform.