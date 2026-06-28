# TradingBot-CH — Systematischer Algorithmus-Trading Bot

Ein vollautomatisierter, professioneller Trading-Bot für Schweizer Privatanleger.
Unterstützt US-Aktien (Alpaca), Crypto (Binance/Kraken via CCXT) und ist für
Paper-Trading sowie Live-Trading ausgelegt.

---

## Plattform- & Broker-Empfehlung (Schweiz)

### Vergleich: Automatisierungs-Plattformen

| Plattform/Setup | Märkte | API/Bot-Support | CH-Zugang | Gebühren |
|---|---|---|---|---|
| **Alpaca Markets + Python** | US-Aktien/ETFs | REST + WebSocket API, Python SDK | Ja (Konto in USD) | 0 Kommission (Stocks), niedrig |
| **Binance / Kraken + CCXT** | Crypto 24/7 | Vollständige REST + WS API | Ja (Kraken CH-freundlich) | 0.04–0.20% |
| **Interactive Brokers + TWS API** | Aktien, Optionen, Forex, Futures | TWS API, Python ib_insync | Ja (IBKR CH) | Niedrig bis mittel |
| **MetaTrader 5 + Python** | Forex, CFDs, Indizes | MQL5 + Python MT5-Lib | Ja (diverse Broker) | Spread-basiert |

**Hauptempfehlung: Alpaca Markets (US-Stocks/ETFs)**
- Keine Handelskommissionen, professionelle REST-API
- Paper-Trading-Konto für risikofreie Tests
- Ideal für systematisches Aktien-/ETF-Trading aus der Schweiz

**Zweitempfehlung: Kraken (Crypto)**
- Schweizer FINMA-Registrierung, CHF Ein-/Auszahlungen
- Stabile API, gute Liquidität, niedrige Gebühren
- 24/7 Crypto-Märkte

### Broker-Vergleich (Schweiz)

| Broker | Sitz/Regulierung | Produkte | Gebühren | Automatisierung |
|---|---|---|---|---|
| **Alpaca Markets** | USA, SEC/FINRA | US-Aktien, ETFs | 0 Kommission | REST API, Python SDK |
| **Kraken** | USA, FINMA-reg. | Crypto (BTC, ETH, …) | 0.16–0.26% | REST + WebSocket API |
| **IBKR (Schweiz)** | CH, FINMA | Aktien, ETF, Optionen, Forex | Ab CHF 1/Trade | TWS API, Python |

---

## Projekt-Struktur

```
TradingBot/
├── config/
│   ├── bot_config.yaml        # Broker, Symbole, Zeitrahmen
│   ├── strategy_config.yaml   # Indikator-Parameter je Strategie
│   └── risk_config.yaml       # Drawdown-Limits, Positionsgrössen
├── src/
│   ├── bot.py                 # Haupt-Orchestrator
│   ├── brokers/               # Alpaca, CCXT (Binance/Kraken)
│   ├── strategies/            # EMA-Crossover, RSI, MACD, Congress
│   ├── indicators/            # Technische Indikatoren
│   ├── risk/                  # Risk Manager (Drawdown, Positionsgrösse)
│   ├── data/                  # News-Sentiment
│   ├── backtest/              # Backtesting-Engine
│   └── monitoring/            # Reporting & Trading-Journal
├── scripts/
│   ├── run_bot.py             # Bot starten
│   ├── run_backtest.py        # Backtest ausführen
│   └── generate_report.py     # Performance-Report
└── tests/                     # Unit-Tests (pytest)
```

---

## Schnellstart

### 1. Installation

