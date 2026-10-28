# Forschungsplan — was noch offen ist

Ziel: forschen, bis es nichts Sinnvolles mehr zu prüfen gibt (Mathematik, Daten, Annahmen,
Hypothesen). Jede Hypothese wird vorab festgelegt, mit Kosten, Out-of-sample und Placebo bzw.
Mehrfachtest-Korrektur geprüft und in `RESEARCH.md` eingetragen. Gebaut wird erst danach
(`docs/BUILD_BACKLOG.md`).

Abgeschlossen: #1–#63 (siehe RESEARCH.md).

## Block A — Prüfung der eigenen Werkzeuge
| # | Hypothese / Frage | Daten | Status |
|---|---|---|---|
| 64 | Verwässerung/Rückkauf funktioniert auch bei Schweizer und europäischen Aktien | Yahoo-Aktienzahlen (fundamentals-timeseries), SMI/Mid Caps, DAX, CAC, AEX | läuft |
| 65 | Kauf-Check 🟢/🟡/🔴: fahren 🟢-Käufe besser als 🔴-Käufe? Welche Einzelregel trägt? | #47-Ampel, #50b-Signal (US 2010–2025) | läuft |
| 66 | Läuft der Bot wie im Backtest (#44)? Abweichung, Gebühren, Ausführung | Bot-Logs, Alpaca-Fills, Yahoo | **ans Ende verschoben**: Portfolio-Modus erst seit 1.10.2026 (1 Umschichtung) — braucht ≥ 6–12 Monate Live-Daten |

## Block B — Fragen eines Schweizer Privatanlegers
| # | Hypothese / Frage | Daten | Status |
|---|---|---|---|
| 67 | Währungsabsicherung: MSCI World in CHF gesichert vs ungesichert — lohnt Hedging? | Yahoo-Indizes, USD/CHF, EUR/CHF, Zinsdifferenzen | geplant |
| 68 | Heimatmarkt: SMI/SPI vs Welt aus CHF-Sicht; optimaler CH-Anteil | Yahoo | geplant |
| 69 | Hebel: 1,5×/2×/3× täglich gehebelt (wie Leveraged-ETFs) vs Index, Volatilitätsverlust, Finanzierungskosten, seit 1928 | Yahoo ^GSPC, ^IRX | läuft |
| 70 | Einmalanlage vs Sparplan (gestaffelt) bei gleichem Geld | Shiller, Yahoo | läuft |
| 71 | Aktien/Anleihen-Mischung und Umschichtungs-Bänder (60/40, 80/20, 100/0) für CHF-Anleger | Yahoo, Shiller | geplant |
| 72 | Entnahme im Ruhestand: „4 %-Regel“, Reihenfolge-Risiko, international | Shiller, Yahoo | läuft |
| 73 | Kostenmathematik Yuh & Co.: Courtage, Devisenaufschlag, Stempelsteuer, Handelsfrequenz → Endvermögen | Annahmen (öffentliche Gebührenlisten) | geplant |
| 74 | Optimale Anzahl Einzelaktien: Risiko- und Ergebnis-Streuung bei 1–50 Titeln (Mathematik + echte Daten) | #58-Daten, Yahoo | geplant |

## Block C — weitere bekannte Anomalien (öffentliche Daten)
| # | Hypothese / Frage | Daten | Status |
|---|---|---|---|
| 75 | Kursreaktion nach Gewinnüberraschung (Post-Earnings-Drift) | SEC 10-Q EPS (saisonaler Random Walk) + Yahoo | geplant |
| 76 | Insider-VERKÄUFE als Warnsignal (Gegenstück zu #48) | SEC Form-4-Datensätze | geplant |
| 77 | Leerverkaufs-Quote (Short Interest) als Warnsignal | FINRA Short-Interest-Dateien (öffentlich) | Datenzugang prüfen |
| 78 | Börsengänge (IPOs) schneiden langfristig schlechter ab | SEC S-1/424B-Daten + Yahoo | Datenzugang prüfen |
| 79 | Dividenden: Dividendenstarter/-erhöher, „Dividenden-Aristokraten“ vs Index | SEC/Yahoo-Dividenden | geplant |
| 80 | Index-Aufnahme-Effekt (S&P 500 / SMI) | öffentliche Änderungslisten | Datenzugang prüfen |

## Block D — Mathematik / Risiko
| # | Hypothese / Frage | Daten | Status |
|---|---|---|---|
| 81 | Positionsgrösse: Kelly-Kriterium, Ruin-Risiko, Volatilitätsverlust („Varianz-Drag“) | Mathematik + Simulation | läuft |
| 82 | Fat Tails: wie oft kommen Extremtage wirklich vor vs Normalverteilung; was heisst das für Stopps und Hebel? | Yahoo seit 1928 | läuft |
| 83 | Regime: gibt es stabile „Marktphasen“ (Hidden-Markov), und helfen sie out-of-sample? | Yahoo, Shiller | geplant |

## Am Schluss
| # | Was |
|---|---|
| 84 | Gesamtbilanz: alle Experimente in einem Register, Mehrfachtest-Korrektur über das ganze Projekt neu (Update von #57) |
