"""
Tests for the ICT / session day-trading experiment strategies:
London ORB, New York ORB, Judas Swing, 9am Silver Bullet.

These are time-gated, so the tests build 5-minute bars with a tz-aware UTC
index and place the trigger bar inside the strategy's window. They verify the
setup fires in the right direction, stays silent outside its window, and never
crashes on short/empty input.
"""
import pandas as pd

from src.strategies.opening_range_breakout import LondonORBStrategy, NewYorkORBStrategy
from src.strategies.judas_swing import JudasSwingStrategy
from src.strategies.silver_bullet import SilverBulletStrategy
from src.strategies.base_strategy import SignalType


def _frame(day="2026-07-20", start="11:00", end="14:05"):
    """Flat 5-minute OHLCV frame (~100) with a tz-aware UTC index and atr col."""
    idx = pd.date_range(f"{day} {start}", f"{day} {end}", freq="5min", tz="UTC")
    df = pd.DataFrame(index=idx)
    df["open"] = 100.5
    df["high"] = 100.6
    df["low"] = 100.4
    df["close"] = 100.5
    df["volume"] = 1000.0
    df["atr"] = 0.2
    return df


def _set(df, ts, o, h, l, c):
    t = pd.Timestamp(ts, tz="UTC")
    df.loc[t, ["open", "high", "low", "close"]] = [o, h, l, c]


class TestNewYorkORB:
    def test_breakout_up_fires_long(self):
        df = _frame(end="14:00")  # last bar 14:00 UTC (min 840)
        # Opening range 13:30–13:55 → high 101, low 100
        for t in ["13:30", "13:35", "13:40", "13:45", "13:50"]:
            _set(df, f"2026-07-20 {t}", 100.5, 101.0, 100.0, 100.5)
        _set(df, "2026-07-20 13:55", 100.5, 101.0, 100.0, 100.5)   # prev close inside
        _set(df, "2026-07-20 14:00", 101.0, 101.6, 101.0, 101.5)   # closes above OR high
        sigs = NewYorkORBStrategy({}).generate_signals(df, "AAPL")
        assert len(sigs) == 1 and sigs[0].signal == SignalType.LONG

    def test_silent_before_session(self):
        df = _frame(start="10:00", end="12:00")  # last bar 12:00 (min 720 < 810)
        assert NewYorkORBStrategy({}).generate_signals(df, "AAPL") == []


class TestLondonORB:
    def test_breakout_down_fires_short(self):
        # Build a London-session frame ending 08:00 UTC (min 480)
        df = _frame(start="05:00", end="08:00")
        for t in ["07:00", "07:05", "07:10", "07:15", "07:20"]:
            _set(df, f"2026-07-20 {t}", 100.5, 101.0, 100.0, 100.5)  # OR high 101 / low 100
        _set(df, "2026-07-20 07:25", 100.5, 101.0, 100.0, 100.5)     # prev close inside
        _set(df, "2026-07-20 08:00", 100.0, 100.0, 99.0, 99.5)       # closes below OR low
        sigs = LondonORBStrategy({}).generate_signals(df, "BTC/USD")
        assert len(sigs) == 1 and sigs[0].signal == SignalType.SHORT


class TestJudasSwing:
    def test_bull_trap_fires_short(self):
        df = _frame(end="13:50")  # last bar 13:50 (min 830), window [825,915)
        # Opening range 13:30–13:40 (mins <825) → high 101, low 100
        for t in ["13:30", "13:35", "13:40"]:
            _set(df, f"2026-07-20 {t}", 100.5, 101.0, 100.0, 100.5)
        _set(df, "2026-07-20 13:45", 100.5, 100.8, 100.2, 100.5)
        _set(df, "2026-07-20 13:50", 100.5, 102.0, 100.4, 100.5)   # wick above 101, close back inside
        sigs = JudasSwingStrategy({}).generate_signals(df, "AAPL")
        assert len(sigs) == 1 and sigs[0].signal == SignalType.SHORT


class TestSilverBullet:
    def test_up_momentum_pullback_fires_long(self):
        df = _frame(start="07:00", end="09:30")  # last bar 09:30 (min 570), window [540,600)
        # Rising closes over the lookback so momentum > 0
        base = "2026-07-20"
        rising = ["09:00", "09:05", "09:10", "09:15", "09:20", "09:25"]
        px = 100.5
        for t in rising:
            px += 0.3
            _set(df, f"{base} {t}", px - 0.1, px + 0.2, px - 0.2, px)
        _set(df, f"{base} 09:25", 101.9, 102.0, 101.4, 101.5)   # prev bar red (pullback)
        _set(df, f"{base} 09:30", 101.5, 102.3, 101.5, 102.2)   # entry bar green
        sigs = SilverBulletStrategy({}).generate_signals(df, "AAPL")
        assert len(sigs) == 1 and sigs[0].signal == SignalType.LONG

    def test_silent_outside_window(self):
        df = _frame(start="11:00", end="12:00")  # min 720, outside [540,600)
        assert SilverBulletStrategy({}).generate_signals(df, "AAPL") == []


class TestRobustness:
    def test_all_handle_short_input(self):
        tiny = _frame(start="13:30", end="13:45")  # only 4 bars (< 20)
        for strat in (LondonORBStrategy({}), NewYorkORBStrategy({}),
                      JudasSwingStrategy({}), SilverBulletStrategy({})):
            assert strat.generate_signals(tiny, "AAPL") == []
