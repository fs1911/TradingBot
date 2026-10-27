Bitte baue Finanzradar zu einem persönlichen Werkzeug „Mein Depot“ für einen einzigen Nutzer (mich) um. Bestehende Marktlage-Ampel und Trend-Ampel (monatlich, Tabellen `market_regime`, `asset_trend`) bleiben unverändert und werden wiederverwendet. Grundsatz: Die App macht **keine Kursprognosen und keine Kursziele**. Sie prüft nach festen, getesteten Regeln Risiken und meldet Änderungen.

## 0. Zugang und Datenschutz
- Login per Supabase Auth (nur mein Konto). Alle neuen Tabellen mit Row Level Security: nur `auth.uid() = user_id` darf lesen/schreiben.
- Secrets (Supabase Edge Function Secrets, nie im Frontend): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SEC_CONTACT_EMAIL`.

## 1. Depot-Import aus Yuh
Yuh hat keine API. Import über die CSV-Datei „Account activity export“ (Yuh-App → Account → Documents → Request Document → Account activity export).
- Seite „Depot importieren“: CSV hochladen → Vorschau der ersten 20 Zeilen → **Spalten-Zuordnung** (Datum, Typ/Aktivität, ISIN, Name, Anzahl, Preis, Währung, Betrag). Zuordnung speichern, damit der nächste Import automatisch läuft. Trennzeichen `;` oder `,` automatisch erkennen, Dezimal-Komma und Hochkomma als Tausendertrenner erlauben, Zeichensatz UTF-8 oder Latin-1.
- Nur Käufe/Verkäufe (und Splits, falls vorhanden) übernehmen; doppelte Zeilen beim erneuten Import ignorieren (Schlüssel: Datum + ISIN + Anzahl + Betrag).
- Daraus Bestand je ISIN berechnen (Anzahl, durchschnittlicher Einstand).
- Zusätzlich manuell: Position hinzufügen/ändern/löschen (für Bestände, die nicht im Export sind, z. B. Krypto oder Cash).
- ISIN → Ticker: OpenFIGI `https://api.openfigi.com/v3/mapping` (`idType: ID_ISIN`). Börse wählen in dieser Reihenfolge: Schweiz `exchCode SW` → Yahoo-Suffix `.SW`; Deutschland `GY`/`GR` → `.DE`; USA `US` → ohne Suffix; sonst Hauptbörse. Zuordnung speichern und auf der Positionsseite änderbar machen.

Tabellen:
```sql
create table holdings (
  user_id uuid not null default auth.uid(),
  isin text not null,
  name text, ticker text, yahoo_symbol text,
  asset_type text,            -- 'aktie' | 'etf' | 'krypto' | 'cash' | 'andere'
  home_market text,           -- Zuordnung wie bisher (.SW → Schweiz usw.)
  quantity numeric not null, avg_cost numeric, currency text,
  ter numeric,                -- nur ETFs, manuell eintragbar (in %)
  updated_at timestamptz default now(),
  primary key (user_id, isin)
);
create table transactions (
  user_id uuid not null default auth.uid(),
  trade_date date, isin text, kind text, quantity numeric, price numeric, amount numeric, currency text,
  source_hash text, primary key (user_id, source_hash)
);
```

## 2. Verwässerung / Rückkauf – für alle Aktien (USA, Schweiz, Europa)
Tabelle `company_shares` (ticker, source, filed_or_asof date, shares_now, shares_prior, change, badge, updated_at).
- **US-Aktien (bevorzugt):** SEC companyconcept `https://data.sec.gov/api/xbrl/companyconcept/CIK{10-stellig}/us-gaap/WeightedAverageNumberOfDilutedSharesOutstanding.json` (Ersatz `...SharesOutstandingBasic`), Header `User-Agent: Finanzradar <SEC_CONTACT_EMAIL>`. Neuester 10-K/10-Q; **aktuell und Vorjahr aus derselben `accn`** (gleicher Bericht, gleiche Periodenlänge, `end` 350–380 Tage auseinander). Nie Werte aus verschiedenen Berichten mischen.
- **Alle anderen (Schweiz, Europa) und Ersatz:** Yahoo `https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{SYMBOL}?type=annualOrdinarySharesNumber,quarterlyOrdinarySharesNumber&period1=<vor 3 Jahren>&period2=<heute>`. Aktuell = neuester Wert, Vorjahr = Wert ca. 12 Monate früher (330–400 Tage). **Splits bereinigen:** Splits der letzten 3 Jahre aus `https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}?range=3y&interval=1d&events=splits` holen und den Vorjahreswert mit allen Splits dazwischen multiplizieren.
- `change = aktuell / vorjahr − 1`; |change| ≥ 0,8 → `keine_daten`. `change ≤ −0,02` → 👍 Rückkauf; `change ≥ +0,05` → ⚠️ Verwässerung; sonst neutral. Wert älter als 15 Monate → `keine_daten`.
- Quelle anzeigen („SEC 10-Q vom …“ bzw. „Yahoo, Stand …“). Bei Nicht-US-Aktien Zusatz „Signal in USA getestet, international laut Studien ähnlich“.
- Zusatz „👍 Rückkauf + hohe Qualität“ nur bei US-Aktien mit ROE ≥ 15 % und Cashflow-Deckung ≥ 1 (bestehende Firmenqualität).

