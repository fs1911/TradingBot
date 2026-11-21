# Experiment #99 — Buffett indicator (market value / GDP) (2026-11-21 10:07 UTC)

Shiller rows 1869 (https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv); sources: FRED NCBEILQ027S: RuntimeError("TimeoutError('The read operation timed out')"); DBnomics FED search 103164103: <HTTPError 404: 'NOT FOUND'>; DBnomics search 'nonfinancial corporate equities': <HTTPError 404: 'NOT FOUND'>; Yahoo ^W5000 (Wilshire 5000 points ≈ $bn, proxy): 152 values 1989–2026; FRED GDP: RuntimeError("TimeoutError('The read operation timed out')"); DBnomics BEA NIPA-T10105 A191RC-Q: 319 values 1947–2026.

Buffett indicator 1989-06–2027-02 (monthly, available 3 months after each quarter). **Latest: 0 %** (quarter ending ≈ 2026-11); its 20-year average 0 %, highest ever 0 % (2026-09).
Months above 100 % ('overvalued' by the usual rule): before 1995 0 %, since 1995 0 %. Shiller returns end 2026-09.

## Buffett indicator (BI): quintile → next real S&P return per year
| quintile | range | months | next 1 y | next 3 y | next 10 y |
|---|---|--:|--:|--:|--:|
| Q1 (cheapest) | 0.05–0.07 | 80 | +12.1 % | +13.4 % | +10.7 % |
| Q2 | 0.07–0.09 | 80 | +17.5 % | +15.3 % | +8.0 % |
| Q3 | 0.09–0.10 | 80 | +3.9 % | +2.7 % | +6.5 % |
| Q4 | 0.10–0.12 | 80 | +5.6 % | +4.3 % | +0.3 % |
| Q5 (dearest) | 0.12–0.20 | 80 | +3.0 % | +3.5 % | -2.7 % |
- correlation, non-overlapping: 1 y -0.26 (t -1.51, n 34); 10 y — (t —, n 3); 10 y every 5 y -0.98 (t -8.20, n 5, half-overlapping)

## relative BI (vs own 20-year average): quintile → next real S&P return per year
| quintile | range | months | next 1 y | next 3 y | next 10 y |
|---|---|--:|--:|--:|--:|
| Q1 (cheapest) | 0.65–1.01 | 57 | +15.4 % | +12.2 % | +9.8 % |
| Q2 | 1.01–1.11 | 56 | +8.0 % | +4.5 % | +7.2 % |
| Q3 | 1.11–1.23 | 56 | +0.3 % | +3.1 % | +5.0 % |
| Q4 | 1.23–1.38 | 56 | +4.8 % | +8.8 % | +2.6 % |
| Q5 (dearest) | 1.38–1.83 | 56 | -1.1 % | -5.6 % | -2.5 % |
- correlation, non-overlapping: 1 y -0.38 (t -1.91, n 24); 10 y — (t —, n 2); 10 y every 5 y — (t —, n 3, half-overlapping)

## CAPE (same months, for comparison): quintile → next real S&P return per year
| quintile | range | months | next 1 y | next 3 y | next 10 y |
|---|---|--:|--:|--:|--:|
| Q1 (cheapest) | 13.32–20.52 | 80 | +12.9 % | +11.9 % | +11.7 % |
| Q2 | 20.52–24.21 | 80 | +9.9 % | +13.4 % | +8.7 % |
| Q3 | 24.35–26.64 | 80 | +11.4 % | +6.9 % | +5.5 % |
| Q4 | 26.69–31.16 | 80 | +7.2 % | +7.0 % | +4.0 % |
| Q5 (dearest) | 31.24–44.20 | 80 | +0.7 % | -0.9 % | -1.1 % |
- correlation, non-overlapping: 1 y -0.26 (t -1.55, n 34); 10 y — (t —, n 3); 10 y every 5 y -0.98 (t -9.57, n 5, half-overlapping)

## Timing rules (real, monthly, no costs): 100 % stocks, or 50/50 stocks/bonds when the signal's causal percentile ≥ 80 %
| rule | months | real CAGR | max drawdown | Sharpe | avg stock share |
|---|--:|--:|--:|--:|--:|
| T1 Buffett indicator | 291 | +3.2 % | -48 % | +0.34 | 76 % |
| static mix with the same 76 % stock share | 291 | +3.9 % | -38 % | +0.44 | 76 % |
| 100 % stocks (same months) | 291 | +4.5 % | -52 % | +0.40 | 100 % |
| T2 relative BI | 172 | +9.6 % | -22 % | +1.09 | 79 % |
| static mix with the same 79 % stock share | 172 | +8.8 % | -23 % | +1.00 | 79 % |
| 100 % stocks (same months) | 172 | +11.2 % | -24 % | +0.99 | 100 % |

Reading: a valuation measure can be right about the next 10 years and still useless for timing — the question is whether rules based on it beat simply holding, or a fixed mix with the same risk.
Caveats: few independent 10-year windows (≈ 7 since 1951); latest-vintage Fed/GDP data (revised, not as known then); nonfinancial corporate equities only; Shiller returns may end before today.