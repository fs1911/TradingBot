"""
Heartbeat — pushes a small status.json to GitHub so the bot's liveness is
observable at any time without SSH access.

Answers "is the bot actually running and trading?" — the question we kept
being blind about. Updated hourly via the GitHub REST API (same mechanism
as JournalSync). Silently skips when no GITHUB_TOKEN is configured.
"""
from __future__ import annotations
import os
import json
import base64
from datetime import datetime, timezone
import requests
from loguru import logger


class Heartbeat:
    REPO = "fs1911/TradingBot"
    BRANCH = "claude/trading-bot-setup-qb6687"
    REMOTE_PATH = "status.json"

    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.started_at = datetime.now(timezone.utc)

    def build_status(self, *, state: str, open_positions: int, trades_today: int,
                     equity: float, market_trend: str, daily_pnl: float,
                     realized_pnl: float = 0.0, unrealized_pnl: float = 0.0,
                     positions: list | None = None) -> dict:
        now = datetime.now(timezone.utc)
        uptime_h = round((now - self.started_at).total_seconds() / 3600, 1)
        return {
            "updated_utc": now.strftime("%Y-%m-%d %H:%M:%S"),
            "alive": True,
            "state": state,
            "uptime_hours": uptime_h,
            "open_positions": open_positions,
            "trades_today": trades_today,
            "daily_pnl_usd": round(daily_pnl, 2),
            # Diagnostics: separates booked losses from open-position mark-to-market,
            # so an equity drop the trade journal can't explain becomes visible.
            "realized_pnl_usd": round(realized_pnl, 2),
            "unrealized_pnl_usd": round(unrealized_pnl, 2),
            "equity_usd": round(equity, 2),
            "market_trend": market_trend,
            "positions": positions or [],
        }

    def push(self, status: dict) -> bool:
        if not self.token:
            logger.debug("Heartbeat: no GITHUB_TOKEN — skipping")
            return False
        try:
            content = base64.b64encode(
                json.dumps(status, indent=2).encode()
            ).decode()
            url = f"https://api.github.com/repos/{self.REPO}/contents/{self.REMOTE_PATH}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            r = requests.get(url, headers=headers, params={"ref": self.BRANCH}, timeout=10)
            sha = r.json().get("sha") if r.ok else None
            payload: dict = {
                "message": f"heartbeat {status['updated_utc']}",
                "content": content,
                "branch": self.BRANCH,
            }
            if sha:
                payload["sha"] = sha
            resp = requests.put(url, json=payload, headers=headers, timeout=15)
            if resp.ok:
                logger.debug("Heartbeat: status pushed")
                return True
            logger.warning(f"Heartbeat: push failed {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False
