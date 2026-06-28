# TradingBot — Deployment Guide & Referenz

Erstellt: 28. Juni 2026  
Setup durch: Filip Subara (iPad-only, Oracle Cloud Free Tier)

---

## Wichtige Links

### Accounts & Plattformen
| Dienst | Link | Zweck |
|---|---|---|
| **Alpaca Paper Trading** | https://app.alpaca.markets | Bot-Resultate, Orders, Portfolio |
| **Alpaca API Keys** | https://app.alpaca.markets/paper/dashboard/overview | API Keys verwalten |
| **Oracle Cloud Console** | https://cloud.oracle.com | Server verwalten |
| **GitHub Repository** | https://github.com/fs1911/TradingBot | Bot-Code |
| **Termius (iPad App)** | https://apps.apple.com/app/termius-ssh-client/id549039908 | SSH-Client für iPad |

### Für die Zukunft (noch nicht genutzt)
| Dienst | Link | Zweck |
|---|---|---|
| **Kraken** | https://www.kraken.com | Crypto Exchange (kein Paper Trading für Spot) |
| **Kraken Futures Demo** | https://demo-futures.kraken.com | Kraken Paper Trading (nur Futures) |
| **Binance Testnet** | https://testnet.binance.vision | Binance Paper Trading |
| **Telegram BotFather** | https://t.me/BotFather | Bot-Benachrichtigungen einrichten |
| **QuiverQuant** | https://www.quiverquant.com | Congress-Trades Strategie (API-Key benötigt) |
| **Alpaca Docs** | https://docs.alpaca.markets | Alpaca API Dokumentation |

---

## Server-Informationen

| Feld | Wert |
|---|---|
| **Anbieter** | Oracle Cloud Free Tier |
| **Region** | Zürich (eu-zurich-1) |
| **Instanz-Typ** | VM.Standard.E2.1.Micro |
| **OS** | Ubuntu 22.04 |
| **SSH-Benutzer** | ubuntu |
| **SSH-Key** | `ssh-key-2026-06-28.key` (auf iPad gespeichert) |
| **Bot-Verzeichnis** | `/home/ubuntu/TradingBot` |
| **Bot-Service** | `tradingbot` (systemd) |
| **Log** | `sudo journalctl -u tradingbot -f` |

---

## Bot-Konfiguration (Stand: 28.06.2026)

| Parameter | Wert |
|---|---|
| **Broker** | Alpaca Paper Trading |
| **Timeframe** | 15 Minuten |
| **Symbole (Aktien)** | SPY, QQQ, AAPL, MSFT, NVDA, AMZN |
| **Symbole (Crypto)** | BTC/USD, ETH/USD |
| **Strategien** | EMA Crossover, RSI Mean Reversion, MACD Momentum |
| **Trading-Modus** | Paper (kein echtes Geld) |
| **Crypto 24/7** | Ja (BTC/USD, ETH/USD handeln auch Sa/So) |
| **Aktien-Zeiten** | Mo–Fr 15:30–22:00 Uhr Schweizer Zeit |

---

## Wichtigste Befehle (SSH / Termius)

### Bot-Management
```bash
# Status prüfen
sudo systemctl status tradingbot

# Bot starten
sudo systemctl start tradingbot

# Bot stoppen
sudo systemctl stop tradingbot

# Bot neu starten
sudo systemctl restart tradingbot

# Live-Log anschauen (Ctrl+C zum Beenden)
sudo journalctl -u tradingbot -f

# Letzte 100 Zeilen Log
sudo journalctl -u tradingbot -n 100
```

### Bot aktualisieren (nach Code-Änderungen)
```bash
cd TradingBot
git pull origin claude/trading-bot-setup-qb6687
sudo systemctl restart tradingbot
sudo systemctl status tradingbot
```

### Bot einmalig testen
```bash
cd TradingBot
source .venv/bin/activate
python scripts/run_bot.py --once
```

---

## Konfiguration anpassen

### API Keys ändern (`.env` Datei)
```bash
# Aktuellen Key anzeigen
grep ALPACA_API_KEY /home/ubuntu/TradingBot/.env

# Key ändern (Beispiel)
sed -i 's/ALPACA_API_KEY=.*/ALPACA_API_KEY=PK_NEUER_KEY/' /home/ubuntu/TradingBot/.env
```

