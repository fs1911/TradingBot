"""
9-Uhr-Bullet — a fixed-time-window momentum setup (ICT "Silver Bullet" family).

The real ICT Silver Bullet hunts a Fair Value Gap inside a set 1-hour window.
On 5-minute bars we use a robust proxy: inside the configured window, enter in
the direction of short-term momentum after a minor pullback (a bullish bar that
follows a red bar while momentum is up → LONG; mirror → SHORT).

Window defaults to 09:00–10:00 UTC; configurable via window_start/window_end
(UTC minutes-of-day).
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType
from .intraday_utils import bar_minute


class SilverBulletStrategy(BaseStrategy):
    name = "silver_bullet"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 20:
            return []

        p = self.params
        w_start = p.get("window_start", 9 * 60)   # 09:00 UTC
        w_end = p.get("window_end", 10 * 60)      # 10:00 UTC
        lookback = p.get("momentum_lookback", 6)  # ~30 min on 5m bars
        sl_mult = p.get("sl_atr_multiplier", 1.5)
        tp_mult = p.get("tp_atr_multiplier", 3.0)

        if not (w_start <= bar_minute(df) < w_end):
            return []
        if len(df) < lookback + 2:
            return []

        row = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(row["close"])
        atr = float(row.get("atr", price * 0.005)) or price * 0.005
        momentum = price - float(df["close"].iloc[-(lookback + 1)])

        bull_bar = row["close"] > row["open"]
        bear_bar = row["close"] < row["open"]
        prev_red = prev["close"] < prev["open"]     # minor pullback before the entry bar
        prev_green = prev["close"] > prev["open"]

        signals: list[Signal] = []
        if momentum > 0 and bull_bar and prev_red:
            signals.append(Signal(
                symbol=symbol, signal=SignalType.LONG, strategy=self.name,
                score=self._score(momentum, atr),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"momentum": round(momentum, 4)},
            ))
        elif momentum < 0 and bear_bar and prev_green:
            signals.append(Signal(
                symbol=symbol, signal=SignalType.SHORT, strategy=self.name,
                score=self._score(momentum, atr),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"momentum": round(momentum, 4)},
            ))
        return signals

    @staticmethod
    def _score(momentum: float, atr: float) -> float:
        strength = abs(momentum) / (atr * 3 + 1e-9)
        return round(min(0.72 + strength * 0.15, 0.93), 4)
