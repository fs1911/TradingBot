"""
AnomalyMonitor (class kept as `AutoTuner` for compatibility) — reads the
trading journal nightly and reports behavioural anomalies: ghost trades,
rapid re-entry, losing streaks. Detection only.

The former parameter-tuning ("self-correction") was removed on 2026-08-06:
nudging ADX/ATR cannot create an edge that isn't there, and it cannot fix
structural bugs (like ghost trades — those need code). What stays valuable is
honest anomaly *detection* + the hourly equity diagnostics elsewhere.
"""
from __future__ import annotations
from pathlib import Path
from datetime import date
import pandas as pd
from loguru import logger


class AutoTuner:
    MIN_TRADES_TOTAL = 30

    def __init__(
        self,
        base_config_path: Path | None = None,
        tuned_config_path: Path | None = None,
        journal_path: Path | None = None,
        strategies: list | None = None,
        telegram=None,
    ):
        # base_config_path / tuned_config_path / strategies are accepted for
        # backward compatibility but no longer used (tuning was removed).
        self.journal_path = journal_path
        self.telegram = telegram

    def _detect_behavioral_patterns(self, df: pd.DataFrame) -> list[str]:
        """Detect temporal/behavioral anomalies not captured by per-strategy metrics."""
        warnings: list[str] = []

        if "entry_time" not in df.columns:
            return warnings

        try:
            df = df.copy()
            df["entry_ts"] = pd.to_datetime(df["entry_time"], utc=True, errors="coerce")
            df = df.dropna(subset=["entry_ts"])
        except Exception:
            return warnings

        # 1. Ghost trades: position closed in ≤2 seconds (spread/mark artifact)
        if "hold_seconds" in df.columns:
            ghost = df[df["hold_seconds"] <= 2]
            if len(ghost) > 10:
                pct = len(ghost) / len(df) * 100
                warnings.append(
                    f"⚠️ <b>Ghost-Trades</b>: {len(ghost)} Trades ({pct:.0f}%) "
                    f"geschlossen in ≤2 Sek — Mindesthaltezeit greift nicht?"
                )
                logger.warning(f"AnomalyMonitor: {len(ghost)} ghost trades detected ({pct:.0f}%)")

        # 2. Rapid re-entry: same symbol traded ≥3 times within 30 minutes
        if "symbol" in df.columns:
            rapid_symbols: list[str] = []
            for sym, grp in df.groupby("symbol"):
                grp_sorted = grp.sort_values("entry_ts")
                times = grp_sorted["entry_ts"].tolist()
                for i in range(len(times) - 2):
                    window_min = (times[i + 2] - times[i]).total_seconds() / 60
                    if window_min <= 30:
                        rapid_symbols.append(str(sym))
                        break
            if rapid_symbols:
                preview = ", ".join(rapid_symbols[:5]) + (" …" if len(rapid_symbols) > 5 else "")
                warnings.append(
                    f"⚠️ <b>Rapid Re-Entry</b>: {len(rapid_symbols)} Symbole "
                    f"≥3× in 30 Min gehandelt: {preview}"
                )
                logger.warning(f"AnomalyMonitor: rapid re-entry on {rapid_symbols}")

        # 3. Losing streak per symbol: ≥4 consecutive losses
        if "symbol" in df.columns and "pnl_usd" in df.columns:
            streak_symbols: list[str] = []
            for sym, grp in df.groupby("symbol"):
                grp_sorted = grp.sort_values("entry_ts")
                streak = 0
                for pnl in grp_sorted["pnl_usd"]:
                    if pnl <= 0:
                        streak += 1
                        if streak >= 4:
                            streak_symbols.append(str(sym))
                            break
                    else:
                        streak = 0
            if streak_symbols:
                preview = ", ".join(streak_symbols[:5]) + (" …" if len(streak_symbols) > 5 else "")
                warnings.append(
                    f"⚠️ <b>Verlust-Serien</b>: {len(streak_symbols)} Symbole "
                    f"mit ≥4 aufeinanderfolgenden Verlusten: {preview}"
                )
                logger.warning(f"AnomalyMonitor: losing streaks on {streak_symbols}")

        return warnings

    def run(self) -> None:
        if not self.journal_path or not self.journal_path.exists():
            logger.info("AnomalyMonitor: no journal yet — skipping")
            return
        try:
            df = pd.read_csv(self.journal_path)
        except Exception as e:
            logger.error(f"AnomalyMonitor: cannot read journal: {e}")
            return
        if len(df) < self.MIN_TRADES_TOTAL:
            logger.info(f"AnomalyMonitor: {len(df)} trades, need {self.MIN_TRADES_TOTAL} — skipping")
            return

        warnings = self._detect_behavioral_patterns(df)
        if warnings:
            if self.telegram:
                self.telegram.send(
                    f"🔎 <b>Anomalie-Check — {date.today()}</b>\n\n"
                    + "\n".join(f"• {w}" for w in warnings)
                )
        else:
            logger.info("AnomalyMonitor: keine Anomalien erkannt")
