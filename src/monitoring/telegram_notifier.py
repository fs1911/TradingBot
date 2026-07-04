"""
Telegram notification service — sends trade alerts and daily reports.
Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment.
"""
from __future__ import annotations
import os
import requests
from datetime import datetime, timezone
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

    def trade_entered(self, symbol: str, side: str, qty: float, price: float, strategy: str,
                      sl: float | None, tp: float | None) -> None:
        sl_str = f"{sl:.4f}" if sl else "—"
        tp_str = f"{tp:.4f}" if tp else "—"
        emoji = "🟢" if side.lower() == "buy" else "🔴"
        self.send(
            f"{emoji} <b>ENTERED {side.upper()}</b>\n"
            f"Symbol: <b>{symbol}</b>\n"
            f"Qty: {qty:.4f} @ ${price:.4f}\n"
            f"Strategy: {strategy}\n"
            f"SL: {sl_str} | TP: {tp_str}"
        )

    def trade_exited(self, symbol: str, side: str, qty: float, entry: float,
                     exit_price: float, pnl: float, reason: str) -> None:
        emoji = "✅" if pnl > 0 else "❌"
        self.send(
            f"{emoji} <b>CLOSED {side.upper()}</b>\n"
            f"Symbol: <b>{symbol}</b>\n"
            f"Entry: ${entry:.4f} → Exit: ${exit_price:.4f}\n"
            f"PnL: <b>${pnl:+.2f}</b>  ({reason.upper()})"
        )

    def daily_report(self, report: dict) -> None:
        if report.get("message"):
            self.send(f"📊 <b>Tagesbericht</b>\n{report['message']}")
            return

        pnl = report.get("total_pnl_usd", 0)
        equity = report.get("account_equity", 0)
        pnl_pct_total = (pnl / equity * 100) if equity > 0 else 0
        emoji = "📈" if pnl >= 0 else "📉"

        trade_lines = []
        for t in report.get("trades", []):
            t_emoji = "🟢" if t["pnl_usd"] > 0 else "🔴"
            direction = "L" if t["direction"] == "long" else "S"
            reason = (t.get("exit_reason", "") or "??")[:2].upper()
            trade_lines.append(
                f"{t_emoji} {t['symbol']:<10} {direction}  "
                f"{t['pnl_usd']:>+7.2f}$  ({t['pnl_pct']:>+5.2f}%)  [{reason}]"
            )
        trades_block = "\n".join(trade_lines) if trade_lines else "— keine Trades —"

        strat_lines = "\n".join(
            f"  {k}: ${v:+.2f}"
            for k, v in report.get("strategy_breakdown", {}).items()
        )

        summary = (
            f"<b>Gesamt:  {pnl:+.2f}$  ({pnl_pct_total:+.2f}%)</b>\n"
            f"Trades: {report.get('total_trades', 0)} | "
            f"Win Rate: {report.get('win_rate_%', 0):.1f}%\n"
            f"Profit Factor: {report.get('profit_factor', 0):.2f}\n"
            f"Best: ${report.get('best_trade', 0):+.2f} | "
            f"Worst: ${report.get('worst_trade', 0):+.2f}\n\n"
            f"<b>Pro Strategie:</b>\n{strat_lines}"
        )

        full_msg = (
            f"{emoji} <b>Tagesbericht — {report.get('label', '')}</b>\n\n"
            f"<b>Einzelne Trades:</b>\n"
            f"<code>{trades_block}</code>\n\n"
            f"{'─' * 32}\n"
            f"{summary}"
        )

        if len(full_msg) <= 4096:
            self.send(full_msg)
        else:
            self.send(
                f"{emoji} <b>Tagesbericht — {report.get('label', '')} (Trades)</b>\n\n"
                f"<code>{trades_block}</code>"
            )
            self.send(f"{summary}")

    def error_alert(self, message: str) -> None:
        self.send(f"⚠️ <b>BOT ALERT</b>\n{message}")

    def startup(self, symbols: list[str], timeframe: str) -> None:
        self.send(
            f"🚀 <b>TradingBot gestartet</b>\n"
            f"Symbole: {len(symbols)}\n"
            f"Timeframe: {timeframe}\n"
            f"Zeit: {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
        )
