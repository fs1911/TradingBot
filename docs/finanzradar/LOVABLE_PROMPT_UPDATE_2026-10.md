Bitte erweitere Finanzradar um die folgenden Punkte. Bestehende Ampeln (Marktlage, Trend), Datenquellen und Tabellen bleiben unverändert. Grundsatz bleibt: keine Kauf-/Verkaufsbefehle, keine Kursziele, keine Versprechen, den Markt zu schlagen.

## 1. Rückkauf / Verwässerung (nur US-Aktien)
Neue Tabelle:
```sql
create table company_shares (
  ticker text primary key,
  form text,            -- '10-K' | '10-Q'
  filed date,
  period_end date,
  shares_now numeric, shares_prior numeric,
  change numeric,       -- shares_now / shares_prior - 1
  badge text,           -- 'rueckkauf' | 'verwaesserung' | 'neutral' | 'keine_daten'
  updated_at timestamptz default now()
);
```
Berechnung serverseitig (Edge Function, wöchentlich, nur angezeigte/gesuchte Ticker; gleicher SEC-User-Agent `Finanzradar <SEC_CONTACT_EMAIL>` wie bei der Firmenqualität, max. 10 Anfragen/Sekunde):
- Ticker → CIK über `https://www.sec.gov/files/company_tickers.json`.
- Abruf `https://data.sec.gov/api/xbrl/companyconcept/CIK{10-stellig}/us-gaap/WeightedAverageNumberOfDilutedSharesOutstanding.json`; falls leer: `.../WeightedAverageNumberOfSharesOutstandingBasic.json`. Werte unter `units.shares`.
- Neuesten Bericht (`form` = `10-K` oder `10-Q`, nach `filed`) wählen. Nur Einträge mit **derselben `accn`** verwenden (wegen Aktiensplits nie Werte aus verschiedenen Berichten kombinieren).
- Periodenlänge = `end − start`: 10-K 330–400 Tage, 10-Q 80–100 Tage. **Aktuell** = Periode mit spätestem `end`; **Vorjahr** = gleiche Periodenlänge, `end` 350–380 Tage früher.
- `change = aktuell / vorjahr − 1`. Wenn |change| ≥ 0,8 → `keine_daten`.
- `change ≤ −0,02` → `rueckkauf`; `change ≥ +0,05` → `verwaesserung`; sonst `neutral`.
- Gültig 12 Monate ab `filed`; älter → nicht anzeigen.

Anzeige auf der Einzelaktien-Seite (US), unter „Firmenqualität“: „Aktienanzahl 12 M: −3,1 % 👍 Rückkauf“ (bzw. „⚠️ Verwässerung“ oder nur die Zahl bei neutral), darunter klein „aus 10-Q vom 2026-08-01“. Zusätzlich „👍 Rückkauf + hohe Qualität“, wenn Rückkauf **und** ROE ≥ 15 % **und** Cashflow-Deckung ≥ 1. Keine Ampelfarbe, kein Button.

Texte (wörtlich, im „Info“-Aufklapper):
- 👍 Rückkauf: „Die Firma hat in den letzten 12 Monaten mindestens 2 % ihrer Aktien zurückgekauft. Solche Firmen lagen 2009–2026 im Schnitt rund 2 % pro Jahr vor vergleichbaren Firmen. Das ist ein Durchschnitt über hunderte Firmen, keine Garantie für diese Aktie – und kein Versprechen, den Index zu schlagen.“
- ⚠️ Verwässerung: „Die Firma hat mindestens 5 % neue Aktien ausgegeben. Bestehende Aktionäre besitzen dadurch einen kleineren Anteil. Solche Firmen lagen im Schnitt rund 3 % pro Jahr zurück. Ausnahmen gibt es (z. B. gerettete Firmen), aber das Risiko ist höher.“
- Firmenqualität (ersetzt den bisherigen Text): „Information zur Finanzkraft der Firma. Allein lagen profitable Firmen in unseren Tests nur leicht vorne (+0,5 % pro Jahr, nicht gesichert). Zusammen mit Aktienrückkäufen war der Vorsprung grösser. Kein Kaufsignal.“

