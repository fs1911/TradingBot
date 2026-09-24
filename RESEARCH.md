<!-- ops: force redeploy 2026-09-22 (exp #28 unbounded fetch stalled the runner; #28 now capped at 16 contracts, #29 added) -->
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
| 13 | 2026-09 | RSI(2) Parameter-Robustheit + Kosten-Stress (SPY/QQQ/DIA/XLK/XLF) — echt oder Glücks-Parameter? | **Real, aber fragil.** *Richtung* über das ganze Raster konsistent positiv (echter kurzfristiger Mean-Reversion-Effekt, kein Zufall!), aber bei realistischen Kosten überstehen nur 2-4/24 Kombis die strenge Signifikanz (Haircut); DIA/XLF 0/24; bei harten Kosten ~0. Kein handelbarer Edge nach ehrlicher Korrektur | ❌ (aber echter Effekt) |
| 14 | 2026-09 | Volatilitäts-Targeting (Risiko-Overlay auf Halten) | Drawdowns ~halbiert (BTC −77%→−25%, SPY −25%→−15%), Sharpe ~gleich (QQQ/GLD minimal besser), aber Rendite deutlich niedriger → **0/6 besser risikoadjustiert (MAR)**. Risikomanagement, kein Return-Edge | ✅ als Risiko-Tool, ❌ als Edge |
| 15 | 2026-09 | **ML** (Walk-Forward Logistische Regression, 11 Features → Tagesrichtung) | **0/6 überleben.** QQQ marginal (p=0.03, scheitert Haircut). Aufschlussreich: das Modell lernte *negatives* Gewicht auf rsi2 & d_sma20 = „kaufe wenn überverkauft" — es hat also **denselben schwachen Mean-Reversion-Effekt wie Exp #13 wiederentdeckt** und bestätigt: nichts Handelbares generalisiert | ❌ kein Edge (aber konsistent mit #13) |
| 16 | 2026-09 | Volumen-Signale (Kapitulations-Bounce, OBV-Trend) + Aktien/Anleihen Dual-Momentum (SPY/TLT) | **0/9 überleben.** OBV-Trend (SPY/QQQ) & DualMom positiv, 3/3 Regime, aber p>0.05 → scheitern am Haircut. Volumen als Primärsignal bringt nichts Signifikantes | ❌ kein Edge |
| 17 | 2026-09 | Regime-bedingte Mean-Reversion: RSI(2) NUR im Hochvolatilitäts-Regime (dort ist Rückkehr am stärksten) — lässt sich der eine reale Effekt (#13) durch Konditionierung retten? | **1/8 „besteht" — aber es ist ein Multiple-Testing-Artefakt und wird VERWORFEN:** der Überlebende (RSI2-*lowvol* SPY, p=0.001) **widerspricht der vorab registrierten Hypothese** (Hochvol sollte es sein, war aber nur ⚠️), tritt nur auf 1 von 4 Indizes auf, und p liegt hauchdünn unter α/45=0.0011. Ein echter Regime-Effekt wäre konsistent + theoriekonform. Lehrbuch-Beispiel, warum Vorab-Registrierung + Haircut zählen | ❌ (Scheintreffer korrekt abgelehnt) |
| 18 | 2026-09 | **NEUES DATENREGIME:** Intraday-Mean-Reversion auf 5-Min-Bars (SPY/QQQ/BTC/ETH) | **Refutiert + Datengrenze.** Intraday-MR *verliert signifikant* (t=−2 bis −5, alle 4) — auf 5-Min-Horizont dominiert Kosten/Continuation, keine Reversion. UND: Gratis-IEX-Feed liefert nur **~70 Tage** Intraday-Historie → für seriöse Intraday-Forschung braucht es einen **bezahlten Mehrjahres-Feed**. Bestätigt die These „falsche/zu wenig Daten" als *Datenzugang*-Grenze | ❌ + Datengrenze erkannt |
| 19 | 2026-09 | **BREITEN-SCAN** über 55 Werte aller Klassen (Indizes, Sektoren, Edel-/Industriemetalle, Rohstoffe, Agrar, Währungen inkl. CHF, Anleihen, Krypto): Struktur (Hurst/VR) + RSI(2) | **0/55 überleben.** Der Mean-Reversion-Effekt existiert **nur bei US-Großindizes/-Sektoren** (SPY/QQQ p=0.001, XLK/XLY/XLI/XLF — alle ⚠️, scheitern am Haircut). **Metalle, Rohstoffe, Währungen, Anleihen, Krypto: Hurst ≈ 0.5 (Random Walk), kein Edge.** 8 ⚠️ sind korrelierte Großcap-Aktien = derselbe bekannte schwache Effekt, kein neuer | ❌ (vollständige Landkarte) |
| 20 | 2026-09 | **QUERSCHNITT** statt Timing: dollar-neutrales Long/Short-Portfolio über 92 S&P-Einzelaktien (2018–2026, 1549 Tage). Zwei dokumentierte Anomalien — Short-Term-Reversal (5T, tägl.) & 12-1-Momentum (monatl.) — je über Kosten-Sweep (1/5/10 bps) durch die volle Rigor-Batterie. Universum bewusst survivorship-biased (inflationär) | **0/6 überleben.** Reversal ist schon bei 1 bps negativ (OOS −10%) und bricht mit Kosten völlig ein (−46%/−71%, t bis −3.7) — der Effekt ist real, aber die Umschlagskosten fressen ihn mehr als auf. Momentum hat den *einzigen positiven* Sharpe des ganzen Projekts (0.44) und 2/3 Regimes+, ist aber statistisch nicht signifikant (p≈0.15, OOS negativ). Selbst auf dem geschönten Survivor-Universum: kein handelbarer Edge | ❌ |
| 21 | 2026-09 | **MOMENTUM VERFEINERT** (dem #20-Fund nachgehen): 6 dokumentierte Veredelungen von 12-1 — vol-skaliertes Ranking, residuales/idiosynkratisches Momentum (Blitz-Huij-Martens), vol-managed (Barroso-Santa-Clara), Regime-Filter (>200T), Long-only — je monatlich, 5 bps, volle Rigor-Batterie | **0/6 überleben.** Die markt-neutralen Varianten (1–5) clustern bei Sharpe 0.27–0.43, keine signifikant — die Verfeinerungen bringen **nichts** (vol-managed 0.42 ≈ roh 0.43; residual verschlechtert auf 1/3 Regimes). **Ausreißer: Long-only Top-Dezil** OOS +106%, Sharpe 0.72, t=1.79, p=0.0195, 3/3 Regimes — der stärkste Wert des Projekts, aber scheitert am Haircut (α/66) UND Walk-forward nur 48%. **Verdacht: das ist Beta, nicht Alpha** — Long-Exposure in Survivor-Aktien in einem Bullenmarkt, nicht bessere Selektion. Muss in #22 gegen die Benchmark getestet werden | ❌ (aber Long-only → #22) |
| 22 | 2026-09 | **ALPHA-oder-BETA-TEST** des Long-only-Momentum: Überschussrendite (Portfolio − gleichgewichtete Universum-Benchmark) für 5 Selektionen (roh 12-1 top 10/20/30%, residual, vol-skaliert) durch die volle Rigor-Batterie. Der Excess ist konstruktionsbedingt markt-neutral — überlebt er, ist es echte Selektions-Fähigkeit; wenn nicht, war #21s Long-only reines Marktbeta | **0/5, eindeutig BETA.** Die Benchmark (gleichgewichtetes Gesamt-Universum) hat Sharpe **1.03** — *höher* als jede Momentum-Selektion (0.61–0.78)! Alpha-Sharpes ≈ 0 (0.31/0.01/−0.18/0.14/0.15), keine signifikant. **Momentum-Auswahl hat null Selektions-Alpha — sie war sogar schlechter als „alle gleich halten".** Der stärkste Fund des Projekts löst sich vollständig auf. Der einzige Sharpe>1 ist reines (survivor-verzerrtes) Beta+Diversifikation | ❌ (Beta entlarvt) |
| 23 | 2026-09 | **REBALANCING-PRÄMIE** (Volatilitäts-Ernte, Fernholz): der einzige verbleibende *strukturelle* (nicht-prognostische) Mechanismus. Überschuss (periodisch auf Gleichgewicht zurückgesetzt − einfach halten) auf demselben Universum, wöchentlich/monatlich/quartalsweise über Kosten, volle Rigor-Batterie. Beta & Survivor-Bias heben sich zwischen beiden Beinen auf | **0/4, Prämie sogar NEGATIV** (Sharpe −0.25 bis −0.29, OOS −11%, p≈0.73). B&H-Sharpe 0.96 ≈ rebalanced 0.94–0.95: Frequenz egal. Im Trend-Bullenmarkt schlägt „Gewinner laufen lassen" das Trimmen → Rebalancing ist hier ein **Risiko-Werkzeug, kein Ertrags-Edge**. Auch die letzte strukturelle Hoffnung vermessen | ❌ |
| 32 | 2026-09 | **JAHRZEHNTE-DATEN** (Stooq/Yahoo, bis zu 50+ Jahre): (A) Drawdown-Signal bei −20/−35/−50 % mit echten Crash-Episoden (1987, 2000, 2008, Japan 1989) — Überrendite, t-Test, beide Hälften, Sparplan vs. Crash-Reserve; (B) 200T-Filter & 12M-Momentum vs. Buy&Hold über viele Zyklen (CAGR/Sharpe/MaxDD + Rigor auf Differenz). Indizes: S&P, Nasdaq, Dow, Russell, Nikkei, DAX, SMI, Gold, BTC | **Zwei robuste Befunde, beide keine Rendite-Edge.** Daten via Yahoo, 17–57 Jahre. (A) **Drawdown-Kaufsignal widerlegt:** bei −35 % Überrendite nur 5/9, t>2 nur 2/9 (winzige n), beide Hälften 3/9; Nasdaq (Dotcom), Nikkei, Gold und **BTC negativ** (BTC 12 J.: Zone −5 Pp unter normal → #30-Krypto-Effekt war 2022-Artefakt). **Crash-Reserve schlägt normalen Sparplan in 0/9 (−35 %/−50 %) und 1/9 (−20 %)** — über Jahrzehnte eindeutig: nicht auf Dips warten. (B) **200T-Trendfilter = echtes Risiko-Werkzeug:** senkt max. Drawdown in **9/9** (S&P −57→−30 %, Nasdaq −78→−49 %, Nikkei −82→−33 %, DAX −73→−36 %), Sharpe besser 6/9, aber CAGR meist 1–4 Pp tiefer (Cash 0 % angesetzt) und schlägt B&H in 0/9 durch Rigor. → Finanzradar: Drawdown-„Kaufzone" streichen, 200T-Trend als Risiko-Anzeige | ✅ Risiko-Tool / ❌ Kaufsignal |
| 31 | 2026-09 | **STRESSTEST des Drawdown-Signals** (#30 härter prüfen): Überrendite ggü. normaler 90T-Rendite, echte Anzahl unabhängiger Crash-Episoden, t-Test auf nicht-überlappenden Stichproben, OOS-Hälften, breiteres Universum inkl. Verlierer (EEM, XLE, TLT, EFA, GLD, SOL), plus Praxis: Sparplan vs. „Reserve halten & im Crash nachkaufen" | **Signal hält der Härteprüfung NICHT stand — nur schwache Tendenz.** Zone in 6 Jahren nur bei 7/13 Assets erreicht (SPY, DIA, IWM, EFA, XLF, GLD: nie). Überrendite zwar in 6/7 positiv, aber **t>2 in 0/7**, beide Hälften positiv nur 2/7; insgesamt nur ~15 unabhängige Episoden, fast alle aus 2022. SOL sogar negativ. Praxis: „Reserve halten & im Crash kaufen" schlägt normalen Sparplan nur 5/13 (Cash-Bremse, z. B. SPY 1,31× vs 1,62×). Fazit: Richtung plausibel, aber statistisch unbewiesen; Stichprobe (6 J., Alpaca-IEX) zu kurz → Finanzradar-Tooltip abschwächen; nächster Schritt: Jahrzehnte-Daten | ⚠️ unbewiesen |
| 30 | 2026-09 | **BEWERTUNGS-GAUGES für Finanzradar** (Drawdown vom ATH & Abstand 200T-MA) über native Broker-Preise (kein ccxt): sagt „billig" höhere Folge-Renditen (90T) voraus? Indizes + Krypto | **TEILWEISE POSITIV — bester Finanzradar-Fund.** Drawdown-vom-ATH contrarian in **4/6** (BTC/ETH SEHR stark: tiefster-DD-Bucket +17%/+22% vs. nahe-ATH −5,7%/+0,4%; QQQ/DIA mild; SPY flat, IWM invers). Gepoolt (9833 Beob.): **DD ≤ −35% → +14,0%/90T** (n=2291), −35…−10% → +2,4%, nahe ATH → +4,3%. ABER: (a) nur der **tiefe Drawdown (≥35%) = echtes Kaufsignal**; (b) „nahe ATH = überhitzt" gilt NICHT (Renditen dort ok, +4,3% — Trend läuft weiter); (c) 200T-MA-Gauge schwach/gemischt (3/6), nicht nutzen; (d) gilt nur für Assets in säkularem Aufwärtstrend, die sich erholen | ✅ nutzbar (Deep-Drawdown-Kaufsignal) |
| 29 | 2026-09 | **FUNDING ALS ÜBERHITZUNGS-GAUGE** (Finanzradar-Signal, kein Bot-Trade): Funding = Crowding der gehebelten Longs. Zwei Tests über 6 Coins — (a) prädiktiv: sagt hohes Funding niedrigere 30T-Forward-Renditen voraus (contrarian)? (b) nutzbare Regel: „bei heißem Funding aussteigen" vs. Buy&Hold | **NEIN, funktioniert nicht.** Contrarian nur in **1/6** Coins (BNB); in 5/6 folgten auf hohes Funding sogar *höhere* Renditen (Funding läuft eher MIT dem Momentum, nicht dagegen). „Aussteigen"-Filter schlägt Buy&Hold in **0/6** — er verpasst nur Aufwärtsbewegung (Sharpe & Rendite überall schlechter). **Keine belastbare Finanzradar-Ampel aus Funding.** Ehrliches Negativ — nicht einbauen | ❌ |
| 28 | 2026-09 | **DATED-FUTURES KALENDER-BASIS** (letzter eigenständiger Carry, umgeht #25s Turnover-Killer): Spot long / Quartals-Future short, bis Abrechnung halten ≈ null Turnover. ZWEI Ziele: (a) Carry durch die Batterie; (b) **Finanzradar-Signal** — annualisierte Basis als Überhitzungs-Gauge (hohes Contango → niedrigere Forward-Renditen?). Daten abgelaufener Kontrakte evtl. lückenhaft → meldet ehrlich | _(läuft auf VM — Ergebnis in `experiment28_results.md`)_ | ⏳ |
| 27 | 2026-09 | **CROSS-EXCHANGE-FUNDING-DIFFERENZ** (low-turnover Carry): umgeht #25s Turnover-Killer? Dieselbe Perp long auf Niedrig-Funding-Börse, short auf Hoch-Funding-Börse = perp-neutral, kein Spot, erntet die Börsen-Differenz. Über 5 Coins (2 Venues verfügbar), volle Batterie | **Statistisch ✅, ökonomisch trivial.** Kombiniert nur **~1.55%/Jahr brutto** (Sharpe 5.53, 100% wf, p=0) — überlebt zwar die Batterie, aber die Differenz ist winzig (<3%/J). Nach Gebühren auf zwei Börsen + Transfers + doppeltem Liquidations-Risiko **kein echter Edge**. Bestätigt: Funding ist über Venues stark korreliert/arbitragiert. Der Level-Carry (#24–26, Tilt ~8.6%) bleibt die einzige lohnende Version | ✅ real aber zu dünn |
| 26 | 2026-09 | **CARRY BREITER/SMARTER**: kann der eine echte Edge vergrößert/robuster werden? 3 Varianten über 23 Perps (2022-11→2026-09) — breiter Gleichgewichts-Korb, carry-gewichteter Tilt (kausal aus Trailing-Funding), Cross-Sectional-Dispersions-Spread — je durch die volle Batterie | **3/3 überleben ✅.** Breiter Korb 5.8%/J (Sharpe 7.05) — Breite *verdünnt* die Rendite (mehr Niedrig-Funding-Coins) statt sie zu erhöhen. **Carry-Tilt ist der Sieger: 8.6%/J, Sharpe 11.15, 100% Walk-fwd** — Übergewichtung hoch-Funding-Coins hilft real (5.8→8.6%). Spread 6.3%/J, Sharpe 14.78 (glättester), aber shortet auch Niedrig-Funding-Perps → mehr Beine/Kosten. Fazit: Edge bestätigt & moderat verbesserbar (~8.6% brutto), aber weiterhin ~cash-plus & kostenfragil — kein Durchbruch der Größenordnung | ✅ (Tilt bester, Ceiling bestätigt) |
| 25 | 2026-09 | **CARRY NETTO** (Machbarkeit): #24s Carry durch ein *konkretes* Kostenmodell (Bybit Taker 0.055%/Maker 0.02% pro Bein, Rotations- & Rehedge-Frequenz) statt abstrakter %-Drag; plus benötigtes Kapital für 10 CHF/Tag. Wandelt „Sharpe 7" in eine Franken-Antwort | **Brutto ~7.9%/J.** Netto stark turnover-abhängig: 7-Tage-Rotation Taker = **−4.4% (Verlust!)**; seltene Rotation gewinnt: 90T Maker **+7.3%**, 90T Taker +6.2%, 30T Maker +6.7%. Für 10 CHF/Tag: **~50.000–83.000 CHF Kapital** nötig. Fazit: real & netto-positiv NUR bei disziplinierter Low-Turnover/Maker-Ausführung, aber nur ~1–3 pp über risikofreiem Cash (~4–5%) — und ungepreiste Tail-Risiken (Liquidation/Börse/Basis) fressen diese dünne Marge in einem schlechten Ereignis plausibel auf | ✅ real, aber dünn über Cash & kapitalhungrig |
| 24 | 2026-09 | **FUNDING-CARRY** (Krypto-Perpetuals, delta-neutral): erster Test einer *strukturellen Zahlung* statt Vorhersage. **Neue Datenquelle** (ccxt/Bybit-Funding-Historie, ~1400 Tage) + **neuer Mechanismus**. Longs zahlen Shorts Funding → delta-neutral (Spot long/Perp short) kassiert es ohne Kursrisiko. Pro Coin + Korb durch die volle Batterie, Kosten-Sweep | **ERSTER ÜBERLEBENDER.** BTC/ETH/DOGE ✅, XRP ⚠️, SOL ❌. Korb @0% Kosten: Sharpe **9.25**, 100% Walk-fwd, 3/3 Regimes ✅. ABER: (1) absolute Rendite nur **~8%/Jahr brutto** (Sharpe hoch, weil glatter Tropf — nicht wegen Höhe); (2) **kostenfragil**: @2%/J nur noch ⚠️ (Sharpe 5.6), **@5%/J tot** (Sharpe 0.11); (3) Funding 17–27% der Zeit **negativ**; (4) Batterie sieht Gegenpartei-/Liquidations-/Basis-Risiko NICHT; (5) auf Alpaca nicht handelbar. Real, aber dünn — Netto-Kosten-Studie nötig (#25) | ✅ (erster echter, aber kostenfragil) |

## ANWENDUNGSRICHTUNG (Nutzer-Direktive 2026-09-22)

Ein Fund muss **nicht** zwingend eine Bot-Automatik sein. Genauso wertvoll — evtl.
wertvoller — ist eine **manuell anwendbare Strategie** oder ein **sauberes,
ernsthaftes Bewertungs-/Prognosesignal**, das der Nutzer in sein Zweitprojekt
**„Finanzradar"** einbauen kann (Kaufen/Halten/Überhitzt-Ampel). Bei jedem Fund also
prüfen: Lässt sich daraus ein verständliches, robustes Signal für einen Menschen
ableiten (nicht nur ein delta-neutraler Bot-Trade)? Ggf. dedizierter Backtest dafür.

## STAND — laufendes Forschungsprojekt (zuletzt 2026-09-21)

**Der ursprünglich definierte Hypothesenraum (Exp. 1–14) ist abgearbeitet; das
Projekt läuft als offene Forschung weiter mit neuen Methodik-Kategorien (ML ab
Exp. 15, danach Volumen-/Intermarket-Signale usw.).** Ergebnis bisher, ehrlich und
reproduzierbar über eine im Zeitverlauf verschärfte Batterie:

Ergebnis, ehrlich und reproduzierbar:

1. **Kein robuster, kosten-überlebender, handelbarer Edge** — weder gerichtet
   (Trend, Momentum, Rotation, Saisonalität, Lead-Lag, Term-Struktur, Overnight)
   noch marktneutral (Stat-Arb-Pairs, Rohstoff-Ratios) — hält der ehrlichen
   Prüfung nach Kosten stand. Jeder scheinbare Fund zerbrach an einer Stufe: OOS,
   Walk-Forward, Kosten, Parameter-Robustheit oder Signifikanz nach Haircut.
2. **Der einzige reale, aber zu schwache Effekt:** kurzfristige Mean-Reversion in
   liquiden Aktienindizes (RSI(2)) — Richtung konsistent, aber nach Kosten +
   Korrektur nicht verlässlich handelbar (deckt sich mit der Literatur: real,
   seit ~2010 wegkonkurriert).
3. **Was zuverlässig funktioniert:** (a) die **Aktien-Risikoprämie** — schlicht
   halten, hat in jedem Test die beste Rendite geliefert; (b) **Volatilitäts-
   Targeting** als Risikomanagement — halbiert Drawdowns, fügt aber keine Rendite
   hinzu.

**Schlussfolgerung:** Ein Retail-Bot erzeugt aus öffentlichen Preisdaten nach
Kosten keinen verlässlichen Edge. Das ist kein Versagen der Methode — es ist das
Ergebnis, und es stimmt mit Jahrzehnten akademischer Evidenz überein. Das
Framework bleibt bestehen: jede *neue* Hypothese kann in Minuten durch dieselbe
Härte geprüft werden.

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
