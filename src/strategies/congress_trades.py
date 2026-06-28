"""
Congress Trades Mirror Strategy
────────────────────────────────────────────────────────────────────────────
US Congress members must file trades within 45 days via the STOCK Act.
QuiverQuant aggregates and provides this data via API.

Logic:
1. Fetch recent congressional trades via QuiverQuant API.
2. Filter to BUY transactions above a minimum size from the last N days.
3. Confirm with a simple trend filter (price > short EMA).
4. Enter LONG positions with standard risk management.
5. Auto-exit after max_age_days or on stop/target.

This is a supplementary signal — always combine with technical confirmation.
Full academic reference: Ziobrowski et al. (2004), "Abnormal Returns from the
Common Stock Investments of the US Senate."

⚠️  Requires QUIVER_API_KEY in .env
"""
from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests
import pandas as pd
from loguru import logger
from .base_strategy import BaseStrategy, Signal, SignalType


QUIVER_BASE = "https://api.quiverquant.com/beta"


class CongressTradesStrategy(BaseStrategy):
    name = "congress_mirror"

    def __init__(self, params: dict):
        super().__init__(params)
        self._api_key = os.environ.get("QUIVER_API_KEY", "")
        self._cache: dict[str, list[dict]] = {}
        self._last_fetch: Optional[datetime] = None
        self._fetch_interval_hours = 6

    # ── Public interface ──────────────────────────────────────────────────────

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if not self._api_key:
            logger.debug("CongressTradesStrategy: no QUIVER_API_KEY, skipping")
            return []
        if df.empty or len(df) < 25:
            return []

        trades = self._get_congress_trades(symbol)
        if not trades:
            return []

        params = self.params
        max_age_h = params.get("max_age_hours", 72)
        min_value = params.get("min_transaction_value", 15000)
        trend_ema = params.get("trend_confirmation_ema", 20)
        position_type = params.get("position_type", "long_only")

        now = datetime.now(timezone.utc)
        signals: list[Signal] = []

        for trade in trades:
            tx_date = self._parse_date(trade.get("TransactionDate", ""))
            if tx_date is None:
                continue
            age_h = (now - tx_date).total_seconds() / 3600
            if age_h > max_age_h:
                continue

            tx_type = trade.get("Transaction", "").lower()
            amount = self._parse_amount(trade.get("Amount", ""))
            if amount < min_value:
                continue

            row = df.iloc[-1]
            price = row["close"]
            ema_col = f"ema_{trend_ema}" if f"ema_{trend_ema}" in df.columns else "ema_fast"
            ema_val = row.get(ema_col, price)
            atr = row.get("atr", price * 0.01)
            trend_ok = price > ema_val

            if "purchase" in tx_type and trend_ok:
                score = self._score(amount, age_h, max_age_h)
                signals.append(Signal(
                    symbol=symbol,
                    signal=SignalType.LONG,
                    strategy=self.name,
                    score=score,
                    stop_loss=price - 1.5 * atr,
                    take_profit=price + 2.5 * atr,
                    metadata={
                        "politician": trade.get("Representative", "Unknown"),
                        "amount": amount,
                        "tx_date": str(tx_date),
                        "age_hours": round(age_h, 1),
                    },
                ))

            elif "sale" in tx_type and not trend_ok and position_type == "long_short":
                score = self._score(amount, age_h, max_age_h)
                signals.append(Signal(
                    symbol=symbol,
                    signal=SignalType.SHORT,
                    strategy=self.name,
                    score=score * 0.7,   # Lower conviction for shorts
                    stop_loss=price + 1.5 * atr,
                    take_profit=price - 2.5 * atr,
                    metadata={
                        "politician": trade.get("Representative", "Unknown"),
                        "amount": amount,
                        "tx_date": str(tx_date),
                    },
                ))

        return signals

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_congress_trades(self, symbol: str) -> list[dict]:
        """Fetch congressional trades for a symbol, with 6-hour cache."""
        now = datetime.now(timezone.utc)
        if (
            symbol in self._cache
            and self._last_fetch
            and (now - self._last_fetch).total_seconds() < self._fetch_interval_hours * 3600
        ):
            return self._cache[symbol]

        try:
            resp = requests.get(
                f"{QUIVER_BASE}/live/congresstrading/{symbol}",
                headers={"Authorization": f"Token {self._api_key}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            self._cache[symbol] = data if isinstance(data, list) else []
            self._last_fetch = now
            logger.debug(f"CongressTrades: fetched {len(self._cache[symbol])} trades for {symbol}")
        except Exception as e:
            logger.warning(f"CongressTrades fetch failed for {symbol}: {e}")
            self._cache.setdefault(symbol, [])

        return self._cache[symbol]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
        return None

    @staticmethod
    def _parse_amount(amount_str: str) -> float:
        """Convert '$15,001 - $50,000' style strings to midpoint float."""
        if not amount_str:
            return 0.0
        parts = str(amount_str).replace("$", "").replace(",", "").split("-")
        try:
            nums = [float(p.strip()) for p in parts if p.strip()]
            return sum(nums) / len(nums) if nums else 0.0
        except ValueError:
            return 0.0

    def _score(self, amount: float, age_h: float, max_age_h: float) -> float:
        """Score 0–1: higher amount, more recent → higher conviction."""
        amount_score = min(amount / 500_000, 1.0)
        recency_score = max(1.0 - age_h / max_age_h, 0.0)
        return round(amount_score * 0.5 + recency_score * 0.5, 4)
