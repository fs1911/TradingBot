# Finanzradar – Spezifikation „Marktlage- & Trend-Ampel“

> Zum Einfügen in Lovable. Grundlage: 49 Experimente im Projekt TradingBot (RESEARCH.md).
> Jede Regel hier wurde getestet; die Nummern (#45, #46 …) verweisen auf das Experiment.

---

## 0. Grundsätze (bitte strikt einhalten)

1. Die App gibt **keine Kauf-/Verkaufsbefehle für einzelne Aktien**. Sie zeigt **Ampeln**
   (Marktlage, Trend) und **Informationen** (Firmenqualität, Bewertung).
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
`company_quality` einmal pro Woche aktualisieren.

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

**Info-Seite „Wie funktionieren die Ampeln?“** mit den Texten aus Abschnitt 6.

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

**Firmenqualität:** „Information zur Finanzkraft der Firma. In unseren Tests lagen profitable
Firmen leicht vorne, der Vorsprung war aber statistisch nicht gesichert. Kein Kaufsignal.“

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
