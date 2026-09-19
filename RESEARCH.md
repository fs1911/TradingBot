# TradingBot — Forschungs-Journal

Dieses Projekt wird als **Quant-Forschungsprojekt** geführt, nicht als
"Geld-druck-Bot". Jede Hypothese wird durch dieselbe Härte-Pipeline getestet, und
jedes Ergebnis — auch ein "kein Edge" — ist echtes, festgehaltenes Wissen.

## Methodik (die Messlatte)

Jede Hypothese muss:
1. **Out-of-Sample (OOS)** funktionieren — erste Hälfte der Historie schätzt/wählt,
   unbekannte zweite Hälfte testet.
2. Über die **meisten Walk-Forward-Fenster** halten (rollierende 1-Jahres-Fenster) —
   nicht nur in einem Glücksfenster.
3. **Realistische Kosten** überleben (Kommission + Slippage auf beide Beine +
   Leihgebühren fürs Shorten).
4. Möglichst **wirtschaftlich begründet** sein (echte Kopplung), nicht ein
   statistischer Zufallstreffer.

**Warnung — Multiples Testen:** Je mehr Hypothesen wir probieren, desto
wahrscheinlicher sieht eine rein zufällig gut aus. Deshalb ist die Messlatte
absichtlich streng, und ein einzelnes schönes Fenster zählt nicht.

## Bisherige Experimente

| # | Datum | Hypothese | Ergebnis | Verdikt |
|---|---|---|---|---|
| 1 | 2026-08 | Intraday-TA (macd, vwap, supertrend, breakout), 15-Min, alle Anlageklassen | OOS Profit-Faktor < 1 überall | ❌ kein Edge |
| 2 | 2026-08 | Daily Trend-Following (MA20/100, Faber SMA200) | Marktbeta; Buy&Hold schlug es klar (MAR) | ❌ kein Edge |
| 3 | 2026-08 | Metall-Trend Walk-Forward (7 Metall-ETFs) | schlug Halten in 1/19 Fenstern | ❌ nicht robust |
| 4 | 2026-08 | Cross-Sectional Momentum (Aktien, Krypto) | 6/18 bzw. 3/17 Fenster; OOS < Halten | ❌ nicht robust |
| 5 | 2026-08 | BTC/Gold/Dollar Rotation (top1 & dual) | schlug Halten in 3/19 Fenstern | ❌ nicht robust |
| 6 | 2026-08 | Volatilitäts-Risikoprämie (SVXY, naiv + trend) | Prämie real, aber MAR 1.24 vs SPY 7.22; 5/21 | ❌ schlechter als Halten |
| 7 | 2026-09 | Quant-Struktur + Stat-Arb-Pairs (alle Symbole) | Walk-Forward 8/12 (67 %) — vielversprechend | ⚠️ zu prüfen |
| 8 | 2026-09 | Pairs-Stress-Test (nur sinnvolle Paare, echte Kosten) | 33 % Walk-Forward; hängt an 1 Paar (NVDA/AMD); stirbt bei harten Kosten | ❌ nicht tragfähig |
| 9 | 2026-09 | Inter-Rohstoff-Ratios (Gold/Silber, Platin/Palladium, Gold/Öl, Gold/Miner, Silber/Miner) | **GLD/GDX** überlebt bei niedrigen/Basis-Kosten (Walk-Fwd 76%/67%, MAR 2.5-2.9), marginal bei realistischen Kosten (52%, MAR 1.92, +18% OOS); andere Ratios ❌; PPLT/PALL hohe Rendite aber nur 47% WF | ⚠️ GLD/GDX vielversprechend |
| 10 | 2026-09 | GLD/GDX Parameter-Robustheit (z-Fenster, Entry/Exit-Schwellen) — echt oder überangepasst? | *offen* | ⏳ |

## Erkenntnis-Stand (Update Exp. 9)

- **Erster wirtschaftlich begründeter Teilerfolg: GLD/GDX** (Gold vs. Goldminen).
  Ökonomisch sinnvoll — Minen-Aktien sind ein gehebeltes Gold-Investment (Goldpreis
  minus Förderkosten), der Spread hat also einen echten strukturellen Anker, kein
  Zufall wie NVDA/AMD. Übersteht OOS + Walk-Forward bei niedrigen/Basis-Kosten;
  wird bei realistischen Kosten marginal. Beide ETFs sind liquide → reale Kosten
  liegen eher bei "Basis" als "hart".
- **Offene, entscheidende Frage:** Hängt es an den zufällig gewählten Parametern
  (z-Fenster 60, Entry 2.0, Exit 0.5)? Wenn ja → überangepasst. Wenn es über einen
  Bereich vernünftiger Parameter hält → echter, tragfähiger Kandidat. Das ist
  Experiment #10.

## Erkenntnis-Stand

- Richtungswetten aus öffentlichen Kursen haben nach Kosten keinen persistenten
  Edge (Exp. 1–6). Der einzige zuverlässige Edge blieb die **Aktien-Risikoprämie**
  (Halten).
- Marktneutrale Ansätze (Pairs) kamen am weitesten (Exp. 7), fielen aber unter
  ehrlicher Prüfung (Exp. 8): Zufallspaare + Ein-Paar-Abhängigkeit + Kosten.
- Nächste Richtung: **wirtschaftlich begründete** marktneutrale Spreads
  (Rohstoff-Ratios) — echte Kopplung statt statistischer Zufall.

## Vorlage für neue Experimente

```
| N | JJJJ-MM | <Hypothese, wirtschaftliche Begründung> | <Zahlen: OOS ret/MAR, Walk-Forward, Kosten> | ✅/⚠️/❌ |
```

Neue Hypothese testen: Tages-Rendite-Serie der Strategie erzeugen und durch
`src/backtest/research.py:evaluate_hypothesis()` schicken (OOS + Walk-Forward),
idealerweise mit Kosten-Sweep über `COST_SCENARIOS`.
