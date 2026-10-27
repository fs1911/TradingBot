# Finanzradar – Spezifikation „Marktlage- & Trend-Ampel“

> Zum Einfügen in Lovable. Grundlage: 56 Experimente im Projekt TradingBot (RESEARCH.md).
> Stand: Oktober 2026 (Update: Rückkauf-Hinweis, Sparplan-Rechner, Crash-Hinweis, Info-Seite „Was wir getestet haben“).
> Jede Regel hier wurde getestet; die Nummern (#45, #46 …) verweisen auf das Experiment.

---

## 0. Grundsätze (bitte strikt einhalten)

1. Die App gibt **keine Kauf-/Verkaufsbefehle für einzelne Aktien**. Sie zeigt **Ampeln**
   (Marktlage, Trend) und **Informationen** (Firmenqualität, Rückkauf/Verwässerung, Bewertung).
   Die App verspricht nie, den Markt zu schlagen: In 56 Tests gab es keine verlässliche
   Kurs-Prognose (#42, #51, #53, #56). Ihr Nutzen ist **Risiko erkennen und Fehler vermeiden**.
2. Alle Signale werden **einmal pro Monat am Monatsende** berechnet und gespeichert.
   Nicht täglich neu berechnen – tägliche Signale erzeugen viele Fehlsignale.
3. Berechnung **serverseitig** (Supabase Edge Function + geplanter Job), nicht im Browser
   (Yahoo/FRED blockieren Browser-Anfragen per CORS, API-Schlüssel bleiben geheim).
4. Jede Ampel zeigt ein **„Warum?“** (welche Teilbedingungen erfüllt sind) und einen
   **ehrlichen Hinweis** zu Stärken und Grenzen (Texte in Abschnitt 6).
5. Folgende bisherigen Funktionen **entfernen** (siehe Abschnitt 7): RSI, MACD, Bollinger,
   Fibonacci, Unterstützung/Widerstand, Ausbruchssignale, Kalender-Signale,
   „Überbewertet = Verkaufen“.

---

## 1. Datenquellen (alle kostenlos)

| Daten | Quelle | Symbol / Serie | Hinweis |
|---|---|---|---|
| Index- und ETF-Kurse (Monatsende, dividendenbereinigt wo möglich) | Yahoo Finance Chart-API `https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}?range=3y&interval=1d` | siehe Abschnitt 2 | `adjclose` verwenden, sonst `close`. User-Agent setzen. |
| Geldmarktzins (Cash-Hürde) | Yahoo | `^IRX` (13-Wochen T-Bill, Jahreszins in %) | |
| 10-jährige US-Zinsen | Yahoo | `^TNX` (in %) | |
| Kreditstress-Indikator | Yahoo | `VWEHX` (Hochzins-Anleihenfonds) und `VFITX` (Staatsanleihenfonds) | genau so getestet (#46) |
| US-Arbeitslosenquote | FRED `UNRATE` (kostenloser API-Key, als Secret `FRED_API_KEY`) – Ersatz: BLS-API Serie `LNS14000000` | | monatlich, erscheint ca. 1. Freitag des Folgemonats |
| Aktienanzahl USA (Rückkauf/Verwässerung) | SEC `https://data.sec.gov/api/xbrl/companyconcept/CIK{10-stellig}/us-gaap/WeightedAverageNumberOfDilutedSharesOutstanding.json` (Ersatz: `WeightedAverageNumberOfSharesOutstandingBasic`) | Einheit `shares` | gleicher User-Agent/Limit wie unten |
| Sparplan-Rechner | statische Datei `sp500_real_monthly.json` (reale S&P-500-Gesamtrendite pro Monat 1871–2023, Shiller) | | im Projekt ablegen (`public/data/`), wird nicht abgerufen |
| Firmenkennzahlen USA (nur Info) | SEC `https://data.sec.gov/api/xbrl/companyfacts/CIK{10-stellig}.json`, Ticker→CIK über `https://www.sec.gov/files/company_tickers.json` | `NetIncomeLoss`, `StockholdersEquity`, `NetCashProvidedByUsedInOperatingActivities` | SEC verlangt Header `User-Agent: Finanzradar <kontakt-email>` (Secret `SEC_CONTACT_EMAIL`), max. 10 Anfragen/Sekunde |

---

## 2. Märkte und Anlagen

**Märkte für die Marktlage-Ampel:**

| Markt | Yahoo-Symbol |
|---|---|
| USA | `^GSPC` (S&P 500) |
| USA Technologie | `^IXIC` (Nasdaq) |
| Schweiz | `^SSMI` (SMI) |
| Deutschland | `^GDAXI` (DAX) |
| Europa | `^STOXX50E` (Euro Stoxx 50) |
| Japan | `^N225` |
| Welt | `VT` (Vanguard Total World) |
| Schwellenländer | `EEM` |

**Zuordnung Einzelaktie → Heimatmarkt** (nach Börsenkürzel):
`.SW` → Schweiz · `.DE`/`.F` → Deutschland · `.PA` `.AS` `.MI` `.MC` `.BR` → Europa ·
`.T` → Japan · ohne Suffix (US-Börsen) → USA · alles andere → Welt.

**Anlageklassen für die Trend-Ampel** (ohne Wirtschafts-Teil):
Rohstoffe (z. B. `DBC`, `GLD`, `SLV`, `USO`), Anleihen (`TLT`, `IEF`, `LQD`, `HYG`),
Immobilien (`VNQ`), Krypto (`BTC-USD`, `ETH-USD`). Aktien-ETFs (Welt, Region, Land)
verwenden die **Marktlage-Ampel** ihres Marktes.

---

## 3. Berechnung (monatlich, am letzten Handelstag des Monats)

### 3.1 Monatsendkurse
Für jedes Symbol: letzter verfügbarer Tageskurs jedes Kalendermonats.

### 3.2 Cash-Rendite über h Monate
Monatlicher Cash-Ertrag im Monat m = `IRX(Monatsende m−1) / 100 / 12`.
Cash-Rendite über h Monate = Produkt `(1 + Cash-Ertrag)` der letzten h Monate − 1.

### 3.3 Trend-Score (0–3)   *(#45, #44)*
Für h ∈ {3, 6, 12} Monate:
`Rendite_h = Kurs(t) / Kurs(t−h) − 1`
`Bedingung_h erfüllt`, wenn `Rendite_h > Cash-Rendite_h`.
**Trend-Score = Anzahl erfüllter Bedingungen (0, 1, 2 oder 3).**
Nur berechnen, wenn mindestens 12 Monate Historie vorhanden sind.

### 3.4 Wirtschafts-Stress (nur USA-Daten, gilt für alle Aktienmärkte)   *(#46)*
Drei Indikatoren, jeweils `true`/`false`:

1. **Arbeitslosigkeit:** letzter **veröffentlichter** UNRATE-Wert (also Vormonat) >
   Durchschnitt der letzten 12 veröffentlichten Werte (inklusive dieses Werts).
2. **Kreditstress:** `Verhältnis = Kurs(VWEHX) / Kurs(VFITX)` am Monatsende;
   Stress, wenn `Verhältnis(t) <` Durchschnitt der letzten 12 Monatsend-Verhältnisse.
3. **Zinskurve:** `TNX − IRX` am Monatsende; Stress, wenn dieser Wert in **einem der letzten
   12 Monate** (inkl. aktuell) **kleiner als 0** war.

**Wirtschafts-Stress = mindestens 2 der 3 Indikatoren sind `true`.**
Fehlt ein Indikator (Datenfehler): mit den verfügbaren rechnen; sind nur 0–1 verfügbar →
Stress = `unbekannt`, dann wird wie „Stress“ behandelt und in der App vermerkt.

### 3.5 Marktlage-Ampel (Aktienmärkte, Aktien-ETFs, Einzelaktien)   *(#46, #47)*

| Ampel | Bedingung |
|---|---|
| 🟢 **Rückenwind** | Trend-Score ≥ 2 |
| 🟡 **Korrektur** | Trend-Score ≤ 1 **und kein** Wirtschafts-Stress |
| 🔴 **Gefahr** | Trend-Score ≤ 1 **und** Wirtschafts-Stress |

### 3.6 Trend-Ampel (Rohstoffe, Anleihen, Immobilien, Krypto)   *(#45)*

| Ampel | Bedingung |
|---|---|
| 🟢 **Rückenwind** | Trend-Score = 3 |
| 🟡 **Gemischt** | Trend-Score 1 oder 2 |
| 🔴 **Gegenwind** | Trend-Score = 0 |

Für Gold, Silber und Währungen zusätzlich den Hinweis „geringe Aussagekraft“ anzeigen
(in #45 kein Nutzen bei diesen Klassen).

### 3.7 Firmenqualität (nur Information, nur US-Aktien)   *(#49, #43)*
Aus dem letzten Geschäftsjahr (10-K, Formular `10-K`, Einheit USD):
- **Eigenkapitalrendite (ROE)** = NetIncomeLoss / StockholdersEquity (nur wenn Eigenkapital > 0)
- **Cashflow-Deckung** = NetCashProvidedByUsedInOperatingActivities / NetIncomeLoss (nur wenn Gewinn > 0)

Anzeige als Textbausteine, **ohne Ampelfarbe und ohne Kaufempfehlung**:
- ROE ≥ 15 % → „hohe Eigenkapitalrendite“; 5–15 % → „mittlere“; < 5 % → „niedrige“
- Cashflow-Deckung ≥ 1 → „Gewinn durch Cashflow gedeckt“; < 1 → „Gewinn nicht voll durch Cashflow gedeckt“

### 3.7b Rückkauf / Verwässerung (nur US-Aktien)   *(#50, #50b)*
Aus dem **neuesten** Bericht (Formular `10-K` oder `10-Q`) mit beiden Werten:
- Aus der companyconcept-Antwort (`units.shares`) alle Einträge mit derselben `accn` (= derselbe Bericht) nehmen.
- **Aktuell** = Wert der Periode mit dem spätesten `end`; **Vorjahr** = Wert derselben Periodenlänge,
  deren `end` 350–380 Tage früher liegt. Beide aus **demselben Bericht** – so sind Aktiensplits
  bereits herausgerechnet. Bei 10-K: Perioden ~1 Jahr (330–400 Tage); bei 10-Q: Quartal (80–100 Tage).
- `Veränderung = Aktuell / Vorjahr − 1`. Nur werten, wenn |Veränderung| < 80 % (sonst Datenfehler → „keine Daten“).
- Gültig 12 Monate ab Einreichdatum (`filed`); älter → „veraltet“, nicht anzeigen.

| Hinweis | Bedingung |
|---|---|
| 👍 **Rückkauf** | Veränderung ≤ −2 % |
| ⚠️ **Verwässerung** | Veränderung ≥ +5 % |
| neutral (kein Badge, nur Zahl) | dazwischen |

Zusatz „👍 Rückkauf + hohe Qualität“, wenn Rückkauf **und** ROE ≥ 15 % **und** Cashflow-Deckung ≥ 1
(#50: Kombination +3,1 %/Jahr). Keine Ampelfarbe, kein Kaufbutton.

### 3.7c Crash-Hinweis (Aktienmärkte)   *(#53, #54)*
`Abstand vom Hoch = Monatsendkurs / höchster Monatsendkurs bisher − 1` (gesamte geladene Historie,
mindestens 10 Jahre). Wenn ≤ −20 %: Hinweisbox (Text in Abschnitt 6) unter der Marktlage-Ampel.
**Kein Kaufsignal**, ändert die Ampel nicht.

### 3.8 Bewertung (nur Information)   *(#34)*
Bestehende Bewertungsanzeige (KGV/CAPE) behalten, aber **umbenennen** von
„Überhitzt / Verkaufen“ zu **„Bewertung (langfristig)“** mit Text aus Abschnitt 6.
Darf die Ampel **nicht** beeinflussen.

---

## 4. Datenbank (Supabase)

```sql
create table market_regime (
  month date not null,              -- letzter Tag des Monats
  market text not null,             -- z. B. 'USA', 'Schweiz'
  symbol text not null,
  trend_score int not null,         -- 0..3
  h3 boolean, h6 boolean, h12 boolean,
  stress_unemployment boolean, stress_credit boolean, stress_curve boolean,
  macro_stress text not null,       -- 'ja' | 'nein' | 'unbekannt'
  light text not null,              -- 'gruen' | 'gelb' | 'rot'
  computed_at timestamptz default now(),
  primary key (month, market)
);

create table asset_trend (
  month date not null,
  symbol text not null,
  asset_class text not null,        -- 'rohstoff' | 'anleihe' | 'immobilien' | 'krypto'
  trend_score int not null,
  h3 boolean, h6 boolean, h12 boolean,
  light text not null,
  computed_at timestamptz default now(),
  primary key (month, symbol)
);

create table company_shares (
  ticker text primary key,
  form text,                        -- '10-K' | '10-Q'
  filed date,
  period_end date,
  shares_now numeric, shares_prior numeric,
  change numeric,                   -- shares_now / shares_prior - 1
  badge text,                       -- 'rueckkauf' | 'verwaesserung' | 'neutral' | 'keine_daten'
  updated_at timestamptz default now()
);

create table company_quality (
  ticker text primary key,
  fiscal_year int,
  roe numeric, cashflow_cover numeric,
  updated_at timestamptz default now()
);
```

**Job:** Edge Function `compute-monthly-signals`, per `pg_cron` täglich um 22:30 UTC
aufrufen; sie rechnet nur, wenn heute der letzte Handelstag des Monats ist **oder** für den
abgelaufenen Monat noch kein Eintrag existiert (Nachholen). Ergebnisse per `upsert` speichern.
`company_quality` und `company_shares` einmal pro Woche aktualisieren (nur angezeigte/gesuchte Ticker).

---

## 5. Anzeige

**Startseite – „Marktlage“:** Karte pro Markt mit Ampel, Name, Datum der Berechnung
(„Stand: Ende September 2026, nächste Aktualisierung: Ende Oktober“).

**Detail „Warum?“ (aufklappbar):**
- Trend: 3 Zeilen „3 Monate ✓/✗ · 6 Monate ✓/✗ · 12 Monate ✓/✗ (Rendite vs. Geldmarkt)“
- Wirtschaft (nur Aktienmärkte): 3 Zeilen „Arbeitslosigkeit steigt ✓/✗ · Kreditstress ✓/✗ ·
  Zinskurve invertiert (12 M) ✓/✗“ und Ergebnis „Wirtschafts-Stress: ja/nein“
- Verlauf: Ampelfarben der letzten 24 Monate als Farbbalken

**Einzelaktie:** oben die **Marktlage-Ampel des Heimatmarkts** („Marktlage Schweiz: 🟡 Korrektur“),
darunter „Firmenqualität“ (nur US) und „Bewertung (langfristig)“. **Keine** Kauf-/Verkaufsbuttons
oder -labels, keine aktienspezifischen Signale.

**ETF / Rohstoff / Krypto:** Trend-Ampel (bzw. Marktlage-Ampel bei Aktien-ETFs) mit „Warum?“.

**Einzelaktie (US) zusätzlich:** Zeile „Aktienanzahl 12 M: −3,1 % 👍 Rückkauf“ (bzw. ⚠️/neutral),
mit Bericht und Datum („aus 10-Q vom 2026-08-01“) und Info-Text aus Abschnitt 6.

**Crash-Hinweis:** Box unter der Marktlage-Karte, nur wenn Abstand vom Hoch ≤ −20 %.

**Sparplan-Rechner (eigene Seite):** Eingaben: Betrag pro Monat (Standard 500), Jahre (5–50,
Standard 30), Fondsgebühr TER in % (Standard 0,2). Berechnung im Browser mit `sp500_real_monthly.json`:
für **jeden** Startmonat (Schritt 12 Monate) mit genug Daten:
Start `Vermögen = 0`, dann für jeden Monat mit realer Rendite `r`:
`Vermögen = (Vermögen + Betrag) × (1 + r) × (1 − TER/12)`.
Anzeige: eingezahlt, schlechtester Verlauf, 10 %, Median, 90 %, bester (in heutiger Kaufkraft),
dazu zwei Vergleichszeilen „mit 1 % höherer Gebühr: −x %“ und „10 Jahre länger: +y %“.
Prüfwert: 500/Monat, 30 Jahre, TER 0,2 % → Median ≈ 535 000, schlechtester ≈ 206 000.

**Info-Seite „Wie funktionieren die Ampeln?“** mit den Texten aus Abschnitt 6.

**Info-Seite „Was wir getestet haben“** mit der Tabelle aus Abschnitt 6.

---

## 6. Texte (wörtlich übernehmen)

**🟢 Rückenwind:** „Der Aufwärtstrend ist intakt: Über die letzten 3, 6 und 12 Monate lag
der Markt überwiegend über dem Geldmarktzins.“

**🟡 Korrektur:** „Der Markt schwächelt, aber die Wirtschaftsindikatoren zeigen keinen Stress.
Historisch war das meist eine Korrektur und kein grosser Absturz.“

**🔴 Gefahr:** „Abwärtstrend und gleichzeitig Wirtschafts-Stress. In der Vergangenheit fielen
die grossen Abstürze (2000–2002, 2008) in diese Lage. Ein vorsichtigeres Verhalten (z. B.
Positionen reduzieren) hat dort grosse Verluste vermieden.“

**Trend-Ampel 🟢/🟡/🔴:** „Rückenwind / Gemischt / Gegenwind – Anzahl der Zeiträume
(3, 6, 12 Monate), in denen die Anlage mehr brachte als der Geldmarkt.“

**Bewertung (langfristig):** „Eine hohe Bewertung deutet auf geringere Renditen in den nächsten
10 Jahren hin. Sie ist kein Verkaufssignal: Märkte bleiben oft jahrelang teuer.“

**Firmenqualität:** „Information zur Finanzkraft der Firma. Allein lagen profitable Firmen in
unseren Tests nur leicht vorne (+0,5 % pro Jahr, nicht gesichert). Zusammen mit Aktienrückkäufen
war der Vorsprung grösser. Kein Kaufsignal.“

**👍 Rückkauf:** „Die Firma hat in den letzten 12 Monaten mindestens 2 % ihrer Aktien zurückgekauft.
Solche Firmen lagen 2009–2026 im Schnitt rund 2 % pro Jahr vor vergleichbaren Firmen (#50). Das ist ein
Durchschnitt über hunderte Firmen, keine Garantie für diese Aktie – und kein Versprechen, den Index zu schlagen.“

**⚠️ Verwässerung:** „Die Firma hat mindestens 5 % neue Aktien ausgegeben. Bestehende Aktionäre besitzen
dadurch einen kleineren Anteil. Solche Firmen lagen im Schnitt rund 3 % pro Jahr zurück (#50b). Ausnahmen
gibt es (z. B. gerettete Firmen), aber das Risiko ist höher.“

**Crash-Hinweis:** „Dieser Markt liegt mehr als 20 % unter seinem Höchststand. Historisch waren die
Renditen nach solchen Einbrüchen weder deutlich besser noch schlechter als sonst (#53). Wer einen Sparplan
hat, fuhr meist am besten, ihn einfach weiterzuführen – Geld zurückzuhalten, um „unten“ zu kaufen, lohnte
sich fast nie (#54). Kein Kaufsignal.“

**Sparplan-Rechner:** „Berechnet mit der echten Entwicklung des S&P 500 seit 1871, nach Inflation. Die
Spanne zeigt, wie unterschiedlich es je nach Startjahr lief. Am meisten bewirken: früh anfangen, mehr
sparen, tiefe Gebühren (#55). Vergangene Renditen garantieren keine zukünftigen.“

**Info-Seite „Was wir getestet haben“ (Tabelle):**

| Idee | Ergebnis |
|---|---|
| Chartmuster, RSI, MACD, Fibonacci, Elliott-Wellen | Nicht besser als Zufall (#42) |
| Insider-Käufe nachmachen | Kein Vorteil (#48) |
| Berkshire / Hedgefonds nachkaufen (13F) | Schlechter als der S&P 500 (#51) |
| Nach Crashs kaufen / Geld für Crashs zurückhalten | Kein Vorteil / meist schlechter (#53, #54) |
| Faktor-ETFs (Momentum, Qualität, Value) statt MSCI World | Seit 2011 kein verlässlicher Vorsprung (#56) |
| Marktlage-Ampel (Trend + Wirtschaft) | Grosse Verluste in Rezessionen deutlich kleiner (#46, #47) |
| Aktienrückkäufe | Rund +2 % pro Jahr im Schnitt (#50) |
| Sparrate, Anlagedauer, Gebühren | Wirken stärker als jede getestete Strategie (#55) |

**Pflicht-Hinweis (auf jeder Ampel-Seite, klein):**
„Die Ampeln beruhen auf historischen Tests (S&P 500 seit 1928, 146 Einzelaktien, 35 Anlagen).
Sie haben grosse Verluste in Rezessionen deutlich verkleinert, schützen aber **nicht** bei
Einbrüchen ohne Rezession (z. B. 1987, 2022) und kosten in normalen Jahren etwas Rendite.
Rund 40 % der Trendwechsel drehen innerhalb von 3 Monaten wieder. Keine Anlageberatung.“

**Info-Seite – Belege (Auszug):**
- S&P 500 (1981–2026): mit Marktlage-Ampel grösster Verlust −24 % statt −51 % bei etwa gleicher Rendite (#46)
- 146 Einzelaktien USA/CH/DE: kleinere Verluste bei 74/92, 22/24 und 26/30 Aktien (#47)
- Finanzkrise 2008: Portfolio Schweizer Aktien −2 % statt −51 % (#47)

---

## 7. Entfernen

| Funktion | Grund |
|---|---|
| RSI, MACD, Bollinger, Fibonacci, Unterstützung/Widerstand, Ausbruch | Nicht besser als Zufall (#42) |
| Trend-/Kaufsignal der einzelnen Aktie | Eher schädlich (#45) |
| Insider-Kaufsignal | Kein Vorteil, Grosskäufe sogar negativ (#48) |
| „Überbewertet / Überhitzt = Verkaufen“ | Bewertung taugt nicht als Zeitpunkt (#34, #46) |
| Kalender-Signale | Seit Veröffentlichung verschwunden (#36) |
| Elliott-Wellen / Einstiegszonen | Chartanalyse ohne Mehrwert (#42) |
| „Smart Money“ / Guru- oder Hedgefonds-Nachkauf | Schlechter als der Index (#51) |
| „Crash = Kaufsignal“ | Kein Vorteil (#53) |
| „Diese Aktie/dieser ETF schlägt den Markt“ | Seit 2011 nicht verlässlich (#56) |

---

## 8. Akzeptanzkriterien

1. Pro Markt und Monat genau **ein** Eintrag in `market_regime`; erneutes Ausführen ändert nichts (idempotent).
2. Ampel ändert sich **nur** am Monatsende, nie untertags.
3. „Warum?“ zeigt exakt die gespeicherten Teilbedingungen (h3/h6/h12, drei Wirtschafts-Indikatoren).
4. Fällt eine Datenquelle aus, bleibt die letzte gültige Ampel sichtbar mit Vermerk
   „Aktualisierung fehlgeschlagen – Stand: …“; es wird **nichts geraten**.
5. Einzelaktien zeigen keine eigenen Kauf-/Verkaufssignale.
6. Rechenprüfung (Unit-Test der Edge Function): Kursreihe 100, 101, …, 113 (13 Monatsenden,
   steigend) mit Cash 0 % → Trend-Score 3; dieselbe Reihe fallend → Trend-Score 0;
   Zinskurve `TNX−IRX` = +1, … , −0,1 (in einem der letzten 12 Monate negativ) → Zinskurven-Stress `true`.
7. Rückkauf-Prüfung: Bericht mit Aktien 97 Mio (aktuell) und 100 Mio (Vorjahr) → −3 % → 👍 Rückkauf;
   106 / 100 → +6 % → ⚠️ Verwässerung; 101 / 100 → neutral; Bericht älter als 12 Monate → nicht angezeigt;
   Werte aus **verschiedenen** Berichten werden nie kombiniert.
8. Sparplan-Rechner: 500/Monat, 30 Jahre, TER 0,2 % → Median 530 000–540 000; TER 2 % → Median ca. −29 %.
9. Nirgends in der App erscheinen Wörter wie „Kaufsignal“, „Kursziel“, „sicher“ oder „schlägt den Markt“.
