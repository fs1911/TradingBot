# Experiments #53–#55 — crash buying, counter-cyclical savings, what really matters (2026-10-26 09:52 UTC)

## #53 (H2) — buying after crashes
Trigger = first month per bear market in which the index is X % below its all-time high. Returns are total return where available (Shiller, funds), else price only. Bootstrap p = share of random month sets (same size) with an equal or higher 3-year return.

### S&P 500 TR (Shiller, 1871→) (1871-02 → 2026-09)
| Trigger | events | 1Y after | 3Y after (p.a.) | 5Y after (p.a.) | worst 3Y | all months 3Y (p.a.) | bootstrap p (3Y) | dates |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| -20 % | 13 | +6.4% | +8.8% | +7.0% | -58% | +10.7% | 0.741 | 1873-11, 1884-01, 1903-07, 1907-06, 1913-06, 1929-11, 1962-06, 1970-05 … |
| -30 % | 8 | +9.7% | +9.6% | +10.7% | -58% | +10.7% | 0.635 | 1876-11, 1884-06, 1907-10, 1917-11, 1929-11, 1974-07, 2002-06, 2008-10 |
| -40 % | 6 | +14.8% | +15.3% | +15.2% | -34% | +10.7% | 0.116 | 1877-04, 1896-08, 1930-10, 1974-09, 2002-09, 2008-11 |

### S&P 500 fund TR (VFINX) (1980-02 → 2026-10)
| Trigger | events | 1Y after | 3Y after (p.a.) | 5Y after (p.a.) | worst 3Y | all months 3Y (p.a.) | bootstrap p (3Y) | dates |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| -20 % | 5 | +13.6% | +10.8% | +12.8% | +2% | +12.3% | 0.668 | 1982-03, 1987-10, 2001-03, 2008-09, 2022-06 |
| -30 % | 2 | -5.3% | +7.8% | +11.2% | +12% | +12.3% | 0.779 | 2001-09, 2008-10 |
| -40 % | 2 | +24.8% | +15.3% | +16.4% | +48% | +12.3% | 0.294 | 2002-09, 2008-11 |

### S&P 500 price (^GSPC) (1928-01 → 2026-10)
| Trigger | events | 1Y after | 3Y after (p.a.) | 5Y after (p.a.) | worst 3Y | all months 3Y (p.a.) | bootstrap p (3Y) | dates |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| -20 % | 10 | +10.7% | +6.9% | +7.6% | -71% | +7.7% | 0.589 | 1929-10, 1962-06, 1970-01, 1974-03, 1982-03, 1987-10, 2001-03, 2008-09 … |
| -30 % | 6 | +5.0% | +4.0% | +6.0% | -69% | +7.7% | 0.812 | 1929-11, 1970-06, 1974-07, 1987-11, 2001-09, 2008-10 |
| -40 % | 4 | +7.2% | +7.3% | +9.3% | -48% | +7.7% | 0.545 | 1930-09, 1974-09, 2002-09, 2008-11 |

### Nasdaq Composite (^IXIC) (1971-03 → 2026-10)
| Trigger | events | 1Y after | 3Y after (p.a.) | 5Y after (p.a.) | worst 3Y | all months 3Y (p.a.) | bootstrap p (3Y) | dates |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| -20 % | 8 | +20.0% | +9.3% | +11.2% | -53% | +12.5% | 0.772 | 1973-05, 1982-03, 1984-02, 1987-10, 1990-09, 1998-08, 2000-05, 2022-04 |
| -30 % | 5 | +10.6% | +14.0% | +13.0% | -25% | +12.5% | 0.379 | 1973-11, 1987-11, 1990-10, 2000-11, 2022-09 |
| -40 % | 2 | -11.0% | -0.9% | +4.5% | -25% | +12.5% | 0.920 | 1974-05, 2000-11 |

### DAX (^GDAXI) (1988-01 → 2026-10)
| Trigger | events | 1Y after | 3Y after (p.a.) | 5Y after (p.a.) | worst 3Y | all months 3Y (p.a.) | bootstrap p (3Y) | dates |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| -20 % | 8 | +16.6% | +9.4% | +7.2% | -34% | +9.9% | 0.525 | 1990-09, 1998-09, 2001-03, 2008-06, 2016-02, 2018-12, 2020-03, 2022-09 |
| -30 % | 3 | +0.3% | +4.3% | +8.9% | -27% | +9.9% | 0.791 | 1990-09, 2001-08, 2008-10 |
| -40 % | 2 | -7.6% | +3.3% | +11.2% | -10% | +9.9% | 0.777 | 2001-09, 2008-11 |