## 2. Crash-Hinweis (Aktienmärkte)
In der monatlichen Berechnung zusätzlich pro Markt: `abstand_vom_hoch = Monatsendkurs / höchster Monatsendkurs der geladenen Historie − 1` (Historie mindestens 10 Jahre laden). Spalte `drawdown numeric` in `market_regime` ergänzen. Wenn ≤ −0,20: Hinweisbox unter der Marktlage-Karte. Ändert die Ampel **nicht**.
Text: „Dieser Markt liegt mehr als 20 % unter seinem Höchststand. Historisch waren die Renditen nach solchen Einbrüchen weder deutlich besser noch schlechter als sonst. Wer einen Sparplan hat, fuhr meist am besten, ihn einfach weiterzuführen – Geld zurückzuhalten, um ‚unten‘ zu kaufen, lohnte sich fast nie. Kein Kaufsignal.“

## 3. Sparplan-Rechner (neue Seite „Sparplan“)
Daten: Datei `sp500_real_monthly.json` unter `public/data/` ablegen. Inhalt von: https://raw.githubusercontent.com/fs1911/TradingBot/claude/trading-bot-setup-qb6687/docs/finanzradar/sp500_real_monthly.json (Felder `start`, `end`, `returns` = reale monatliche Gesamtrenditen des S&P 500 ab 1871-02 als Dezimalzahlen). Falls die Datei nicht ins Projekt kopiert werden kann, im Browser von dieser URL laden.

Eingaben: Betrag pro Monat (Standard 500), Jahre (5–50, Standard 30), Fondsgebühr TER in % (Standard 0,2).
Berechnung im Browser, für jeden Startmonat im Abstand von 12 Monaten, solange genug Daten vorhanden:
`Vermögen = 0`, dann für jeden Monat mit Rendite r: `Vermögen = (Vermögen + Betrag) × (1 + r) × (1 − TER/100/12)`.
Anzeige: eingezahlt; schlechtester Verlauf, 10 %, Median, 90 %, bester (Beschriftung „in heutiger Kaufkraft“); kleines Histogramm der Endwerte; zwei Vergleichszeilen: „mit 1 % höherer Gebühr: Median −x %“ und „10 Jahre länger: Median +y %“.
Prüfwert: 500 / 30 Jahre / 0,2 % → Median ≈ 535 000, schlechtester ≈ 206 000; mit TER 2 % Median ca. 29 % tiefer.
Text: „Berechnet mit der echten Entwicklung des S&P 500 seit 1871, nach Inflation. Die Spanne zeigt, wie unterschiedlich es je nach Startjahr lief. Am meisten bewirken: früh anfangen, mehr sparen, tiefe Gebühren. Vergangene Renditen garantieren keine zukünftigen.“

## 4. Neue Info-Seite „Was wir getestet haben“
Einfache Tabelle:
| Idee | Ergebnis |
|---|---|
| Chartmuster, RSI, MACD, Fibonacci, Elliott-Wellen | Nicht besser als Zufall |
| Insider-Käufe nachmachen | Kein Vorteil |
| Berkshire / Hedgefonds nachkaufen | Schlechter als der S&P 500 (2013–2026) |
| Nach Crashs kaufen / Geld für Crashs zurückhalten | Kein Vorteil / meist schlechter |
| Faktor-ETFs (Momentum, Qualität, Value) statt MSCI World | Seit 2011 kein verlässlicher Vorsprung |
| Marktlage-Ampel (Trend + Wirtschaft) | Grosse Verluste in Rezessionen deutlich kleiner |
| Aktienrückkäufe | Rund +2 % pro Jahr im Schnitt |
| Sparrate, Anlagedauer, Gebühren | Wirken stärker als jede getestete Strategie |
Darunter: „Grundlage: 56 Tests mit Daten bis 2026. Keine Anlageberatung.“

## 5. Entfernen / nicht einbauen
Falls vorhanden entfernen: Elliott-Wellen, Einstiegszonen, „Smart-Money“- oder Guru-/Hedgefonds-Nachkauf, „Crash = Kaufsignal“, Aussagen „schlägt den Markt“. Die Wörter „Kaufsignal“, „Kursziel“, „sicher“, „schlägt den Markt“ dürfen nirgends als Versprechen erscheinen (nur verneint in Hinweisen wie „Kein Kaufsignal“).

## Prüfung
- Rückkauf: 97 Mio / 100 Mio → −3 % → 👍; 106 / 100 → ⚠️; 101 / 100 → neutral; Bericht älter als 12 Monate → nichts anzeigen.
- Sparplan-Prüfwerte wie oben.
- Crash-Hinweis erscheint nur bei Abstand vom Hoch ≤ −20 %.