### Auf Live Trading umstellen (ACHTUNG: echtes Geld!)
```bash
# 1. Echte Alpaca API-Keys eintragen (Live, nicht Paper)
sed -i 's/ALPACA_API_KEY=.*/ALPACA_API_KEY=DEIN_LIVE_KEY/' /home/ubuntu/TradingBot/.env
sed -i 's/ALPACA_SECRET_KEY=.*/ALPACA_SECRET_KEY=DEIN_LIVE_SECRET/' /home/ubuntu/TradingBot/.env
sed -i 's|ALPACA_BASE_URL=.*|ALPACA_BASE_URL=https://api.alpaca.markets|' /home/ubuntu/TradingBot/.env
sed -i 's/TRADING_ENV=.*/TRADING_ENV=live/' /home/ubuntu/TradingBot/.env

# 2. Bot neu starten
sudo systemctl restart tradingbot
```

---

## Symbole / Timeframe ändern

Datei: `/home/ubuntu/TradingBot/config/bot_config.yaml`

```bash
# Timeframe auf 1 Stunde zurückstellen
sed -i 's/timeframe: "15Min"/timeframe: "1Hour"/' /home/ubuntu/TradingBot/config/bot_config.yaml

# Nach Änderungen immer neu starten
sudo systemctl restart tradingbot
```

Mögliche Timeframes: `1Min`, `5Min`, `15Min`, `1Hour`, `4Hour`, `1Day`

---

## Telegram-Benachrichtigungen einrichten (optional)

1. Telegram öffnen → `@BotFather` suchen → `/newbot` → Token kopieren
2. Eigene Chat-ID holen: `@userinfobot` in Telegram schreiben
3. In `.env` eintragen:

```bash
sed -i 's/TELEGRAM_TOKEN=.*/TELEGRAM_TOKEN=DEIN_TOKEN/' /home/ubuntu/TradingBot/.env
sed -i 's/TELEGRAM_CHAT_ID=.*/TELEGRAM_CHAT_ID=DEINE_CHAT_ID/' /home/ubuntu/TradingBot/.env
sudo systemctl restart tradingbot
```

Dann erhalten Sie täglich einen Report über Telegram.

---

## Mögliche Erweiterungen (Zukunft)

### Day Trading Modus
- Timeframe auf `5Min` oder `1Min` stellen
- Logik für automatisches Schliessen aller Positionen um 21:50 Uhr (vor US-Börsenschluss)
- Achtung: PDT-Regel bei echtem Geld unter $25'000 (max. 3 Day Trades / 5 Tage)

### Weitere Strategien aktivieren
In `config/bot_config.yaml`:
```yaml
active_strategies:
  - "ema_crossover"
  - "rsi_mean_reversion"
  - "macd_momentum"
  - "congress_mirror"   # Aktivieren wenn QuiverQuant API-Key vorhanden
```

### Anderen Broker verwenden
In `config/bot_config.yaml`:
```yaml
broker: "binance"   # oder "kraken"
```
Dazu entsprechende API-Keys in `.env` eintragen.

### Mehr Crypto-Symbole
In `config/bot_config.yaml` unter `markets.alpaca.symbols`:
```yaml
symbols: ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD"]
```

---

## Resultate prüfen

**Auf Alpaca:**
1. `app.alpaca.markets` öffnen
2. Oben rechts: "Paper" Account auswählen
3. "Activity" → alle Trades anschauen
4. "Portfolio" → Gesamtperformance

**Auf dem Server:**
```bash
# Alle Trades im Log suchen
sudo journalctl -u tradingbot | grep "ENTERED"

# Fehler suchen
sudo journalctl -u tradingbot | grep "ERROR"
```

---

## Notfall: Bot hängt oder Server nicht erreichbar

```bash
# Server neu starten (Oracle Cloud Console)
# cloud.oracle.com → Compute → Instances → Reboot

# Danach: Bot startet automatisch (systemd enable)
# Prüfen ob Bot wieder läuft:
sudo systemctl status tradingbot
```

---

## Git Branch

Alle Bot-Updates werden auf diesem Branch entwickelt:
```
claude/trading-bot-setup-qb6687
```

Update-Befehl auf dem Server:
```bash
cd TradingBot && git pull origin claude/trading-bot-setup-qb6687 && sudo systemctl restart tradingbot
```
