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

**Stärkere Prüf-Batterie (ab Exp. 11, `src/backtest/rigor.py`):** zusätzlich zu
OOS/Walk-Forward/Kosten jetzt auch (1) **Bootstrap-p-Wert** (ist der Mittelwert
statistisch von Null unterscheidbar?), (2) **Multiple-Testing-Haircut** (Bonferroni:
Schwelle α/Anzahl-Versuche), (3) **Regime-Stabilität** (positiv in allen 3 Dritteln
der Historie?), (4) **Sharpe & t-Statistik**, (5) **Parameter-Plateau** statt
Einzel-Ecke. Ein Edge gilt nur als echt, wenn er ALLE Stufen übersteht.

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
| 10 | 2026-09 | GLD/GDX Parameter-Robustheit (z-Fenster, Entry/Exit-Schwellen) — echt oder überangepasst? | **Überfit.** Basis-Kosten 15/27 Kombis (⚠️, Median MAR 1.01), realistische Kosten nur **5/27** (Median MAR 0.67). Funktioniert nur in einer Parameter-Ecke (z60-90/Entry2.0), nicht breit. Dollar-Ratios (GLD/UUP, SLV/UUP, USO/UUP, GDX/UUP) alle ❌ | ❌ nicht robust |
| 11 | 2026-09 | Saisonalität, Lead-Lag (Kupfer), Term-Struktur (VIX-Contango), Wochentag (Krypto) — unter der **stärkeren** Batterie (Bootstrap-p-Wert, Multiple-Testing-Haircut, Regime-Stabilität) | **0 von 10** überleben. Bestes: XLE-Saisonalität (3/3 Regime, p=0.044) scheitert am Haircut (nötig <0.0025) + Walk-Forward 38%. Lead-Lag klar negativ (t=−2.6) | ❌ kein Edge |
| 12 | 2026-09 | Turn-of-Month, Overnight-Drift, RSI(2)-Reversal, Low-Vol — unter der starken Batterie | **2 von 10 überleben:** **RSI(2) auf SPY** (p=0.001, Sharpe 1.15, WF 81%, 3/3 Regime) **und QQQ** (p=0.001, WF 76%, 3/3). Overnight klar negativ; Turn-of-Month/Low-Vol ❌ | ⚠️ RSI(2) besteht ALLES — Robustheit prüfen (#13) |
| 13 | 2026-09 | RSI(2) Parameter-Robustheit + Kosten-Stress (SPY/QQQ) — echt oder Glücks-Parameter? | *offen* | ⏳ |

## Erkenntnis-Stand (Update Exp. 10)

- **GLD/GDX war doch überangepasst.** Die schöne Zahl aus Exp. 9 (z60/Entry2.0/Exit0.5)
  war eine der wenigen guten Zellen im Raster. Über die *meisten* Parameter bricht der
  Edge bei realistischen Kosten zusammen (5/27). Ein echter Edge würde breit halten.
  → Der Robustheitstest (Exp. 10) hat genau seinen Zweck erfüllt: einen scheinbaren
  Fund als Überanpassung entlarvt, bevor Geld darauf gesetzt wurde.
- **Dollar-Ratios (die USD-Idee):** korrekt über den Dollar-Index (UUP) getestet —
  kein Edge. GLD/UUP ist faktisch eine Richtungswette auf Gold (negativ). Bestätigt:
  „X/USD" ist kein marktneutraler Spread.
- **Faint signal, kein Edge:** Bei Basis-Kosten deutet das Gold/Miner-Verhältnis eine
  schwache reale Mean-Reversion an (15/27), aber zu fragil/kostenempfindlich, um
  handelbar zu sein.

## Offener Backlog (noch nicht getestet)

- Saisonalität in Energie/Agrar (Erdgas Winter, Benzin Sommer) — Kalendereffekte.
- Term-Struktur / Roll-Yield (Contango/Backwardation) als Signal.
- Lead-Lag (Kupfer als Frühindikator; Wochenend-Effekte in Krypto).

### Experiment 11 (abgeschlossen — 0/10 unter der stärkeren Batterie)

Saisonalität (UNG/USO/XLE/GLD/SPY), Lead-Lag (Kupfer→Aktien), Term-Struktur
(VIX-Contango→SVXY), Wochentag-Effekt (Krypto). Die schärfere Batterie hat ihren
Zweck erfüllt: XLE-Saisonalität war in allen 3 Regimen positiv und p<0.05 —
gescheitert erst am Multiple-Testing-Haircut (nötig p<0.0025) und Walk-Forward 38%.
Genau die Fälle, die eine schwache Prüfung durchgelassen hätte, werden korrekt
verworfen. Details → `experiment11_results.md`.
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