```bash
git clone <repo-url> && cd TradingBot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Konfiguration

```bash
cp .env.example .env
# .env editieren: API-Keys eintragen
```

### 3. Paper-Trading testen

```bash
python scripts/run_bot.py          # Dauerhafter Loop
python scripts/run_bot.py --once   # Einzelner Tick
```

### 4. Backtest ausführen

```bash
python scripts/run_backtest.py --symbols SPY QQQ AAPL --period 2y --timeframe 1h
```

### 5. Tests

```bash
pytest tests/ -v
```

---

## Strategie-Übersicht

### 1. EMA-Crossover

| Parameter | Default | Beschreibung |
|---|---|---|
| `fast_ema` | 9 | Schneller EMA |
| `slow_ema` | 21 | Langsamer EMA |
| `sl_atr_multiplier` | 1.5 | Stop-Loss = Entry ± ATR × 1.5 |
| `tp_atr_multiplier` | 2.5 | Take-Profit = Entry ± ATR × 2.5 |
| `volume_filter` | true | Volumen > 1.2× 20-Bar-Durchschnitt |

**Einstieg:** EMA(9) kreuzt EMA(21), mit Volumenbestätigung.
**Ausstieg:** ATR-basierter SL/TP, optional Trailing-Stop.

### 2. RSI Mean Reversion

| Parameter | Default | Beschreibung |
|---|---|---|
| `rsi_period` | 14 | RSI-Periode |
| `oversold_threshold` | 30 | Long-Signal wenn RSI < 30 |
| `overbought_threshold` | 70 | Short-Signal wenn RSI > 70 |
| `ema_trend_filter` | 50 | Nur Long wenn Preis > EMA50 |

**Einstieg:** RSI kehrt von extremem Niveau zurück, Trendfilter aktiv.

### 3. MACD Momentum

| Parameter | Default | Beschreibung |
|---|---|---|
| `fast_period` | 12 | MACD Fast EMA |
| `slow_period` | 26 | MACD Slow EMA |
| `signal_period` | 9 | Signal-Linie |
| `ema_trend_filter` | 200 | Nur Long wenn Preis > EMA200 |

**Einstieg:** MACD-Histogramm wechselt Vorzeichen + Makro-Trend-Bestätigung.

### 4. Congress Trades Mirror (optional)

Nutzt öffentlich gemeldete Käufe von US-Abgeordneten (STOCK Act, via QuiverQuant API)
als ergänzende Long-Signale — immer mit technischem Trendfilter und normalem
Risk-Management kombiniert.

**Logik:**
1. Kauf gemeldet (> $15'000) innerhalb von 72 Stunden
2. Preis über EMA(20) → Aufwärtstrend bestätigt
3. Position mit Standard-ATR-SL/TP eröffnen

---

## Risk-Management

### Positionsgrösse (Fixed Fractional)

```
Risikobetrag    = Eigenkapital × risk_per_trade_pct (Standard: 1%)
SL-Distanz      = |Entry - Stop-Loss|
Positionsgrösse = Risikobetrag / SL-Distanz
```

### Drawdown-Limits

| Limit | Default | Aktion |
|---|---|---|
| Täglicher Drawdown | 3% | Pause bis nächsten Tag |
| Wöchentlicher DD | 6% | Strategie-Review |
| Monatlicher DD | 10% | Notfall-Stop + manuelle Prüfung |
| Gesamter DD | 15% | Hard Stop — manueller Neustart |

### Verlustserien-Schutz

Nach 4 aufeinanderfolgenden Verlust-Trades → 4-Stunden-Pause.

### Safe Mode

Aktiviert bei VIX > 30 oder wenn Tages-Drawdown-Schwelle fast erreicht:
- Positionsgrösse wird halbiert
- Keine neuen Entries (optional konfigurierbar)

---

## Backtesting & Selbst-Optimierung

### Benchmark-Kriterien (Strategie gilt als „akzeptabel")

| Metrik | Minimum |
|---|---|
| Sharpe Ratio | ≥ 0.8 |
| Profit Factor | ≥ 1.3 |
| Max Drawdown | ≤ 15% |
| Win-Rate | ≥ 40% |
| Anzahl Trades | ≥ 30 |

### Wöchentlicher Review-Prozess

1. `python scripts/generate_report.py --period weekly --hints`
2. Optimierungshinweise prüfen (auto-generiert aus Trade-History)
3. Parameter in `config/strategy_config.yaml` anpassen
4. Backtest auf letzten 6 Monaten wiederholen
5. Nur nach Benchmark-Bestätigung auf Live übertragen

### Automatische Optimierungshinweise

Das System analysiert die Trade-History und gibt Empfehlungen zu:
- Win-Rate pro Strategie
- R/R-Verhältnis (Ø-Gewinn vs. Ø-Verlust)
- Häufigste Exit-Gründe (zu viele SL → SL zu eng?)

---

## To-Do-Liste: Inbetriebnahme

### Phase 1 — Setup (Woche 1)
- [ ] `.env` mit API-Keys füllen (Alpaca Paper-Account erstellen)
- [ ] `pip install -r requirements.txt`
- [ ] `pytest tests/ -v` — alle Tests grün?
- [ ] `python scripts/run_bot.py --once` im Paper-Modus testen

### Phase 2 — Backtest (Woche 1–2)
- [ ] Backtest auf 2 Jahre Daten: SPY, QQQ, AAPL
- [ ] Alle Benchmark-Kriterien erfüllt?
- [ ] Parameter in `strategy_config.yaml` ggf. anpassen
- [ ] Backtest wiederholen bis Benchmarks erreicht

### Phase 3 — Paper-Trading (Woche 2–6)
- [ ] Bot 4 Wochen im Paper-Modus laufen lassen (auf VPS/Server)
- [ ] Täglich: `python scripts/generate_report.py --period daily`
- [ ] Wöchentlich: `python scripts/generate_report.py --period weekly --hints`
- [ ] Alle Drawdown-Limits beobachten — greift der Schutz korrekt an?

### Phase 4 — Live (nach Woche 6)
- [ ] `TRADING_ENV=live` in `.env` setzen
- [ ] `ALPACA_BASE_URL=https://api.alpaca.markets` (Live-URL)
- [ ] Startkapital: klein beginnen (z.B. $1'000–$5'000)
- [ ] Monitoring: täglich 5 Minuten Logs prüfen
- [ ] Notfall-Plan: Wie deaktiviere ich den Bot sofort?

