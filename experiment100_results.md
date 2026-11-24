# Experiment #100 — following anonymous public trading accounts (2026-11-24 11:11 UTC)

Internet Archive: 1231 robintrack URLs, archive candidates: none; CoinMetrics columns: btc: FlowInExNtv, FlowInExNtv-status, FlowInExNtv-status-time, FlowOutExNtv, FlowOutExNtv-status, FlowOutExNtv-status-time, SplyExNtv, SplyExNtv-status, SplyExNtv-status-time, PriceUSD; eth: FlowInExNtv, FlowInExNtv-status, FlowInExNtv-status-time, FlowOutExNtv, FlowOutExNtv-status, FlowOutExNtv-status-time, SplyExNtv, SplyExNtv-status, SplyExNtv-status-time, PriceUSD.

## A Robinhood herding (Robintrack)
Robintrack data not available — part A not run.

## B Crypto exchange flows (CoinMetrics community)
- btc (2013→): month-end net inflow vs next 30 days: Spearman -0.13, permutation p +0.087, 165 months (negative = inflow → weaker price, as expected).
  - top 5 % inflow (selling pressure?): 17 events; next 7 d +4.44 % (all days +1.77 %), next 30 d +17.30 % (all days +8.98 %)
  - top 5 % outflow (accumulation?): 27 events; next 7 d +3.94 % (all days +1.77 %), next 30 d +14.58 % (all days +8.98 %)
- eth (2015→): month-end net inflow vs next 30 days: Spearman -0.07, permutation p +0.451, 134 months (negative = inflow → weaker price, as expected).
  - top 5 % inflow (selling pressure?): 16 events; next 7 d +1.38 % (all days +2.26 %), next 30 d +8.58 % (all days +12.25 %)
  - top 5 % outflow (accumulation?): 27 events; next 7 d -0.03 % (all days +2.26 %), next 30 d +14.05 % (all days +12.25 %)

Primary tests, Holm-corrected: B btc IC: p +0.087, Holm +0.174; B eth IC: p +0.451, Holm +0.451

Caveats: Robintrack covers one broker and 2018–2020 only; delisted tickers lack Yahoo prices; CoinMetrics exchange attribution is incomplete (unlabelled wallets).