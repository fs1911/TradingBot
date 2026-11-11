# Experiment #88 — analyst rating changes (2026-11-11 08:45 UTC)

55 US stocks, 24,556 rating headlines (Benzinga via Alpaca, 2016 →); calls 7388, errors 0.

Entry = close of the first trading day AFTER the news day (New York date). 'already' = move over the two closes before entry. Excess vs SPY. p = random-date bootstrap (two-sided); Holm over all cells.

| class | events | already moved | 1 d mean / >0 (p, Holm) | 5 d mean / >0 (p, Holm) | 20 d mean / >0 (p, Holm) | 60 d mean / >0 (p, Holm) |
|---|--:|--:|--:|--:|--:|--:|
| *any day* | | | +0.02 % | +0.11 % | +0.45 % | +1.33 % |
| UPGRADE | 2,189 | +1.30 % | +0.12 % / 51 % (0.022, 0.360) | +0.33 % / 52 % (0.024, 0.360) | +0.70 % / 51 % (0.182, 1.000) | +1.63 % / 50 % (0.412, 1.000) |
| DOWNGRADE | 1,833 | -1.22 % | +0.11 % / 51 % (0.067, 0.931) | +0.29 % / 51 % (0.081, 1.000) | +0.68 % / 49 % (0.257, 1.000) | +1.98 % / 49 % (0.096, 1.000) |
| PT_RAISE | 4,333 | +0.47 % | +0.07 % / 50 % (0.149, 1.000) | +0.09 % / 49 % (0.692, 1.000) | +0.29 % / 48 % (0.261, 1.000) | +1.56 % / 49 % (0.364, 1.000) |
| PT_CUT | 2,605 | -0.54 % | -0.00 % / 48 % (0.489, 1.000) | +0.05 % / 49 % (0.434, 1.000) | +0.35 % / 49 % (0.580, 1.000) | +0.91 % / 48 % (0.214, 1.000) |

Cells tested: 16; significant after Holm: 0.
Caveats: only rating changes that Benzinga reported in a headline; the same change by several brokers on one day counts once (cool-down); large US companies only.