### SMI (^SSMI) (1990-12 → 2026-10)
| Trigger | events | 1Y after | 3Y after (p.a.) | 5Y after (p.a.) | worst 3Y | all months 3Y (p.a.) | bootstrap p (3Y) | dates |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| -20 % | 4 | +2.0% | +10.1% | +9.0% | -12% | +7.8% | 0.316 | 1994-09, 1998-09, 2008-02, 2022-09 |
| -30 % | 2 | +11.0% | -0.4% | +2.1% | -7% | +7.8% | 0.821 | 1998-09, 2008-10 |
| -40 % | 2 | +11.9% | +7.9% | +10.9% | +7% | +7.8% | 0.433 | 2002-09, 2008-12 |

### Nikkei 225 (^N225) (1965-02 → 2026-10)
| Trigger | events | 1Y after | 3Y after (p.a.) | 5Y after (p.a.) | worst 3Y | all months 3Y (p.a.) | bootstrap p (3Y) | dates |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| -20 % | 3 | +3.4% | +12.2% | +7.4% | -38% | +8.6% | 0.297 | 1970-11, 1974-08, 1990-03 |
| -30 % | 2 | +3.5% | +3.8% | +4.5% | -19% | +8.6% | 0.675 | 1974-10, 1990-08 |
| -40 % | 1 | +14.0% | -1.4% | -3.1% | -4% | +8.6% | nan | 1990-09 |

## #54 (H3) — counter-cyclical savings plan (same total money)
Final wealth relative to plain DCA over all rolling windows (start every 12 months). Reserve earns cash (T-bill where available; Shiller: 10-year yield − 1 pt).

| Market | window | rule | median vs DCA | % windows better | worst | best |
|---|--:|---|--:|--:|--:|--:|
| S&P 500 TR (Shiller, 1871→) | 20 y | R20 | +0.0% | 50% | -13.2% | +2.8% |
| S&P 500 TR (Shiller, 1871→) | 20 y | R30 | -5.1% | 16% | -16.2% | +3.4% |
| S&P 500 TR (Shiller, 1871→) | 20 y | RTR | -0.5% | 7% | -3.9% | +0.1% |
| S&P 500 TR (Shiller, 1871→) | 30 y | R20 | -0.7% | 35% | -10.7% | +2.2% |
| S&P 500 TR (Shiller, 1871→) | 30 y | R30 | -5.7% | 2% | -17.6% | +0.5% |
| S&P 500 TR (Shiller, 1871→) | 30 y | RTR | -0.6% | 3% | -3.5% | +0.1% |
| S&P 500 fund TR (VFINX) | 20 y | R20 | -3.0% | 26% | -10.0% | +1.9% |
| S&P 500 fund TR (VFINX) | 20 y | R30 | -4.4% | 7% | -14.4% | +0.5% |
| S&P 500 fund TR (VFINX) | 20 y | RTR | -1.3% | 0% | -3.5% | -0.4% |
| S&P 500 fund TR (VFINX) | 30 y | R20 | -5.3% | 0% | -7.9% | -0.9% |
| S&P 500 fund TR (VFINX) | 30 y | R30 | -6.7% | 0% | -10.8% | -2.9% |
| S&P 500 fund TR (VFINX) | 30 y | RTR | -1.5% | 0% | -2.8% | -0.3% |
| S&P 500 price (^GSPC) | 20 y | R20 | -0.6% | 38% | -7.9% | +10.0% |
| S&P 500 price (^GSPC) | 20 y | R30 | -2.8% | 33% | -13.9% | +6.8% |
| S&P 500 price (^GSPC) | 20 y | RTR | -0.4% | 34% | -2.6% | +0.4% |
| S&P 500 price (^GSPC) | 30 y | R20 | -0.6% | 35% | -5.7% | +7.4% |
| S&P 500 price (^GSPC) | 30 y | R30 | -2.4% | 30% | -15.4% | +4.7% |
| S&P 500 price (^GSPC) | 30 y | RTR | -0.4% | 39% | -2.1% | +0.4% |
| Nasdaq Composite (^IXIC) | 20 y | R20 | -2.1% | 6% | -3.9% | +1.5% |
| Nasdaq Composite (^IXIC) | 20 y | R30 | -2.8% | 17% | -15.2% | +0.3% |
| Nasdaq Composite (^IXIC) | 20 y | RTR | -0.4% | 28% | -1.7% | +0.5% |
| Nasdaq Composite (^IXIC) | 30 y | R20 | -2.3% | 0% | -3.7% | -0.8% |
| Nasdaq Composite (^IXIC) | 30 y | R30 | -2.2% | 8% | -12.4% | +1.1% |
| Nasdaq Composite (^IXIC) | 30 y | RTR | -0.1% | 38% | -1.7% | +0.4% |
| DAX (^GDAXI) | 20 y | R20 | +0.7% | 68% | -2.5% | +1.3% |
| DAX (^GDAXI) | 20 y | R30 | -3.2% | 0% | -6.8% | -0.7% |
| DAX (^GDAXI) | 20 y | RTR | -0.4% | 11% | -0.7% | +0.3% |
| DAX (^GDAXI) | 30 y | R20 | +0.2% | 67% | -0.7% | +1.1% |
| DAX (^GDAXI) | 30 y | R30 | -3.9% | 0% | -5.2% | -3.4% |
| DAX (^GDAXI) | 30 y | RTR | -0.3% | 22% | -0.6% | +0.3% |
| SMI (^SSMI) | 20 y | R20 | +0.0% | 56% | -1.7% | +1.7% |
| SMI (^SSMI) | 20 y | R30 | -1.2% | 25% | -3.8% | +1.8% |
| SMI (^SSMI) | 20 y | RTR | -0.2% | 6% | -1.5% | +0.1% |
| SMI (^SSMI) | 30 y | R20 | +0.3% | 67% | -1.7% | +0.8% |
| SMI (^SSMI) | 30 y | R30 | -1.9% | 0% | -4.2% | -0.6% |
| SMI (^SSMI) | 30 y | RTR | -1.0% | 0% | -1.2% | -0.5% |
| Nikkei 225 (^N225) | 20 y | R20 | +0.0% | 36% | -7.8% | +1.3% |
| Nikkei 225 (^N225) | 20 y | R30 | -3.7% | 33% | -12.5% | +30.7% |
| Nikkei 225 (^N225) | 20 y | RTR | -0.0% | 33% | -0.8% | +0.3% |
| Nikkei 225 (^N225) | 30 y | R20 | +0.1% | 66% | -4.5% | +2.0% |
| Nikkei 225 (^N225) | 30 y | R30 | -2.1% | 38% | -12.3% | +14.5% |
| Nikkei 225 (^N225) | 30 y | RTR | -0.2% | 38% | -0.5% | +0.2% |

