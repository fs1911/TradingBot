"""
Breakout Momentum Strategy
────────────────────────────────────────────────────────────────────────────
Entry:
  LONG  when price closes above the highest high of the last N bars
        AND volume is above average (confirms institutional participation)
  SHORT when price closes below the lowest low of the last N bars
        AND volume above average

Breakout momentum is statistically one of the most robust edges in
markets: a price that breaks a multi-bar range with volume tends to
continue in that direction.

ADX filter: stronger trend confirmation when ADX > adx_min.
EMA trend filter: only long above EMA50, only short below EMA50.
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType


class BreakoutMomentumStrategy(BaseStrategy):
    name = "breakout_momentum"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 50:
            return []

        params = self.params
        lookback = params.get("breakout_lookback", 20)
        vol_mult = params.get("volume_multiplier", 1.5)
        sl_mult = params.get("sl_atr_multiplier", 2.0)
        tp_mult = params.get("tp_atr_multiplier", 5.0)
        adx_min = params.get("adx_min", 0)
        ema_filter = params.get("ema_trend_filter", 50)

        row = df.iloc[-1]
        price = row["close"]
        atr = row.get("atr", price * 0.01)
        adx_val = row.get("adx", 100)

        # Trend filter
        if ema_filter and ema_filter > 0:
            ema_val = row.get(f"ema_{ema_filter}", price)
            trend_long_ok = price > ema_val
            trend_short_ok = price < ema_val
        else:
            trend_long_ok = True
            trend_short_ok = True

        # ADX filter
        if adx_min > 0 and adx_val < adx_min:
            return []

        # Volume filter
        vol_ok = row["volume"] > row.get("vol_sma", row["volume"]) * vol_mult

        # Lookback range (exclude current bar)
        window = df.iloc[-(lookback + 1):-1]
        if len(window) < lookback:
            return []
        highest_high = window["high"].max()
        lowest_low = window["low"].min()

        signals: list[Signal] = []

        if price > highest_high and vol_ok and trend_long_ok:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=self._score(price, highest_high, atr),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"breakout_level": round(highest_high, 4), "adx": round(adx_val, 1)},
            ))

        elif price < lowest_low and vol_ok and trend_short_ok:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=self._score(price, lowest_low, atr),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"breakdown_level": round(lowest_low, 4), "adx": round(adx_val, 1)},
            ))

        return signals

    def _score(self, price: float, level: float, atr: float) -> float:
        """Larger breakout distance = higher conviction."""
        distance = abs(price - level)
        return round(min(0.5 + distance / (atr * 2 + 1e-9), 1.0), 4)