## 3. Depot-Übersicht (Startseite)
Pro Position: Name, Wert in CHF (Kurse Yahoo, Devisen über `USDCHF=X`, `EURCHF=X`), Anteil am Depot, Marktlage-Ampel des Heimatmarkts (bzw. Trend-Ampel bei Krypto/Rohstoffen), Verwässerungs-Badge, bei ETFs TER.
Oben drei Kennzahlen mit Warnfarben:
- **Grösste Einzelaktie:** Anteil; ⚠️ wenn > 10 %.
- **Einzelaktien gesamt:** Anteil; ⚠️ wenn > 20 %. Text: „Rund 4 % aller Aktien erzeugten den ganzen Börsengewinn, viele fallen auf null – Einzelaktien klein halten.“
- **Durchschnittliche ETF-Gebühr (gewichtet):** ⚠️ wenn > 0,4 %. Text: „1 % mehr Gebühr kostet über 30 Jahre rund 14 % des Endvermögens.“

## 4. Kauf-Check (eigene Seite + Telegram)
Eingabe: Ticker oder ISIN + Betrag in CHF. Ausgabe genau eine Bewertung mit Gründen (jede Regel als Zeile ✓/✗):
- 🔴 **Abraten**, wenn mindestens eins: ⚠️ Verwässerung; Marktlage-Ampel des Heimatmarkts 🔴; Einzelaktie wäre nach dem Kauf > 10 % des Depots.
- 🟡 **Vorsicht**, wenn mindestens eins (und kein Rot): Marktlage 🟡; Einzelaktien gesamt wären > 20 %; Verwässerung `keine_daten`; ETF mit TER > 0,4 %.
- 🟢 **Kein Einwand**, sonst. Zusätzlich anzeigen, falls zutreffend: „👍 Rückkauf“ bzw. „👍 Rückkauf + hohe Qualität“.
- Für breite Aktien-ETFs (Welt, Region) bei 🟢 oder 🟡 immer den Satz: „Für einen Sparplan gilt: weiterführen. Zeitpunkt-Wahl hat sich in unseren Tests nicht gelohnt.“
Fester Hinweis unter jedem Ergebnis: „Regelbasierte Risikoprüfung, keine Kursprognose. Ein 🟢 heisst nicht, dass die Aktie steigt.“

## 5. Tägliche Prüfung + Telegram
Edge Function `daily-depot-check`, per `pg_cron` täglich 18:30 UTC (nach Börsenschluss Europa) und 22:30 UTC (nach USA). Sie aktualisiert Kurse, Depotwerte und `company_shares` (Verwässerung höchstens 1× pro Woche je Ticker abrufen) und sendet Telegram-Nachrichten **nur bei Ereignissen**. Gesendete Ereignisse in Tabelle `alerts_sent` (user_id, key, sent_at) speichern, damit nichts doppelt kommt:
1. Marktlage-Ampel eines Heimatmarkts meiner Positionen wechselt die Farbe (nur am Monatsende, wenn die Ampel neu berechnet wird).
2. Eine meiner Aktien bekommt neu ⚠️ Verwässerung oder 👍 Rückkauf.
3. Eine Einzelaktie überschreitet 10 % des Depots bzw. Einzelaktien gesamt 20 % (einmal pro Überschreitung).
4. Ein Markt meiner Positionen fällt erstmals ≥ 20 % unter sein Hoch. Text: „Historisch weder besser noch schlechter als sonst; Sparplan weiterführen, kein Kaufsignal.“
5. Datenfehler (Kurs/Import > 3 Tage nicht aktualisiert).
Zusätzlich am **ersten Tag jedes Monats** eine Zusammenfassung: Depotwert, Veränderung Vormonat, Ampeln meiner Märkte, offene Warnungen.
**Keine** täglichen Kauf-/Verkaufsmeldungen und keine Meldungen über normale Kursschwankungen.

Telegram senden: `POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage` mit `chat_id = TELEGRAM_CHAT_ID`, `parse_mode: HTML`.
Telegram-Befehle (Webhook → Edge Function `telegram-webhook`; **nur Nachrichten von `TELEGRAM_CHAT_ID` beantworten**, alle anderen ignorieren):
- `/check TICKER BETRAG` → Kauf-Check wie Abschnitt 4
- `/depot` → Kurzübersicht
- `/ampel` → Ampeln meiner Märkte

## 6. Entfernen
Falls vorhanden: RSI, MACD, Bollinger, Fibonacci, Elliott-Wellen, Einstiegszonen, Unterstützung/Widerstand, „Smart-Money“/Guru-Nachkauf, „Crash = Kaufsignal“, Kursziele, „Überbewertet = Verkaufen“, tägliche Kauf-/Verkaufssignale für einzelne Aktien. Die Wörter „Kaufsignal“, „Kursziel“, „sicher“, „schlägt den Markt“ nur verneint verwenden.

## 7. Prüfung
- Verwässerung: 97 Mio / 100 Mio → −3 % → 👍; 106 / 100 → ⚠️; 101 / 100 → neutral. Yahoo-Fall mit 2:1-Split dazwischen: 200 Mio jetzt / 100 Mio vor Split → nach Bereinigung 0 % → neutral.
- Kauf-Check: Einzelaktie mit Ziel-Anteil 12 % → 🔴 mit Grund „> 10 % des Depots“.
- Doppelter CSV-Import erzeugt keine doppelten Transaktionen.
- Telegram-Nachricht von fremder Chat-ID → keine Antwort.
- Gleiches Ereignis wird nicht zweimal gemeldet.
