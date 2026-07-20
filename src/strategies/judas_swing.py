"""
Judas Swing (ICT) — a false move at the session open that traps traders and
grabs liquidity, then reverses. You enter the REVERSAL, not the false move.

Implementation (5-minute bars):
- Opening range = high/low of the first `range_minutes` after the session open.
- Within the Judas window, a bar that sweeps ABOVE the opening-range high but
  CLOSES back inside it = a bull trap → enter SHORT.
  A sweep BELOW the low that closes back inside = a bear trap → enter LONG.
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType
from .intraday_utils import session_bars, bar_minute, NEW_YORK_OPEN, LONDON_OPEN


class JudasSwingStrategy(BaseStrategy):
    name = "judas_swing"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 20:
            return []

        p = self.params
        session_open = p.get("session_open", NEW_YORK_OPEN)
        range_minutes = p.get("range_minutes", 15)     # opening-range / liquidity window
        judas_minutes = p.get("judas_window_minutes", 90)  # how long the trap can form
        sl_mult = p.get("sl_atr_multiplier", 1.5)
        tp_mult = p.get("tp_atr_multiplier", 3.0)

        m = bar_minute(df)
        if not (session_open + range_minutes <= m < session_open + range_minutes + judas_minutes):
            return []

        sess = session_bars(df, session_open)
        if len(sess) < 3:
            return []
        sidx = sess.index.tz_convert("UTC") if sess.index.tz is not None else sess.index.tz_localize("UTC")
        sess_mins = sidx.hour * 60 + sidx.minute
        or_bars = sess[sess_mins < session_open + range_minutes]
        if len(or_bars) < 1:
            return []

        or_high = float(or_bars["high"].max())
        or_low = float(or_bars["low"].min())

        row = df.iloc[-1]
        price = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])
        atr = float(row.get("atr", price * 0.005)) or price * 0.005

        # Bull trap: wick swept above the range high, close came back inside → SHORT
        swept_up = high > or_high and price < or_high
        # Bear trap: wick swept below the range low, close came back inside → LONG
        swept_down = low < or_low and price > or_low

        signals: list[Signal] = []
        if swept_up:
            sweep = (high - or_high) / atr
            signals.append(Signal(
                symbol=symbol, signal=SignalType.SHORT, strategy=self.name,
                score=self._score(sweep),
                stop_loss=high + 0.2 * atr,
                take_profit=price - tp_mult * atr,
                metadata={"trap": "bull", "or_high": round(or_high, 4)},
            ))
        elif swept_down:
            sweep = (or_low - low) / atr
            signals.append(Signal(
                symbol=symbol, signal=SignalType.LONG, strategy=self.name,
                score=self._score(sweep),
                stop_loss=low - 0.2 * atr,
                take_profit=price + tp_mult * atr,
                metadata={"trap": "bear", "or_low": round(or_low, 4)},
            ))
        return signals

    @staticmethod
    def _score(sweep_in_atr: float) -> float:
        """A larger liquidity sweep = a more convincing trap."""
        return round(min(0.72 + max(sweep_in_atr, 0.0) * 0.2, 0.95), 4)
