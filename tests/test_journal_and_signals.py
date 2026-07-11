"""
Regression tests for the bugs that reached production during manual changes:

1. Journal CSV column corruption when new columns were added mid-schema
2. Signal-fusion threshold set so high it silently disabled the best strategy
3. AutoTuner behavioural detection reading the wrong column name (stayed blind)
4. SL cooldown lost on restart (in-memory only)

Each test encodes the invariant that was violated, so the same class of
mistake turns the suite red BEFORE it can be deployed.
"""
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pandas as pd

from src.monitoring.reporter import PerformanceReporter
from src.monitoring.auto_tuner import AutoTuner
from src.strategies.base_strategy import Signal, SignalType
from src.bot import TradingBot


CONFIG_DIR = Path(__file__).parent.parent / "config"


# ── 1. Journal CSV integrity ────────────────────────────────────────────────

class TestJournalIntegrity:
    def test_schema_migration_keeps_columns_aligned(self, tmp_path):
        """Adding columns to the record must not shift existing rows' data.

        This is the exact bug: an old-schema journal on disk + a new-schema
        record appended → symbol column ended up holding a timestamp.
        """
        journal = tmp_path / "trading_journal.csv"
        # Old-schema file with NO entry_time / hold_seconds
        pd.DataFrame([{
            "date": "2026-07-08", "time_entry": "14:17:15", "time_exit": "14:53:05",
            "symbol": "META", "strategy": "supertrend", "direction": "long",
            "entry_price": 556.21, "exit_price": 552.78, "qty": 8.98,
            "pnl_usd": -35.1, "pnl_pct": -0.616, "exit_reason": "sl", "notes": "",
        }]).to_csv(journal, index=False)

        r = PerformanceReporter(log_dir=str(tmp_path))
        entry = datetime(2026, 7, 9, 15, 27, 29, tzinfo=timezone.utc)
        r.log_trade(
            symbol="QQQ", strategy="breakout_momentum", direction="short",
            entry_price=701.25, exit_price=705.86, qty=6, pnl=-27.63,
            entry_time=entry, exit_time=entry + timedelta(minutes=51),
            exit_reason="sl",
        )

        df = pd.read_csv(journal)
        # Every symbol must be a real ticker, never a timestamp or number
        assert set(df["symbol"]) == {"META", "QQQ"}
        # The old row keeps its data
        old = df[df["symbol"] == "META"].iloc[0]
        assert old["strategy"] == "supertrend"
        assert old["pnl_usd"] == -35.1
        # The new row lands in the right columns
        new = df[df["symbol"] == "QQQ"].iloc[0]
        assert new["strategy"] == "breakout_momentum"
        assert abs(new["hold_seconds"] - 3060.0) < 1
        assert str(new["entry_time"]).startswith("2026-07-09T15:27:29")

    def test_fresh_journal_has_analysis_columns(self, tmp_path):
        """A brand-new journal must include the columns AutoTuner relies on."""
        r = PerformanceReporter(log_dir=str(tmp_path))
        entry = datetime(2026, 7, 9, 10, 0, 0, tzinfo=timezone.utc)
        r.log_trade(
            symbol="AAPL", strategy="macd_momentum", direction="long",
            entry_price=200.0, exit_price=202.0, qty=10, pnl=20.0,
            entry_time=entry, exit_time=entry + timedelta(seconds=5),
            exit_reason="tp",
        )
        df = pd.read_csv(tmp_path / "trading_journal.csv")
        assert "entry_time" in df.columns
        assert "hold_seconds" in df.columns
        assert df.iloc[0]["hold_seconds"] == 5.0

    def test_self_heals_already_corrupted_file(self, tmp_path):
        """REGRESSION: a journal ALREADY corrupted by the old writer (rows with
        more fields than the header) must be repaired on startup, not crash the
        reporter. This is the failure the first fix missed."""
        journal = tmp_path / "trading_journal.csv"
        # 13-col header, one good row, two corrupted 15-field rows (real shape)
        journal.write_text(
            "date,time_entry,time_exit,symbol,strategy,direction,entry_price,"
            "exit_price,qty,pnl_usd,pnl_pct,exit_reason,notes\n"
            "2026-07-08,10:41:28,10:41:30,DOGE/USD,breakout_momentum,long,"
            "0.0716,0.0713,64117.6,-18.79,-0.409,sl,\n"
            "2026-07-08,15:27:29,16:18:16,2026-07-08T15:27:29+00:00,3047.1,QQQ,"
            "breakout_momentum,short,701.25,705.86,6,-27.63,-0.657,sl,\n"
            "2026-07-10,13:54:09,19:54:53,2026-07-10T13:54:09+00:00,21644.5,NVDA,"
            "breakout_momentum,long,206.3,210.2,22.15,86.28,1.888,time_limit,\n"
        )
        # Instantiating must repair, not raise
        r = PerformanceReporter(log_dir=str(tmp_path))
        df = pd.read_csv(journal)
        assert list(df.columns) == PerformanceReporter.COLUMNS
        # The good row survived; corrupted rows were dropped; no timestamps leaked
        # into the symbol column
        assert "DOGE/USD" in set(df["symbol"])
        assert not any(str(s).startswith("2026-") for s in df["symbol"].dropna())

        # And the reporter can still append cleanly afterwards
        entry = datetime(2026, 7, 11, 2, 0, 0, tzinfo=timezone.utc)
        r.log_trade(symbol="BTC/USD", strategy="supertrend", direction="long",
                    entry_price=64000, exit_price=64500, qty=0.01, pnl=5.0,
                    entry_time=entry, exit_time=entry + timedelta(minutes=45),
                    exit_reason="tp")
        df2 = pd.read_csv(journal)
        new = df2[df2["symbol"] == "BTC/USD"].iloc[0]
        assert new["strategy"] == "supertrend"
        assert float(new["pnl_usd"]) == 5.0
        assert float(new["hold_seconds"]) == 2700.0


