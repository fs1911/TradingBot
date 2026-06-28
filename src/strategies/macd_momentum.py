"""
MACD Momentum Strategy
────────────────────────────────────────────────────────────────────────────
Entry:
  LONG  when MACD line crosses above signal line (histogram turns positive)
        AND EMA200 confirms macro uptrend (price > EMA200)
  SHORT when MACD line crosses below signal line (histogram turns negative)
        AND price < EMA200

Signal is filtered by minimum histogram magnitude to avoid weak crossovers.

Exit:
  Stop-loss / Take-profit via ATR multipliers.
  Also exit when histogram crosses zero in opposite direction.
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType


class MACDMomentumStrategy(BaseStrategy):
    name = "macd_momentum"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 210:   # Need enough history for EMA200
            return []

        params = self.params
        sl_mult = params.get("sl_atr_multiplier", 1.5)
        tp_mult = params.get("tp_atr_multiplier", 3.0)
        min_hist = params.get("min_histogram_magnitude", 0.001)

        signals: list[Signal] = []
        row = df.iloc[-1]
        prev = df.iloc[-2]

        hist = row.get("macd_hist")
        hist_prev = prev.get("macd_hist")
        price = row["close"]
        ema200 = row.get("ema_200", price)
        atr = row.get("atr", price * 0.01)

        if hist is None or hist_prev is None:
            return []

        hist_crossed_up = (hist > 0) and (hist_prev <= 0)
        hist_crossed_down = (hist < 0) and (hist_prev >= 0)
        magnitude_ok = abs(hist) >= min_hist

        if hist_crossed_up and magnitude_ok and price > ema200:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=self._score(row, "long"),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"macd": row.get("macd"), "hist": hist, "ema200": ema200},
            ))

        elif hist_crossed_down and magnitude_ok and price < ema200:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=self._score(row, "short"),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"macd": row.get("macd"), "hist": hist, "ema200": ema200},
            ))

        return signals

    def _score(self, row: pd.Series, direction: str) -> float:
        atr = row.get("atr", 1.0)
        hist = abs(row.get("macd_hist", 0))
        price = row["close"]

        # Score based on momentum magnitude relative to ATR
        momentum_score = min(hist / (atr * 0.5 + 1e-9), 1.0)

        # Trend alignment score (price distance from EMA200)
        ema200 = row.get("ema_200", price)
        trend_score = min(abs(price - ema200) / (atr * 5 + 1e-9), 1.0)

        return round(momentum_score * 0.7 + trend_score * 0.3, 4)
