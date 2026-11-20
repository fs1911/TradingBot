# Finanzradar entrümpeln — 4 Lovable-Prompts (Stand 20.11.2026)

Grundlage: Code-Durchsicht des Projekts „Dein Finanz Radar“ und RESEARCH.md (#45–#98).
Einen Prompt pro Tag einfügen (Budget 5 Credits/Tag), in dieser Reihenfolge.
Falls Lovable mitten in einem Auftrag stoppt: am nächsten Tag „Bitte den letzten Auftrag fertigstellen“.

---

## Prompt 1 — Unnötiges ausblenden (klein)

```
Bitte nur diese Änderungen, nichts anderes umbauen, keine Dateien löschen:

1. src/routes/__root.tsx, NAV_ITEMS:
   - "Dashboard" umbenennen in "Übersicht".
   - Menüeinträge "Briefing" und "Termine" entfernen (Routen, Nacht-Job und Termine auf der Detailseite bleiben bestehen).
   - Bei allen Einträgen accent entfernen (keine gelb-orangen Hervorhebungen mehr).

2. src/routes/_authenticated/wert.$id.tsx:
   - Den Reiter "Prognose" (TabsTrigger value="prognose" und dessen TabsContent mit ForecastCard und AiBrief) entfernen. Die Komponenten-Dateien bleiben bestehen, werden nur nicht mehr angezeigt.

3. src/routes/_authenticated/index.tsx, Watchlist-Karten:
   - Die Zeile mit der 24h-Veränderung und die Kennzahl "7T" entfernen. "30T" und "z. 52W"/"z. ATH" bleiben.
   - Die Zeile "Drawdown-Signal" nur noch anzeigen, wenn ddMap[it.id].eligible true ist (breite Index-ETFs, BTC, ETH). Bei Einzelaktien die Zeile ganz weglassen (auch "Drawdown: —").

4. src/components/DrawdownBadge.tsx: Beschriftung "Kaufzone" ändern in "Stark unter Hoch" (Emoji 🔵 statt 🟢). Die interne Zone "kaufzone" bleibt gleich.
   In src/lib/drawdown-conflict.ts im Text "Kaufzone" ebenfalls durch "stark unter dem Hoch" ersetzen.

Danach Tests und Build prüfen.
```

---

## Prompt 2 — Marktlage kompakt (klein)

```
Bitte nur diese Änderung:

Auf der Startseite (src/routes/_authenticated/index.tsx) wird <RegimeSection /> mit rund 12 grossen Karten VOR der Watchlist angezeigt. Ersetze das auf der Startseite durch eine kompakte Zeile:
- Titel "Marktlage" mit InfoTip k="marktlage".
- Pro Markt (MARKETS aus src/lib/regime.ts) ein kleiner Chip: Name + Emoji (🟢/🟡/🔴) aus getRegimeOverview, z. B. "USA 🟡". Bei Tooltip/Klick: MARKET_LABEL und standText(month).
- Ist mindestens ein Markt 🔴: unter den Chips einmal den Text MARKET_TEXT.rot anzeigen.
- Ein Link "Alle Details" auf /ampeln.
- Die Anlageklassen-Karten (Trend) NICHT mehr auf der Startseite zeigen.

Auf der Seite /ampeln (src/routes/_authenticated/ampeln.tsx) die vollständige <RegimeSection /> oben einfügen, falls sie dort noch nicht ist (mit allen Karten, "Warum?" und Verlauf).

Reihenfolge Startseite danach: RegimeChangeBanner, kompakte Marktlage-Zeile, Watchlist-Kopf, Watchlist, Disclaimer. Danach Build prüfen.
```

---

## Prompt 3 — „Mein Depot“ zusammenlegen + Klumpen-Warnung (mittel)

```
Bitte nur diese Änderungen:

1. src/routes/_authenticated/portfolio.tsx in "Mein Depot" umbenennen (Seitentitel und Menü in src/routes/__root.tsx). Auf der Seite drei Reiter (Tabs aus src/components/ui/tabs):
   - "Bestand": der bisherige Inhalt der Portfolio-Seite.
   - "Risiko": der Inhalt von src/routes/_authenticated/risiko.tsx (Klumpen & Exposure, Währungen) – als Komponente wiederverwenden, nicht kopieren.
   - "Verteilung": der Inhalt von src/routes/_authenticated/empfehlung.tsx – als Komponente wiederverwenden.
   Die Routen /risiko und /empfehlung leiten auf /portfolio weiter. Menüeinträge "Empfehlung" und "Risiko" in NAV_ITEMS entfernen.

2. Startseite (src/routes/_authenticated/index.tsx): wenn getPortfolio() Warnungen liefert (warnings nicht leer), oberhalb der Watchlist eine schmale gelbe Box "⚠ Klumpenrisiko: …" mit den Warnungen und Link "Mein Depot" anzeigen. Keine Box, wenn es keine Warnungen gibt.

Menü danach: Übersicht, Markt-Radar, Mein Depot, Ampeln (Label "Info"), Profil. Danach Tests und Build prüfen.
```

---

## Prompt 4 — Warn-Plaketten für Einzelaktien (grösser, evtl. 2 Tage)

```
Ziel: auf Watchlist-Karten (src/routes/_authenticated/index.tsx) und im Kopf der Detailseite (src/routes/_authenticated/wert.$id.tsx) bei AKTIEN (isStock) bis zu drei kleine Plaketten. Werte beim Aktualisieren eines Watchlist-Werts berechnen und im Snapshot speichern (nicht bei jedem Seitenaufruf neu laden). Keine Kauf- oder Verkaufsempfehlung, keine grüne Farbe.

1. Trend (200 Tage): letzter Tagesschlusskurs < Durchschnitt der letzten 200 Tagesschlusskurse → Trend gebrochen. Tageskurse aus der bestehenden Historie (src/lib/long-history.server.ts bzw. getAssetHistory). Mindestens 220 Tageskurse nötig, sonst "keine Daten".

2. Aktienanzahl 12 Monate (nur US-Aktien, SEC): Falls src/lib/sec.ts / CompanyQuality schon eine Veränderung der Aktienanzahl berechnet, diese verwenden. Sonst: aus https://data.sec.gov/api/xbrl/companyconcept/CIK{10-stellig}/us-gaap/WeightedAverageNumberOfDilutedSharesOutstanding.json (Ersatz: WeightedAverageNumberOfSharesOutstandingBasic) den neuesten 10-K/10-Q nehmen, aktuelle Periode und gleich lange Vorjahresperiode aus DEMSELBEN Bericht (accn), Veränderung = aktuell/vorjahr − 1, nur gültig wenn |Veränderung| < 80 % und Bericht ≤ 12 Monate alt. Bestehenden SEC-User-Agent aus src/lib/sec.server.ts verwenden.
   ≥ +5 % → "⚠️ Verwässerung +x %"; ≤ −2 % → "👍 Rückkauf −x %"; dazwischen nichts anzeigen.

3. Börsengang: erster verfügbarer Tageskurs weniger als 3 Jahre alt → "⚠️ Börsengang < 3 J."

Plaketten-Logik:
- "🔴 Warnsignal" wenn Trend gebrochen ODER Verwässerung ≥ +5 %. InfoTip/Text: "Aktien mit diesem Signal sind historisch etwa doppelt so oft stark abgestürzt (Backtest US-Aktien 2010–2026). Kein Verkaufsbefehl, aber kein guter Moment für Zukäufe."
- Sonst "kein Warnsignal" in grauer, unauffälliger Schrift (bewusst NICHT grün: ohne Warnsignal heisst nicht "kaufen").
- Zusätzlich je nach Daten: "👍 Rückkauf", "⚠️ Verwässerung", "⚠️ Börsengang < 3 J."
- Neuen InfoTip-Eintrag in src/lib/glossary.ts: "warnsignal" mit obigem Text; "rueckkauf": "Firmen, die eigene Aktien zurückkaufen, liefen historisch etwas besser als der Durchschnitt (+2–3 %/Jahr, US-Daten 2010–2026). Information, keine Garantie."; "ipo": "Börsengänge lagen nach 3 Jahren im Mittel deutlich hinter dem Markt (73 % im Minus)."

Bei Krypto und ETFs keine dieser Plaketten. Bei fehlenden Daten die jeweilige Plakette weglassen. Tests für die drei Rechnungen ergänzen, danach Build prüfen.
```
