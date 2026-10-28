# Bau-Liste (erst nach Abschluss der Forschung)

Vereinbarung (28.10.2026): **Zuerst wird alles erforscht, gebaut wird erst am Schluss.**
Hier wird alles gesammelt, was nach der Forschung umzusetzen ist, mit dem Experiment, aus dem es stammt.
Nichts davon wird vorher gebaut oder an Lovable geschickt.

## Finanzradar / „Mein Depot“ (Lovable)
| # | Was | Grundlage | Stand |
|---|---|---|---|
| B1 | Prompt `docs/finanzradar/LOVABLE_PROMPT_MEIN_DEPOT.md` an Lovable schicken (nur mit OK des Nutzers, kostet Credits) | #45–#47, #50/#50b, #55, #58 | Prompt fertig, vor dem Senden mit den Ergebnissen von #64/#65 aktualisieren |
| B2 | Verwässerungs-/Rückkauf-Hinweis für CH/EU-Aktien: nur einbauen bzw. so beschriften, wie #64 es stützt | #50, #50b, #64 | wartet auf #64 |
| B3 | Kauf-Check-Regeln (🟢/🟡/🔴) an die Ergebnisse von #65 anpassen (Schwellen, welche Regeln überhaupt zählen) | #65 | wartet auf #65 |
| B4 | Bewertung (CAPE) nur als Info „Erwartung nächste 10 Jahre“ anzeigen, nie als Kauf-/Verkaufs-Zeitpunkt | #34, #61 | offen |
| B5 | Keine „KI-Bewertung“ / kein Score aus vielen Merkmalen — ein klares Signal (Rückkauf/Verwässerung) genügt | #62 | offen |
| B6 | Crash-Hinweis nur als Beruhigungstext, kein Kaufsignal; kein „Kriegskasse“-Feature | #53, #54 | im Prompt enthalten |
| B7 | Klumpen-Warnung (Einzelaktie > 10 %, Einzelaktien gesamt > 20 %) | #58 | im Prompt enthalten |
| B8 | Gebühren-Check (ETF-TER > 0,4 %) | #55 | im Prompt enthalten |

## Was der Nutzer selbst einrichten muss (vor B1)
| # | Was |
|---|---|
| U1 | Telegram-Bot via @BotFather, Chat-ID via @userinfobot → Secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` in Supabase/Lovable |
| U2 | Secret `SEC_CONTACT_EMAIL` in Supabase/Lovable (nie ins öffentliche Repo) |
| U3 | Yuh-CSV „Account activity export“ anfordern; Kopfzeile (Beträge geschwärzt) schicken, damit die Spalten-Zuordnung fest eingebaut werden kann |

## Bot (TradingBot, Alpaca Paper)
| # | Was | Grundlage | Stand |
|---|---|---|---|
| B9 | Allfällige Anpassungen am Trend-Portfolio nach dem Abgleich Live vs. Backtest | #44, #66 | wartet auf #66 |

## Repo
| # | Was | Stand |
|---|---|---|
| B10 | README mit allen Ergebnissen auf einer Seite (öffentliches Repo verständlich machen); prüfen, dass nichts Privates drinsteht | optional, am Schluss |
