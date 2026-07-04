"""
EMA Crossover Strategy
────────────────────────────────────────────────────────────────────────────
Entry:
  LONG  when fast EMA crosses above slow EMA AND volume > vol_sma * multiplier
  SHORT when fast EMA crosses below slow EMA AND volume > vol_sma * multiplier

Exit (stop-loss / take-profit):
  Stop-loss  = entry ± ATR × sl_atr_multiplier
  Take-profit = entry ± ATR × tp_atr_multiplier

Optional trailing stop activates once trade is profitable.

Confirmation: wait N closed candles after crossover before entering.
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType


class EMACrossoverStrategy(BaseStrategy):
    name = "ema_crossover"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 50:
            return []

        params = self.params
        fast_col = "ema_fast"
        slow_col = "ema_slow"
        vol_mult = params.get("volume_multiplier", 1.2)
        use_volume = params.get("volume_filter", True)
        confirm = params.get("confirmation_candles", 1)
        sl_mult = params.get("sl_atr_multiplier", 1.5)
        tp_mult = params.get("tp_atr_multiplier", 2.5)
        lookback = params.get("crossover_lookback", 3)  # bars to look back for crossover

        signals: list[Signal] = []
        row = df.iloc[-1]

        atr = row.get("atr", row["close"] * 0.01)
        price = row["close"]
        volume_ok = (not use_volume) or (row["volume"] > row["vol_sma"] * vol_mult)

        fast_now = row[fast_col]
        slow_now = row[slow_col]

        # Check if a crossover happened within the last N bars
        crossed_up = False
        crossed_down = False
        for i in range(1, min(lookback + 1, len(df))):
            prev = df.iloc[-(i + 1)]
            fast_prev = prev[fast_col]
            slow_prev = prev[slow_col]
            if (fast_now > slow_now) and (fast_prev <= slow_prev):
                crossed_up = True
                break
            if (fast_now < slow_now) and (fast_prev >= slow_prev):
                crossed_down = True
                break

        # ADX filter — EMA crossover works best in trending markets
        adx_min = params.get("adx_min", 0)
        if adx_min > 0 and row.get("adx", 100) < adx_min:
            return []

        if crossed_up and volume_ok:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=self._score(df, "long"),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"fast_ema": fast_now, "slow_ema": slow_now, "atr": atr},
            ))

        elif crossed_down and volume_ok:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=self._score(df, "short"),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"fast_ema": fast_now, "slow_ema": slow_now, "atr": atr},
            ))

        return signals

    def _score(self, df: pd.DataFrame, direction: str) -> float:
        """Conviction score 0–1 based on trend strength and volume."""
        row = df.iloc[-1]
        atr = row.get("atr", 1)
        price = row["close"]

        # Normalise the EMA gap as fraction of ATR (stronger = higher score)
        ema_gap = abs(row["ema_fast"] - row["ema_slow"]) / (atr + 1e-9)
        gap_score = min(ema_gap / 2.0, 1.0)

        # Volume relative to average (> 1.5x avg → full vol score)
        vol_ratio = row["volume"] / (row["vol_sma"] + 1e-9)
        vol_score = min(vol_ratio / 1.5, 1.0)

        return round((gap_score * 0.6 + vol_score * 0.4), 4)
