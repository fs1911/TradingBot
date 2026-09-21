# Experiment #18 — intraday (5Min) mean reversion (2026-09-21 06:26 UTC)

NEW DATA REGIME: intraday bars (~50-80x more observations than daily). Within-session rolling-z mean reversion, flat overnight, per-bar P&L aggregated to daily and judged by the full rigor battery (haircut α/50). Intraday costs bite hard — watch whether any edge survives them.

| Symbol | bars | days | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |
|---|--:|--:|--:|--:|--:|--:|:--:|:--:|:--:|---|
| SPY | 5855 | 71 | tot -12 · IS -7/OOS -6 | -7.9 | -4.19 | 1.0 | no | bar-level | 1 regime | ❌ no edge |
| QQQ | 6354 | 71 | tot -15 · IS -10/OOS -6 | -6.04 | -3.21 | 0.9993 | no | bar-level | 1 regime | ❌ no edge |
| BTC/USD | 20000 | 70 | tot -35 · IS -19/OOS -20 | -11.03 | -4.83 | 1.0 | no | bar-level | 1 regime | ❌ no edge |
| ETH/USD | 20000 | 76 | tot -24 · IS -14/OOS -11 | -4.53 | -2.07 | 0.9933 | no | bar-level | 1 regime | ❌ no edge |

**Summary:** 0/0 survive the full daily battery on intraday data. Free feed gives only ~70 days of intraday history — proper intraday research needs a paid multi-year intraday data source.