"""
Supertrend Strategy
────────────────────────────────────────────────────────────────────────────
Entry:
  LONG  when Supertrend flips from bearish (-1) to bullish (+1)
  SHORT when Supertrend flips from bullish (+1) to bearish (-1)

Supertrend is an ATR-based trailing stop band that flips direction when
price crosses the band. It is one of the most reliable trend-following
indicators for automated trading.

ADX filter: only enter when trend is strong enough (ADX > adx_min).
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType


class SupertrendStrategy(BaseStrategy):
    name = "supertrend"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 30:
            return []

        params = self.params
        sl_mult = params.get("sl_atr_multiplier", 2.0)
        tp_mult = params.get("tp_atr_multiplier", 4.0)
        adx_min = params.get("adx_min", 20)

        row = df.iloc[-1]
        prev = df.iloc[-2]

        direction = row.get("st_direction")
        direction_prev = prev.get("st_direction")
        price = row["close"]
        atr = row.get("atr", price * 0.01)
        adx_val = row.get("adx", 100)

        if direction is None or direction_prev is None:
            return []

        # ADX filter — only trade in trending markets
        if adx_min > 0 and adx_val < adx_min:
            return []

        signals: list[Signal] = []

        if direction_prev == -1 and direction == 1:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=self._score(adx_val),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"adx": round(adx_val, 1), "st_value": round(row.get("st_value", 0), 4)},
            ))

        elif direction_prev == 1 and direction == -1:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=self._score(adx_val),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"adx": round(adx_val, 1), "st_value": round(row.get("st_value", 0), 4)},
            ))

        return signals

    def _score(self, adx_val: float) -> float:
        """Higher ADX = stronger trend = higher conviction."""
        return round(min(0.5 + (adx_val - 20) / 80, 1.0), 4)
