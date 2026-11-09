# Bau-Liste (erst nach Abschluss der Forschung)

Vereinbarung (28.10.2026): **Zuerst wird alles erforscht, gebaut wird erst am Schluss.**
Hier wird alles gesammelt, was nach der Forschung umzusetzen ist, mit dem Experiment, aus dem es stammt.
Nichts davon wird vorher gebaut oder an Lovable geschickt.

## Finanzradar / „Mein Depot“ (Lovable)
| # | Was | Grundlage | Stand |
|---|---|---|---|
| B1 | Prompt `docs/finanzradar/LOVABLE_PROMPT_MEIN_DEPOT.md` an Lovable schicken (nur mit OK des Nutzers, kostet Credits) | #45–#47, #50/#50b, #55, #58 | Prompt fertig, vor dem Senden mit den Ergebnissen von #64/#65 aktualisieren |
| B2 | Verwässerungs-/Rückkauf-Hinweis für CH/EU-Aktien mit Beschriftung „nur in den USA getestet“ (#64: mit Gratis-Daten nicht prüfbar) | #50, #50b, #64 | entschieden |
| B3 | Kauf-Check anpassen: Verwässerung ≥5 % → 🔴 (halbiert Desaster-Quote 10,2 % → ~5 %); Marktampel rot beim Kauf nur 🟡 (Zeitpunkt hilft nicht, 2020 +39 %); Beschriftung „senkt Totalausfall-Risiko, keine Mehrrendite“ | #65 | entschieden |
| B4 | Bewertung (CAPE) nur als Info „Erwartung nächste 10 Jahre“ anzeigen, nie als Kauf-/Verkaufs-Zeitpunkt | #34, #61 | offen |
| B5 | Keine „KI-Bewertung“ / kein Score aus vielen Merkmalen — ein klares Signal (Rückkauf/Verwässerung) genügt | #62 | offen |
| B6 | Crash-Hinweis nur als Beruhigungstext, kein Kaufsignal; kein „Kriegskasse“-Feature | #53, #54 | im Prompt enthalten |
| B7 | Klumpen-Warnung (Einzelaktie > 10 %, Einzelaktien gesamt > 20 %) | #58 | im Prompt enthalten |
| B8 | Gebühren-Check (ETF-TER > 0,4 %) | #55 | im Prompt enthalten |

| B11 | Warnung bei häufigem Handeln (Umschlag > 50 %/Jahr ≈ −16 % Endvermögen) und TER-Vergleich prominent; Devisen-Aufschlag beim Kauf zweitrangig | #73 | offen |
| B12 | Keine Hebel-Produkte im Kauf-Check ohne deutliche Warnung (2×/3× bis −98/−100 % seit 1928) | #69 | offen |

| B13 | Hinweis „hohe Zufalls-Streuung“ bei weniger als ~20 Einzelaktien (#74); Umschicht-Hinweis 1×/Jahr oder bei ±10 Pkt (#71) | #71, #74 | offen |
| B14 | Währung: Info, dass Absicherung für USD-Anteile historisch Rendite kostete, für EUR-Anteile half (Rückschau, keine Regel) | #67 | offen |

## Was der Nutzer selbst einrichten muss (vor B1)
| # | Was |
|---|---|
| U1 | OPTIONAL (9.11.: App hat bereits Web-Push) — nur falls Meldungen lieber per Telegram: Bot via @BotFather, Chat-ID via @userinfobot → Secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` in Lovable |
| U2 | ENTFÄLLT (9.11.: App fragt SEC bereits mit eigenem User-Agent ab, `src/lib/sec.server.ts`) |
| U3 | ENTFÄLLT (9.11.: Positionen inkl. Anzahl/Einstand sind in der App schon erfasst, `watchlist_items`; YUH-Universum vorhanden). Der Prompt „Mein Depot“ muss auf die bestehende App zugeschnitten werden (kein CSV-Import, keine neue `holdings`-Tabelle) |

## Bot (TradingBot, Alpaca Paper)
| # | Was | Grundlage | Stand |
|---|---|---|---|
| B9 | Allfällige Anpassungen am Trend-Portfolio nach dem Abgleich Live vs. Backtest | #44, #66 | wartet auf #66 |

## Repo
| # | Was | Stand |
|---|---|---|
| B10 | README mit allen Ergebnissen auf einer Seite (öffentliches Repo verständlich machen); prüfen, dass nichts Privates drinsteht | optional, am Schluss |

## Abgrenzung zu ähnlichen Apps (z. B. foliologic.app)
Foliologic zeigt Qualitäts-Score, fairen Wert, ETF-Score und KI-Texte — ausdrücklich ohne Kursaussage. „Mein Depot“ soll sich auf das konzentrieren, was in unseren Tests nachweislich zählt: Rückkauf/Verwässerung, Marktampel, Klumpen- und Gebühren-Warnung. Qualitäts- oder Bewertungs-Scores höchstens als Info (#49, #62, #85).

## Aus #76–#86 (31.10.2026)
- **B15 Kauf-Check: Warnhinweis „Börsengang < 3 Jahre“** (#78: 73 % der IPOs nach 3 J. im Minus, Median −102 Pkt vs SPY). Hinweis, keine harte Sperre.
- **B16 Info-Karte „Was passierte nach …“** (#86): Grundraten nach VIX > 40, −20 %, Kriegen, Zinskurve — gegen Panikverkäufe; ausdrücklich keine Prognose.
- **B17 optionale Info-Felder** (#75/#76/#77): letzte Gewinnüberraschung, gehäufte Insider-Verkäufe, stark leerverkauft — nur Info, kein Einfluss auf die Ampel (alle nicht signifikant).
- **B18 Bot: ungetestetes News-Stimmungs-Filter entfernen** (src/data/news_sentiment.py + `_sentiment_filter`): #87 zeigt keinen Nutzen nach Veröffentlichung; derzeit mangels API-Schlüssel ohnehin wirkungslos.
