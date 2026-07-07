"""
JournalSync — pushes trading_journal.csv to GitHub nightly via the REST API.

Requires GITHUB_TOKEN env var (Personal Access Token with repo write scope).
If the token is absent the sync is silently skipped.
"""
from __future__ import annotations
import os
import base64
from datetime import date
from pathlib import Path
import requests
from loguru import logger


class JournalSyncer:
    REPO = "fs1911/TradingBot"
    BRANCH = "claude/trading-bot-setup-qb6687"
    REMOTE_PATH = "logs/trading_journal.csv"

    def __init__(self, journal_path: Path):
        self.journal_path = journal_path
        self.token = os.environ.get("GITHUB_TOKEN", "")

    def push(self) -> bool:
        if not self.token:
            logger.debug("JournalSync: GITHUB_TOKEN not configured — skipping")
            return False
        if not self.journal_path.exists():
            logger.debug("JournalSync: no journal to sync yet")
            return False

        try:
            content = base64.b64encode(self.journal_path.read_bytes()).decode()
            url = f"https://api.github.com/repos/{self.REPO}/contents/{self.REMOTE_PATH}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }

            # Fetch existing file SHA (required to update, absent for first upload)
            r = requests.get(url, headers=headers, params={"ref": self.BRANCH}, timeout=10)
            sha = r.json().get("sha") if r.ok else None

            payload: dict = {
                "message": f"Auto-sync trading journal {date.today()}",
                "content": content,
                "branch": self.BRANCH,
            }
            if sha:
                payload["sha"] = sha

            resp = requests.put(url, json=payload, headers=headers, timeout=20)
            if resp.ok:
                logger.info("JournalSync: journal pushed to GitHub successfully")
                return True
            logger.warning(f"JournalSync: push failed {resp.status_code} — {resp.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"JournalSync error: {e}")
            return False
