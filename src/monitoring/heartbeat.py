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
from pathlib import Path
import requests
from loguru import logger


class Heartbeat:
    REPO = "fs1911/TradingBot"
    BRANCH = "claude/trading-bot-setup-qb6687"
    REMOTE_PATH = "status.json"
    REMOTE_HISTORY_PATH = "logs/equity_history.csv"

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

    def _put_file(self, remote_path: str, content_bytes: bytes, message: str) -> bool:
        """Create/update a file on the branch via the GitHub Contents API."""
        if not self.token:
            logger.debug("Heartbeat: no GITHUB_TOKEN — skipping")
            return False
        try:
            content = base64.b64encode(content_bytes).decode()
            url = f"https://api.github.com/repos/{self.REPO}/contents/{remote_path}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            r = requests.get(url, headers=headers, params={"ref": self.BRANCH}, timeout=10)
            sha = r.json().get("sha") if r.ok else None
            payload: dict = {"message": message, "content": content, "branch": self.BRANCH}
            if sha:
                payload["sha"] = sha
            resp = requests.put(url, json=payload, headers=headers, timeout=20)
            if resp.ok:
                return True
            logger.warning(f"Heartbeat: push {remote_path} failed {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"Heartbeat error ({remote_path}): {e}")
            return False

    def push(self, status: dict) -> bool:
        return self._put_file(
            self.REMOTE_PATH,
            json.dumps(status, indent=2).encode(),
            f"heartbeat {status['updated_utc']}",
        )

    HISTORY_HEADER = "utc,equity_usd,realized_pnl_usd,unrealized_pnl_usd,open_positions,daily_pnl_usd\n"

    def append_history(self, history_path: Path, status: dict) -> None:
        """Append one hourly equity snapshot to a local CSV and push it, so the
        equity curve is reconstructable — this is what would have let us pinpoint
        WHEN an unexplained drawdown happened."""
        try:
            history_path.parent.mkdir(exist_ok=True)
            row = (
                f"{status['updated_utc']},{status['equity_usd']},"
                f"{status['realized_pnl_usd']},{status['unrealized_pnl_usd']},"
                f"{status['open_positions']},{status['daily_pnl_usd']}\n"
            )
            new = not history_path.exists()
            with open(history_path, "a") as f:
                if new:
                    f.write(self.HISTORY_HEADER)
                f.write(row)
            self._put_file(
                self.REMOTE_HISTORY_PATH,
                history_path.read_bytes(),
                f"equity history {status['updated_utc']}",
            )
        except Exception as e:
            logger.error(f"Heartbeat history error: {e}")
