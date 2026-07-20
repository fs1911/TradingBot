"""
Opening Range Breakout (ORB) — London and New York variants.

Concept: the high/low of the first `or_minutes` of a session define the
"opening range". A close beyond that range signals a directional breakout;
trade in the breakout direction for the rest of the session's trade window.

On 5-minute bars the opening range is the first few bars of the session.
This is a coarse but faithful version of the classic ORB setup.
"""
from __future__ import annotations
import pandas as pd
from .base_strategy import BaseStrategy, Signal, SignalType
from .intraday_utils import session_bars, bar_minute, LONDON_OPEN, NEW_YORK_OPEN


class _OpeningRangeBreakout(BaseStrategy):
    """Shared ORB logic. Subclasses set `name` and `default_open`."""

    default_open = NEW_YORK_OPEN

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if len(df) < 20:
            return []

        p = self.params
        session_open = p.get("session_open", self.default_open)
        or_minutes = p.get("or_minutes", 30)         # length of the opening range
        trade_minutes = p.get("trade_window_minutes", 180)  # entries allowed after OR
        sl_mult = p.get("sl_atr_multiplier", 1.5)
        tp_mult = p.get("tp_atr_multiplier", 3.0)

        m = bar_minute(df)
        # Only act after the opening range is complete and within the trade window
        if not (session_open + or_minutes <= m < session_open + or_minutes + trade_minutes):
            return []

        sess = session_bars(df, session_open)
        if len(sess) < 3:
            return []

        # Opening range = bars within [open, open+or_minutes)
        or_end = session_open + or_minutes
        sidx = sess.index.tz_convert("UTC") if sess.index.tz is not None else sess.index.tz_localize("UTC")
        sess_mins = sidx.hour * 60 + sidx.minute
        or_bars = sess[sess_mins < or_end]
        if len(or_bars) < 1:
            return []

        or_high = float(or_bars["high"].max())
        or_low = float(or_bars["low"].min())

        row = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(row["close"])
        atr = float(row.get("atr", price * 0.005)) or price * 0.005

        # Fresh breakout: prior close inside the range, current close beyond it
        broke_up = prev["close"] <= or_high and price > or_high
        broke_down = prev["close"] >= or_low and price < or_low

        signals: list[Signal] = []
        if broke_up:
            dist = (price - or_high) / atr
            signals.append(Signal(
                symbol=symbol, signal=SignalType.LONG, strategy=self.name,
                score=self._score(dist),
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"or_high": round(or_high, 4), "or_low": round(or_low, 4)},
            ))
        elif broke_down:
            dist = (or_low - price) / atr
            signals.append(Signal(
                symbol=symbol, signal=SignalType.SHORT, strategy=self.name,
                score=self._score(dist),
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"or_high": round(or_high, 4), "or_low": round(or_low, 4)},
            ))
        return signals

    @staticmethod
    def _score(dist_in_atr: float) -> float:
        """Bigger break beyond the range = higher conviction."""
        return round(min(0.72 + max(dist_in_atr, 0.0) * 0.15, 0.95), 4)


class LondonORBStrategy(_OpeningRangeBreakout):
    name = "london_orb"
    default_open = LONDON_OPEN


class NewYorkORBStrategy(_OpeningRangeBreakout):
    name = "newyork_orb"
    default_open = NEW_YORK_OPEN
