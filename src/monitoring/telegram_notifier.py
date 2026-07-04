"""
Telegram notification service — sends trade alerts and daily reports.
Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment.
"""
from __future__ import annotations
import os
import requests
from loguru import logger


class TelegramNotifier:

    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)
        if not self.enabled:
            logger.debug("Telegram not configured — notifications disabled")

    def send(self, text: str) -> bool:
        if not self.enabled:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
            }, timeout=10)
            return resp.ok
        except Exception as e:
            logger.warning(f"Telegram send failed: {e}")
            return False

    def trade_entered(self, *args, **kwargs) -> None:
        pass  # Stumm — nur Tagesbericht aktiv

    def trade_exited(self, *args, **kwargs) -> None:
        pass  # Stumm — nur Tagesbericht aktiv

    def daily_report(self, report: dict) -> None:
        if report.get("message"):
            self.send(f"📊 <b>Tagesbericht</b>\n{report['message']}")
            return

        pnl = report.get("total_pnl_usd", 0)
        total = report.get("total_trades", 0)
        wins = round(total * report.get("win_rate_%", 0) / 100)
        losses = total - wins
        emoji = "📈" if pnl >= 0 else "📉"

        self.send(
            f"{emoji} <b>Tagesbericht — {report.get('label', '')}</b>\n\n"
            f"Ergebnis: <b>{pnl:+.2f}$</b>\n"
            f"Trades: {total}  ✅ {wins} gewonnen  ❌ {losses} verloren"
        )

    def error_alert(self, message: str) -> None:
        pass  # Stumm — nur Tagesbericht aktiv

    def startup(self, symbols: list[str], timeframe: str) -> None:
        pass  # Stumm — nur Tagesbericht aktiv
