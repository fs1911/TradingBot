# Experiment #48 — insider purchases as a buy signal (2026-10-08 12:08 UTC)

SEC purchases parsed: 786,726 (2006-01 → 2026-03); quarters failed: 3 (e.g. 2026q2: <HTTPError 404: 'Not Found'>).

## Signal A cluster
Events: 11,752; with price data: 2,825 (24% — missing tickers are mostly delisted → survivorship bias upward).

| Horizon | n | mean excess vs SPY | median | hit rate (>SPY) | control mean (same stocks, random dates) | event − control [95% CI] |
|---|--:|--:|--:|--:|--:|--:|
| 1M | 2,825 | -0.02% | -0.39% | 48% | -0.10% | +0.08% [-0.47, +0.65] |
| 3M | 2,825 | +0.24% | -1.16% | 47% | -0.53% | +0.77% [-0.25, +1.77] |
| 6M | 2,825 | -0.90% | -2.67% | 45% | -0.51% | -0.39% [-1.77, +1.12] |
| 12M | 2,740 | +0.08% | -5.28% | 43% | -1.32% | +1.39% [-0.61, +3.46] |

Calendar-time portfolio (hold 6 months, EW, minus SPY): -2.5% p.a., t=-0.96, Sharpe -0.21, one-sided p=0.16907 ❌ (α/224); ≤2015 -0.9% (t -0.3), >2015 -4.0% (t -0.9); months 248.

## Signal B large
Events: 12,563; with price data: 2,880 (23% — missing tickers are mostly delisted → survivorship bias upward).

| Horizon | n | mean excess vs SPY | median | hit rate (>SPY) | control mean (same stocks, random dates) | event − control [95% CI] |
|---|--:|--:|--:|--:|--:|--:|
| 1M | 2,880 | -0.07% | -0.63% | 47% | +0.04% | -0.11% [-0.77, +0.57] |
| 3M | 2,880 | -0.76% | -1.91% | 44% | -0.03% | -0.73% [-1.78, +0.49] |
| 6M | 2,880 | -2.29% | -3.54% | 43% | +0.02% | -2.31% [-3.71, -0.91] |
| 12M | 2,746 | -3.92% | -8.03% | 41% | -0.65% | -3.27% [-5.51, -0.99] |

Calendar-time portfolio (hold 6 months, EW, minus SPY): +1.4% p.a., t=0.28, Sharpe 0.06, one-sided p=0.39163 ❌ (α/224); ≤2015 +8.2% (t 0.9), >2015 -4.9% (t -1.1); months 248.