## #55 (H4) — what matters most for a saver (real S&P total return, Shiller)
Real (inflation-adjusted) monthly returns 1871-02 → 2023-09, every start year. Amounts in today's money; 500 per month unless stated.

| Scenario | worst | 10 % | median | 90 % | best | total paid in |
|---|--:|--:|--:|--:|--:|--:|
| 10 years, fee 0.2 % | 40,231 | 57,768 | 87,104 | 122,014 | 213,167 | 60,000 |
| 20 years, fee 0.2 % | 97,014 | 139,678 | 251,075 | 442,022 | 603,860 | 120,000 |
| 30 years, fee 0.2 % | 205,725 | 313,049 | 534,942 | 995,141 | 1,232,243 | 180,000 |
| 40 years, fee 0.2 % | 397,145 | 674,261 | 1,037,884 | 1,981,775 | 2,314,505 | 240,000 |
| 30 years, fee 1.0 % | 177,906 | 268,279 | 457,378 | 853,199 | 1,057,857 | 180,000 |
| 30 years, fee 2.0 % | 149,425 | 224,255 | 381,357 | 708,803 | 878,049 | 180,000 |
| 30 years, 300/month | 123,435 | 187,829 | 320,965 | 597,084 | 739,346 | 108,000 |
| 30 years, 1000/month | 411,450 | 626,097 | 1,069,884 | 1,990,281 | 2,464,486 | 360,000 |

Median effect vs the 30-year / 500 / 0.2 % baseline:
- 40 years, fee 0.2 %: +94%
- 30 years, fee 1.0 %: -14%
- 30 years, fee 2.0 %: -29%
- 30 years, 1000/month: +100%
- strategy +1 %/yr (e.g. buyback tilt after costs, optimistic): +22%
- strategy +2.6 %/yr (#50 best case, before costs/taxes): +71%