# ── 2. Signal fusion threshold ──────────────────────────────────────────────

class TestSignalFusionThreshold:
    """The 1.2 threshold silently disabled breakout_momentum (max score 1.1).
    These tests guard the invariant: a trend-follower with a strong signal
    must be ABLE to open a trade under the configured threshold."""

    def _cfg(self):
        with open(CONFIG_DIR / "strategy_config.yaml") as f:
            return yaml.safe_load(f)["signal_fusion"]

    def _fuse(self, signals, cfg):
        # _fuse_signals only touches cfg + signals, never self — safe to call
        # on a bare instance without running the full broker init.
        bot = object.__new__(TradingBot)
        return TradingBot._fuse_signals(bot, signals, cfg)

    def test_strong_breakout_can_fire_alone(self):
        """REGRESSION: breakout_momentum at full conviction must clear the bar.
        With threshold 1.2 this returned None → strategy was dead."""
        cfg = self._cfg()
        weight = cfg["score_weights"]["breakout_momentum"]
        sig = Signal(symbol="BTC/USD", signal=SignalType.LONG,
                     strategy="breakout_momentum", score=1.0,
                     stop_loss=100, take_profit=110)
        assert 1.0 * weight >= cfg["score_threshold"], (
            f"breakout_momentum max score {weight} < threshold "
            f"{cfg['score_threshold']} — strategy is silently disabled!"
        )
        assert self._fuse([sig], cfg) is not None

    def test_weak_single_signal_rejected(self):
        """A barely-there single signal must NOT open a trade."""
        cfg = self._cfg()
        sig = Signal(symbol="AAPL", signal=SignalType.LONG,
                     strategy="macd_momentum", score=0.5,
                     stop_loss=100, take_profit=110)
        assert self._fuse([sig], cfg) is None

    def test_two_moderate_signals_agree_fires(self):
        """Two strategies agreeing in the same direction should combine."""
        cfg = self._cfg()
        s1 = Signal(symbol="AAPL", signal=SignalType.LONG, strategy="macd_momentum",
                    score=0.7, stop_loss=100, take_profit=110)
        s2 = Signal(symbol="AAPL", signal=SignalType.LONG, strategy="vwap_reversion",
                    score=0.7, stop_loss=100, take_profit=110)
        assert self._fuse([s1, s2], cfg) is not None

    def test_threshold_not_over_tightened(self):
        """REGRESSION: threshold 1.0 caused ~0 crypto trades. A crypto trend
        signal with genuine (not maximal) conviction must still be able to fire
        alone, or crypto — where only supertrend+breakout are eligible — goes
        silent. Guards against setting the threshold too high again."""
        cfg = self._cfg()
        assert cfg["score_threshold"] <= 0.8, (
            f"score_threshold {cfg['score_threshold']} is too high — a single "
            "conviction crypto signal can't fire and the bot stops trading crypto"
        )
        # A breakout with real (0.7) conviction, weighted 0.77, must fire alone
        sig = Signal(symbol="ETH/USD", signal=SignalType.LONG,
                     strategy="breakout_momentum", score=0.7,
                     stop_loss=100, take_profit=110)
        assert self._fuse([sig], cfg) is not None

    def test_opposing_signals_do_not_sum(self):
        """A LONG and a SHORT must not add up into a phantom entry.
        Scores are chosen below threshold individually but above it if summed,
        so this holds regardless of the exact configured threshold."""
        cfg = self._cfg()
        thr = cfg["score_threshold"]
        each = thr * 0.6   # individually below thr, but 2x is above thr
        s1 = Signal(symbol="AAPL", signal=SignalType.LONG, strategy="macd_momentum",
                    score=each, stop_loss=100, take_profit=110)
        s2 = Signal(symbol="AAPL", signal=SignalType.SHORT, strategy="vwap_reversion",
                    score=each, stop_loss=110, take_profit=100)
        # Correct per-direction fusion evaluates each side alone → neither clears
        assert self._fuse([s1, s2], cfg) is None


