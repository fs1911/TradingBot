# Experiment #87 — news tone and attention (2026-11-09 19:38 UTC)

Companies/coins with news + prices: 61. Probe MSFT: 20312 articles, 2016-01-04–2026-11-08. Source: Alpaca/Benzinga news (headline + summary, word-list tone, pre-registered lists); US stocks + crypto only. Calls 8372, errors 0.
Entry = close of the first trading day AFTER the news day. 'already' = move from two closes before entry to entry (what happened before a reader could act). p = random-date bootstrap; Holm over all cells.

## stocks
| event | n | already moved | 1 d mean / median / >0 (p, Holm) | 5 d mean / median / >0 (p, Holm) | 20 d mean / median / >0 (p, Holm) |
|---|--:|--:|--:|--:|--:|
| *any day* | | | +0.02 % | +0.11 % | +0.44 % |
| E1 tone shock + | 1,316 | +0.52 % | -0.09 % / -0.12 % / 46 % (0.028, 0.660) | -0.11 % / -0.16 % / 48 % (0.069, 1.000) | -0.04 % / -0.60 % / 47 % (0.042, 0.966) |
| E2 tone shock − | 1,353 | -0.65 % | -0.08 % / +0.01 % / 50 % (0.055, 1.000) | +0.06 % / -0.02 % / 50 % (0.657, 1.000) | +0.60 % / -0.09 % / 50 % (0.546, 1.000) |
| E3 attention spike | 1,934 | +0.23 % | +0.03 % / -0.06 % / 48 % (0.783, 1.000) | +0.12 % / -0.09 % / 49 % (0.920, 1.000) | +0.46 % / +0.12 % / 51 % (0.992, 1.000) |
| E4 spike + negative tone | 296 | -3.54 % | +0.05 % / -0.04 % / 49 % (0.799, 1.000) | +0.27 % / -0.36 % / 48 % (0.531, 1.000) | +0.98 % / +0.12 % / 51 % (0.299, 1.000) |
| E5 spike + positive tone | 501 | +2.19 % | -0.06 % / -0.15 % / 46 % (0.345, 1.000) | +0.03 % / -0.03 % / 49 % (0.682, 1.000) | +0.31 % / +0.38 % / 53 % (0.741, 1.000) |

## crypto
| event | n | already moved | 1 d mean / median / >0 (p, Holm) | 5 d mean / median / >0 (p, Holm) | 20 d mean / median / >0 (p, Holm) |
|---|--:|--:|--:|--:|--:|
| *any day* | | | +0.25 % | +1.35 % | +6.56 % |
| E1 tone shock + | 111 | +2.25 % | -0.39 % / -0.66 % / 42 % (0.212, 1.000) | +0.70 % / +0.06 % / 50 % (0.615, 1.000) | +3.92 % / +0.15 % / 52 % (0.514, 1.000) |
| E2 tone shock − | 138 | -1.94 % | +0.15 % / +0.14 % / 52 % (0.853, 1.000) | +0.50 % / -0.24 % / 48 % (0.483, 1.000) | +0.92 % / -1.12 % / 49 % (0.122, 1.000) |
| E3 attention spike | 40 | +1.51 % | -0.82 % / -1.06 % / 35 % (0.184, 1.000) | -0.90 % / -1.84 % / 42 % (0.281, 1.000) | -0.67 % / -4.79 % / 38 % (0.238, 1.000) |
| E4 spike + negative tone | 2 | -10.91 % | -10.85 % / -10.85 % / 0 % (nan, nan) | -15.46 % / -15.46 % / 0 % (nan, nan) | -19.31 % / -19.31 % / 0 % (nan, nan) |
| E5 spike + positive tone | 6 | +3.69 % | -1.55 % / -1.88 % / 33 % (nan, nan) | +3.86 % / +4.17 % / 67 % (nan, nan) | +13.59 % / -0.36 % / 50 % (nan, nan) |

## Weekly long/short by 5-day tone (stocks, 498 weeks)
- gross: -0.041 %/week (t -0.40) ≈ -2.2 %/yr
- net of 10 bp per side: -0.441 %/week (t -4.30) ≈ -23.0 %/yr

Cells tested: 24; significant after Holm: 0.
Caveats: GDELT tone is machine-scored and translated; company-name queries catch some unrelated articles (noise lowers power); events cluster in market-wide news days.