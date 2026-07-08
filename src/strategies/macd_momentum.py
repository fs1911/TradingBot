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
        if len(df) < 60:
            return []

        params = self.params
        sl_mult = params.get("sl_atr_multiplier", 1.5)
        tp_mult = params.get("tp_atr_multiplier", 3.0)
        min_hist = params.get("min_histogram_magnitude", 0.001)
        ema_filter_period = params.get("ema_trend_filter", 50)
        ema_col = f"ema_{ema_filter_period}"
        adx_min = params.get("adx_min", 0)

        signals: list[Signal] = []
        row = df.iloc[-1]
        prev = df.iloc[-2]

        hist = row.get("macd_hist")
        hist_prev = prev.get("macd_hist")
        price = row["close"]
        ema_trend = row.get(ema_col, price)
        atr = row.get("atr", price * 0.01)
        adx_val = row.get("adx", 100)

        # ADX floor: skip MACD crossovers in flat/choppy markets
        if adx_min > 0 and adx_val < adx_min:
            return []

        if hist is None or hist_prev is None:
            return []

        hist_crossed_up = (hist > 0) and (hist_prev <= 0)
        hist_crossed_down = (hist < 0) and (hist_prev >= 0)
        magnitude_ok = abs(hist) >= min_hist

        if hist_crossed_up and magnitude_ok and price > ema_trend:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=self._score(row, ema_col, "long"),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"macd": row.get("macd"), "hist": hist, "ema_trend": ema_trend},
            ))

        elif hist_crossed_down and magnitude_ok and price < ema_trend:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=self._score(row, ema_col, "short"),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"macd": row.get("macd"), "hist": hist, "ema_trend": ema_trend},
            ))

        return signals

    def _score(self, row: pd.Series, ema_col: str, direction: str) -> float:
        atr = row.get("atr", 1.0)
        hist = abs(row.get("macd_hist", 0))
        price = row["close"]

        momentum_score = min(hist / (atr * 0.5 + 1e-9), 1.0)

        ema_trend = row.get(ema_col, price)
        trend_score = min(abs(price - ema_trend) / (atr * 5 + 1e-9), 1.0)

        return round(momentum_score * 0.7 + trend_score * 0.3, 4)
