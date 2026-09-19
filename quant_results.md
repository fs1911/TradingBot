# Quant Research — 2026-09-19 07:23 UTC

## Market structure (is any asset non-random?)
Hurst <0.45 = mean-reverting · >0.55 = trending · ~0.5 = random walk (no edge).

| Symbol | Hurst | VarRatio | lag1 autocorr | verdict |
|---|--:|--:|--:|---|
| SPY | 0.42 | 0.93 | -0.024 | mean-reverting |
| QQQ | 0.45 | 0.92 | -0.037 | random walk |
| IWM | 0.46 | 0.95 | -0.02 | random walk |
| DIA | 0.41 | 0.97 | -0.002 | mean-reverting |
| XLF | 0.44 | 1.02 | 0.011 | mean-reverting |
| XLK | 0.5 | 0.95 | -0.023 | random walk |
| XLE | 0.46 | 1.0 | 0.018 | random walk |
| XLY | 0.48 | 1.0 | 0.006 | random walk |
| XLV | 0.44 | 1.0 | 0.007 | mean-reverting |
| XLI | 0.43 | 1.02 | -0.002 | mean-reverting |
| XLP | 0.41 | 0.99 | -0.013 | mean-reverting |
| XLU | 0.49 | 1.05 | 0.011 | random walk |
| JPM | 0.44 | 0.94 | -0.001 | mean-reverting |
| BAC | 0.47 | 1.09 | 0.044 | random walk |
| C | 0.48 | 1.0 | 0.014 | random walk |
| WFC | 0.45 | 0.99 | -0.001 | mean-reverting |
| GS | 0.46 | 1.02 | 0.035 | random walk |
| MS | 0.46 | 1.01 | 0.041 | random walk |
| AAPL | 0.37 | 1.02 | -0.019 | mean-reverting |
| MSFT | 0.45 | 0.92 | 0.002 | random walk |
| GOOGL | 0.5 | 0.96 | -0.017 | random walk |
| META | 0.5 | 0.93 | -0.011 | random walk |
| NVDA | 0.47 | 0.95 | -0.017 | random walk |
| AMD | 0.52 | 0.93 | -0.024 | random walk |
| GLD | 0.48 | 0.95 | -0.012 | random walk |
| SLV | 0.46 | 0.88 | -0.025 | random walk |
| GDX | 0.47 | 1.04 | -0.024 | random walk |
| PPLT | 0.52 | 1.06 | 0.012 | random walk |
| PALL | 0.48 | 0.86 | -0.061 | random walk |
| USO | 0.32 | 0.97 | -0.009 | mean-reverting |
| UNG | 0.47 | 0.88 | -0.034 | random walk |
| BTC/USD | 0.52 | 0.95 | -0.043 | random walk |
| ETH/USD | 0.51 | 0.99 | -0.042 | random walk |
| SOL/USD | 0.56 | 0.99 | -0.018 | trending |
| LTC/USD | 0.44 | 0.88 | -0.045 | mean-reverting |
| BCH/USD | 0.49 | 1.0 | -0.079 | random walk |

## Statistical-arbitrage pairs (market-neutral mean reversion)
Top pairs by spread half-life (in-sample): SPY/XLY (28.0d), QQQ/XLY (37.4d), XLV/UNG (39.6d), WFC/GOOGL (43.2d), AMD/BTC/USD (47.3d), XLK/XLY (49.0d), XLF/GOOGL (56.6d), DIA/XLY (58.1d)

| Segment | ret% | maxDD% | MAR |
|---|--:|--:|--:|
| In-Sample | +8 | -4 | 2.01 |
| Out-of-Sample | +10 | -8 | 1.17 |

**Walk-forward:** positive with MAR>0.5 in **8/12 windows (67%)** → ✅ robust market-neutral edge

Pairs trading is market-neutral: it does not predict direction, only that a mean-reverting spread returns to its mean. A robust edge stays positive across windows.