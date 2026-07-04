"""
Bollinger Band Bounce Strategy
────────────────────────────────────────────────────────────────────────────
Entry:
  LONG  when previous bar closes below/at lower band, current bar closes
        back inside (price bounced off oversold territory)
  SHORT when previous bar closes above/at upper band, current bar closes
        back inside (price rejected from overbought territory)

RSI is used as a conviction filter: RSI < 45 for longs, > 55 for shorts.
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType


class BollingerBounceStrategy(BaseStrategy):
    name = "bollinger_bounce"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 25:
            return []

        params = self.params
        sl_mult = params.get("sl_atr_multiplier", 1.2)
        tp_mult = params.get("tp_atr_multiplier", 2.0)
        rsi_long_max = params.get("rsi_long_max", 50)
        rsi_short_min = params.get("rsi_short_min", 50)

        row = df.iloc[-1]
        prev = df.iloc[-2]

        price = row["close"]
        bb_upper = row.get("bb_upper")
        bb_lower = row.get("bb_lower")
        rsi_val = row.get("rsi")
        atr = row.get("atr", price * 0.01)

        if bb_upper is None or bb_lower is None:
            return []

        # ADX regime filter — Bollinger bounce works best in ranging markets
        adx_max = params.get("adx_max", 0)
        if adx_max > 0 and row.get("adx", 0) > adx_max:
            return []

        prev_close = prev["close"]
        prev_lower = prev.get("bb_lower", bb_lower)
        prev_upper = prev.get("bb_upper", bb_upper)

        signals: list[Signal] = []

        # Bounce off lower band → LONG
        bounced_up = (prev_close <= prev_lower) and (price > bb_lower)
        if bounced_up and (rsi_val is None or rsi_val < rsi_long_max):
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=self._score(price, bb_lower, bb_upper, rsi_val, "long"),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"bb_lower": bb_lower, "prev_close": prev_close, "rsi": rsi_val},
            ))

        # Rejection off upper band → SHORT
        rejected_down = (prev_close >= prev_upper) and (price < bb_upper)
        if rejected_down and (rsi_val is None or rsi_val > rsi_short_min):
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=self._score(price, bb_lower, bb_upper, rsi_val, "short"),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"bb_upper": bb_upper, "prev_close": prev_close, "rsi": rsi_val},
            ))

        return signals

    def _score(self, price: float, bb_lower: float, bb_upper: float,
               rsi: float | None, direction: str) -> float:
        band_width = bb_upper - bb_lower + 1e-9

        if direction == "long":
            penetration = max(bb_lower - price, 0) / band_width
            rsi_bonus = max(0, (50 - (rsi or 50)) / 50) * 0.3
        else:
            penetration = max(price - bb_upper, 0) / band_width
            rsi_bonus = max(0, ((rsi or 50) - 50) / 50) * 0.3

        base = min(0.5 + penetration * 2, 0.8)
        return round(min(base + rsi_bonus, 1.0), 4)
