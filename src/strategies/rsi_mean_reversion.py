"""
RSI Mean Reversion Strategy
────────────────────────────────────────────────────────────────────────────
Entry (LONG):
  1. RSI crosses up through oversold threshold (was below, now above)
  2. Price > EMA50 (only buy dips in uptrends)
  3. Stochastic K also in oversold zone (< stoch_oversold)
  4. Entry candle is green (close > open)

Entry (SHORT):
  1. RSI crosses down through overbought threshold
  2. Price < EMA50 (only short rallies in downtrends)
  3. Stochastic K also in overbought zone (> stoch_overbought)
  4. Entry candle is red (close < open)

Exit:
  Stop-loss  = entry ± ATR × sl_atr_multiplier
  Take-profit = entry ± ATR × tp_atr_multiplier
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
        open_price = row.get("open", price)
        atr = row.get("atr", price * 0.01)

        if rsi is None or rsi_prev is None:
            return []

        # ── EMA trend filter ─────────────────────────────────────────────────
        ema_filter = params.get("ema_trend_filter", 50)
        if ema_filter and ema_filter > 0:
            ema_val = row.get(f"ema_{ema_filter}", price)
            trend_long_ok = price > ema_val
            trend_short_ok = price < ema_val
        else:
            trend_long_ok = True
            trend_short_ok = True

        # ── Stochastic confirmation ──────────────────────────────────────────
        if params.get("stoch_confirmation", False):
            stoch_k = row.get("stoch_k")
            stoch_oversold = params.get("stoch_oversold", 25)
            stoch_overbought = params.get("stoch_overbought", 75)
            if stoch_k is not None:
                stoch_long_ok = stoch_k < stoch_oversold
                stoch_short_ok = stoch_k > stoch_overbought
            else:
                stoch_long_ok = True
                stoch_short_ok = True
        else:
            stoch_long_ok = True
            stoch_short_ok = True

        # ── Candle body direction ────────────────────────────────────────────
        if params.get("require_body_direction", False):
            candle_long_ok = price > open_price   # green candle
            candle_short_ok = price < open_price  # red candle
        else:
            candle_long_ok = True
            candle_short_ok = True

        # ── Signal logic ─────────────────────────────────────────────────────
        # RSI crosses UP through oversold threshold → price recovering
        long_signal = (
            (rsi_prev < oversold) and (rsi >= oversold)
            and trend_long_ok
            and stoch_long_ok
            and candle_long_ok
        )
        # RSI crosses DOWN through overbought threshold → price topping
        short_signal = (
            (rsi_prev > overbought) and (rsi <= overbought)
            and trend_short_ok
            and stoch_short_ok
            and candle_short_ok
        )

        if long_signal:
            score = self._score(rsi, oversold, extreme_oversold, "long")
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.LONG,
                strategy=self.name,
                score=score,
                stop_loss=price - sl_mult * atr,
                take_profit=price + tp_mult * atr,
                metadata={"rsi": rsi, "stoch_k": row.get("stoch_k")},
            ))

        elif short_signal:
            score = self._score(rsi, overbought, extreme_overbought, "short")
            signals.append(Signal(
                symbol=symbol,
                signal=SignalType.SHORT,
                strategy=self.name,
                score=score,
                stop_loss=price + sl_mult * atr,
                take_profit=price - tp_mult * atr,
                metadata={"rsi": rsi, "stoch_k": row.get("stoch_k")},
            ))

        return signals

    def _score(self, rsi: float, threshold: float, extreme: float, direction: str) -> float:
        """Score 0–1 based on how far RSI penetrated the extreme zone."""
        if direction == "long":
            depth = max(threshold - rsi, 0)
            max_depth = threshold - extreme
        else:
            depth = max(rsi - threshold, 0)
            max_depth = extreme - threshold

        if max_depth <= 0:
            return 0.5
        return round(min(0.5 + 0.5 * (depth / max_depth), 1.0), 4)
