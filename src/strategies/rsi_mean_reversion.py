"""
RSI Mean Reversion Strategy
────────────────────────────────────────────────────────────────────────────
Entry:
  LONG  when RSI < oversold threshold AND price > EMA50 (uptrend filter)
  SHORT when RSI > overbought threshold AND price < EMA50 (downtrend filter)

  Extreme readings (RSI < 20 / > 80) generate higher-conviction signals.

Exit:
  Stop-loss  = entry ± ATR × sl_atr_multiplier
  Take-profit = entry ± ATR × tp_atr_multiplier
  Also exit when RSI reverts to 50 (mean reversion complete).
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType


class RSIMeanReversionStrategy(BaseStrategy):
    name = "rsi_mean_reversion"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 60:
            return []

        params = self.params
        oversold = params.get("oversold_threshold", 30)
        overbought = params.get("overbought_threshold", 70)
        extreme_oversold = params.get("extreme_oversold", 20)
        extreme_overbought = params.get("extreme_overbought", 80)
        sl_mult = params.get("sl_atr_multiplier", 1.0)
        tp_mult = params.get("tp_atr_multiplier", 2.0)

        signals: list[Signal] = []
        row = df.iloc[-1]
        prev = df.iloc[-2]

        rsi = row.get("rsi")
        rsi_prev = prev.get("rsi")
        price = row["close"]
        ema50 = row.get("ema_50", price)
        atr = row.get("atr", price * 0.01)

        if rsi is None or rsi_prev is None:
            return []

        # RSI crosses up through oversold threshold (mean reversion long)
        long_signal = (rsi_prev < oversold) and (rsi >= oversold) and (price > ema50)
        # RSI crosses down through overbought threshold (mean reversion short)
        short_signal = (rsi_prev > overbought) and (rsi <= overbought) and (price < ema50)

        if long_signal:
            extreme = rsi <= extreme_oversold
            score = self._score(rsi, oversold, extreme_oversold, "long")
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=score,
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"rsi": rsi, "extreme": extreme, "ema50": ema50},
            ))

        elif short_signal:
            extreme = rsi >= extreme_overbought
            score = self._score(rsi, overbought, extreme_overbought, "short")
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=score,
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"rsi": rsi, "extreme": extreme, "ema50": ema50},
            ))

        return signals

    def _score(self, rsi: float, threshold: float, extreme: float, direction: str) -> float:
        """Score based on how extreme the RSI reading is."""
        if direction == "long":
            depth = max(threshold - rsi, 0)
            max_depth = threshold - extreme
        else:
            depth = max(rsi - threshold, 0)
            max_depth = extreme - threshold

        if max_depth <= 0:
            return 0.5
        return round(min(0.5 + 0.5 * (depth / max_depth), 1.0), 4)