---

## Trading-Journal Template

Das Journal wird automatisch in `logs/trading_journal.csv` geführt.

| Spalte | Beschreibung |
|---|---|
| date | Datum (YYYY-MM-DD) |
| symbol | Handelsinstrument |
| strategy | Welche Strategie hat das Signal generiert |
| direction | long / short |
| entry_price / exit_price | Kauf-/Verkaufskurs |
| pnl_usd / pnl_pct | Absoluter und relativer Gewinn/Verlust |
| exit_reason | sl / tp / signal / end_of_data |
| notes | Manuelle Anmerkungen |

---

## Compliance & Rechtliche Hinweise

> **Wichtiger Haftungsausschluss**
>
> Diese Software stellt **keine persönliche Anlageberatung** dar.
> Algorithmisches Trading — insbesondere mit Hebel — birgt erhebliche Risiken
> bis hin zum Totalverlust des eingesetzten Kapitals.
>
> Als Privatanleger in der Schweiz gelten folgende Punkte:
>
> - **Steuer:** Gewinne aus privatem Handel sind in der Schweiz i.d.R. steuerfrei,
>   sofern kein gewerbsmässiger Wertschriftenhandel vorliegt. Bei systematischem,
>   hochfrequentem Handel kann die ESTV Gewerbsmässigkeit prüfen. Bitte
>   konsultieren Sie einen Schweizer Steuerberater.
> - **Regulierung:** Privates algorithmisches Trading ist in der CH erlaubt.
>   Keine FINMA-Lizenz nötig für Eigenhandel. Bei Handel mit Hebelzertifikaten
>   (CFDs) gelten ggf. Anforderungen des zugelassenen Brokers.
> - **Risikohinweise:** Vergangene Performance (Backtest) ist kein Garant für
>   zukünftige Ergebnisse. Flash Crashes, API-Ausfälle und Slippage können zu
>   grösseren Verlusten führen als im Backtest sichtbar.

### Pre-Live-Checklist

- [ ] Broker reguliert (SEC/FINRA, FCA, FINMA)?
- [ ] Paper-Trading ≥ 4 Wochen mit positivem Ergebnis?
- [ ] Notfall-Prozedur: Bot manuell deaktivieren innerhalb < 60 Sekunden?
- [ ] Server/VPS stabil, Auto-Restart konfiguriert?
- [ ] Worst-Case: Was passiert bei 50%-Markt-Crash? (Backtesting auf 2020/2022)
- [ ] Maximales Kapital definiert, das Sie bereit sind zu riskieren?
