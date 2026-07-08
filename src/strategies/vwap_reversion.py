"""
VWAP Mean Reversion Strategy
────────────────────────────────────────────────────────────────────────────
Entry:
  LONG  when price pulled > vwap_deviation_pct below daily VWAP,
        then snaps back above VWAP × (1 - tolerance) AND RSI < rsi_long_max
  SHORT when price pushed > vwap_deviation_pct above daily VWAP,
        then falls back below VWAP × (1 + tolerance) AND RSI > rsi_short_min

Logic: VWAP is the institutional fair-value anchor for the day.
       Significant deviations tend to revert — especially on 15-min bars
       during the US session when liquidity is high.

Exit:
  Stop-loss  = entry ± ATR × sl_atr_multiplier
  Take-profit = entry ± ATR × tp_atr_multiplier
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType


class VWAPReversionStrategy(BaseStrategy):
    name = "vwap_reversion"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 30:
            return []

        params = self.params
        dev_pct = params.get("vwap_deviation_pct", 0.3) / 100  # e.g. 0.3% → 0.003
        tolerance = params.get("reentry_tolerance_pct", 0.1) / 100
        sl_mult = params.get("sl_atr_multiplier", 1.0)
        tp_mult = params.get("tp_atr_multiplier", 2.0)
        rsi_long_max = params.get("rsi_long_max", 55)
        rsi_short_min = params.get("rsi_short_min", 45)
        adx_max = params.get("adx_max", 100)

        row = df.iloc[-1]
        prev = df.iloc[-2]

        price = row["close"]
        atr = row.get("atr", price * 0.01)
        vwap_now = row.get("vwap")
        vwap_prev = prev.get("vwap")
        rsi = row.get("rsi", 50)
        adx_val = row.get("adx", 0)

        # ADX cap: mean-reversion only works in ranging (low-ADX) markets
        if adx_max < 100 and adx_val > adx_max:
            return []

        if (
            vwap_now is None
            or vwap_prev is None
            or pd.isna(vwap_now)
            or pd.isna(vwap_prev)
            or vwap_now <= 0
        ):
            return []

        prev_dev = (prev["close"] - vwap_prev) / vwap_prev
        curr_dev = (price - vwap_now) / vwap_now

        signals: list[Signal] = []

        # LONG: price was significantly below VWAP, now recovering back toward it
        if prev_dev < -dev_pct and curr_dev > -(dev_pct - tolerance) and rsi < rsi_long_max:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=self._score(abs(prev_dev), dev_pct, rsi, "long"),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"vwap": round(vwap_now, 4), "deviation_pct": round(prev_dev * 100, 3)},
            ))

        # SHORT: price was significantly above VWAP, now pulling back
        elif prev_dev > dev_pct and curr_dev < (dev_pct - tolerance) and rsi > rsi_short_min:
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=self._score(abs(prev_dev), dev_pct, rsi, "short"),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"vwap": round(vwap_now, 4), "deviation_pct": round(prev_dev * 100, 3)},
            ))

        return signals

    def _score(self, deviation: float, threshold: float, rsi: float, direction: str) -> float:
        """Higher deviation → stronger reversal conviction."""
        dev_score = min(deviation / (threshold * 4), 1.0)
        if direction == "long":
            rsi_score = max(0.0, (55 - rsi) / 35)
        else:
            rsi_score = max(0.0, (rsi - 45) / 35)
        return round(0.45 + dev_score * 0.35 + rsi_score * 0.20, 4)