# ── 3. AutoTuner behavioural detection ──────────────────────────────────────

class TestBehavioralDetection:
    def _tuner(self):
        return AutoTuner(
            base_config_path=CONFIG_DIR / "strategy_config.yaml",
            tuned_config_path=Path("/tmp/_nonexistent_tuned.yaml"),
            journal_path=Path("/tmp/_nonexistent.csv"),
        )

    def _frame(self):
        rows = []
        t0 = datetime(2026, 7, 8, 5, 8, 0, tzinfo=timezone.utc)
        # SOL: 8 rapid same-symbol entries, 2s holds (ghost + rapid)
        for i, pnl in enumerate([-24, -23, -26, 13, 9, 11, 7, 5]):
            rows.append({"entry_time": (t0 + timedelta(minutes=i)).isoformat(),
                         "hold_seconds": 2.0, "symbol": "SOL/USD",
                         "strategy": "breakout_momentum", "pnl_usd": pnl,
                         "exit_reason": "sl"})
        # AVAX: 5 straight losses (streak >= 4)
        for i, pnl in enumerate([-35, -51, -59, -40, -22]):
            rows.append({"entry_time": (t0 + timedelta(minutes=10 + i)).isoformat(),
                         "hold_seconds": 1.5, "symbol": "AVAX/USD",
                         "strategy": "breakout_momentum", "pnl_usd": pnl,
                         "exit_reason": "sl"})
        # 20 clean, spaced-out winners
        for i in range(20):
            rows.append({"entry_time": (t0 + timedelta(hours=2, minutes=i * 7)).isoformat(),
                         "hold_seconds": 300.0, "symbol": f"SYM{i}",
                         "strategy": "supertrend", "pnl_usd": 5.0,
                         "exit_reason": "tp"})
        return pd.DataFrame(rows)

    def test_detects_ghost_trades(self):
        warnings = self._tuner()._detect_behavioral_patterns(self._frame())
        assert any("Ghost" in w for w in warnings)

    def test_detects_rapid_reentry(self):
        warnings = self._tuner()._detect_behavioral_patterns(self._frame())
        assert any("Rapid" in w for w in warnings)

    def test_detects_losing_streak(self):
        warnings = self._tuner()._detect_behavioral_patterns(self._frame())
        assert any("Verlust-Serien" in w for w in warnings)

    def test_clean_data_produces_no_warnings(self):
        """Well-behaved trades must not trigger false alarms."""
        t0 = datetime(2026, 7, 8, 8, 0, 0, tzinfo=timezone.utc)
        rows = [{"entry_time": (t0 + timedelta(hours=i)).isoformat(),
                 "hold_seconds": 400.0, "symbol": f"SYM{i}",
                 "strategy": "supertrend", "pnl_usd": 5.0, "exit_reason": "tp"}
                for i in range(15)]
        warnings = self._tuner()._detect_behavioral_patterns(pd.DataFrame(rows))
        assert warnings == []

    def test_missing_entry_time_column_is_safe(self):
        """Old-schema journal (no entry_time) must not crash detection."""
        df = pd.DataFrame([{"symbol": "AAPL", "pnl_usd": 5.0, "hold_seconds": 2.0}])
        assert self._tuner()._detect_behavioral_patterns(df) == []


# ── 4. SL cooldown persistence ──────────────────────────────────────────────

class TestSLCooldownPersistence:
    def _bot(self, tmp_path):
        bot = object.__new__(TradingBot)
        bot._cooldown_path = tmp_path / "sl_cooldowns.json"
        bot._sl_cooldown = {}
        return bot

    def test_cooldown_survives_reload(self, tmp_path):
        """A cooldown written to disk must be restored after a 'restart'."""
        bot = self._bot(tmp_path)
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        bot._sl_cooldown = {"BTC/USD": future}
        bot._save_sl_cooldowns()

        # Simulate a fresh process
        bot2 = self._bot(tmp_path)
        restored = bot2._load_sl_cooldowns()
        assert "BTC/USD" in restored
        assert abs((restored["BTC/USD"] - future).total_seconds()) < 2

    def test_expired_cooldown_dropped_on_load(self, tmp_path):
        """An already-expired cooldown must not block re-entry after restart."""
        bot = self._bot(tmp_path)
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        bot._sl_cooldown = {"ETH/USD": past}
        bot._save_sl_cooldowns()

        bot2 = self._bot(tmp_path)
        assert "ETH/USD" not in bot2._load_sl_cooldowns()

    def test_missing_file_returns_empty(self, tmp_path):
        bot = self._bot(tmp_path)
        assert bot._load_sl_cooldowns() == {}
