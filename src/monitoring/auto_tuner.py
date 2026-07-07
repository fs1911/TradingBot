"""
AutoTuner — reads trading_journal.csv nightly and auto-adjusts strategy params.

Writes deltas to strategy_config_tuned.yaml (overlay over the base config).
Hot-reloads running strategy params without a restart.
Changes are conservative: small steps, hard clamps, min-trade guards.
"""
from __future__ import annotations
import yaml
from pathlib import Path
from datetime import date
import pandas as pd
from loguru import logger


class AutoTuner:
    MIN_TRADES_TOTAL = 30
    MIN_TRADES_PER_STRATEGY = 5

    ADX_MIN_FLOOR, ADX_MIN_CAP = 12, 35
    ADX_MAX_FLOOR, ADX_MAX_CAP = 20, 45
    ATR_SL_FLOOR, ATR_SL_CAP = 1.0, 4.0
    ATR_TP_FLOOR, ATR_TP_CAP = 2.0, 8.0

    def __init__(
        self,
        base_config_path: Path,
        tuned_config_path: Path,
        journal_path: Path,
        strategies: list | None = None,
        telegram=None,
    ):
        self.base_path = base_config_path
        self.tuned_path = tuned_config_path
        self.journal_path = journal_path
        self.strategies = strategies or []
        self.telegram = telegram

    def _load_merged(self) -> dict:
        with open(self.base_path) as f:
            cfg = yaml.safe_load(f)
        if self.tuned_path.exists():
            with open(self.tuned_path) as f:
                tuned = yaml.safe_load(f) or {}
            for strat, params in tuned.items():
                if strat in cfg and isinstance(params, dict):
                    cfg[strat].update(params)
        return cfg

    def _save_tuned(self, tuned: dict) -> None:
        self.tuned_path.parent.mkdir(exist_ok=True)
        with open(self.tuned_path, "w") as f:
            yaml.dump(tuned, f, default_flow_style=False)

    def _hot_reload(self, tuned: dict) -> None:
        for strategy in self.strategies:
            if strategy.name in tuned:
                strategy.params.update(tuned[strategy.name])
                logger.info(f"AutoTuner: hot-reloaded {strategy.name}")

    def run(self) -> None:
        if not self.journal_path.exists():
            logger.info("AutoTuner: no journal yet — skipping")
            return

        try:
            df = pd.read_csv(self.journal_path)
        except Exception as e:
            logger.error(f"AutoTuner: cannot read journal: {e}")
            return

        if len(df) < self.MIN_TRADES_TOTAL:
            logger.info(f"AutoTuner: {len(df)} trades, need {self.MIN_TRADES_TOTAL} — skipping")
            return

        cfg = self._load_merged()

        # Load existing tuned overrides so we don't reset previous adjustments
        existing_tuned: dict = {}
        if self.tuned_path.exists():
            with open(self.tuned_path) as f:
                existing_tuned = yaml.safe_load(f) or {}

        new_tuned = dict(existing_tuned)
        changes: list[str] = []

        for strat in df["strategy"].dropna().unique():
            sub = df[df["strategy"] == strat]
            if len(sub) < self.MIN_TRADES_PER_STRATEGY:
                continue
            if strat not in cfg:
                continue

            strat_cfg = dict(cfg[strat])
            wins = int((sub["pnl_usd"] > 0).sum())
            losses = len(sub) - wins
            win_rate = wins / len(sub)
            avg_win = float(sub[sub["pnl_usd"] > 0]["pnl_usd"].mean()) if wins > 0 else 0.0
            avg_loss = float(abs(sub[sub["pnl_usd"] <= 0]["pnl_usd"].mean())) if losses > 0 else 0.0
            sl_rate = float((sub.get("exit_reason", "") == "sl").mean()) if "exit_reason" in sub else 0.0

            strat_changes: list[str] = []

            # Win rate < 40% → tighten entry (stricter ADX)
            if win_rate < 0.40:
                if "adx_min" in strat_cfg:
                    old = strat_cfg["adx_min"]
                    new = min(old + 2, self.ADX_MIN_CAP)
                    if new != old:
                        strat_cfg["adx_min"] = new
                        strat_changes.append(f"adx_min {old}→{new}")
                if "adx_max" in strat_cfg:
                    old = strat_cfg["adx_max"]
                    new = max(old - 2, self.ADX_MAX_FLOOR)
                    if new != old:
                        strat_cfg["adx_max"] = new
                        strat_changes.append(f"adx_max {old}→{new}")

            # R:R schlechter → TP weiter setzen
            if avg_win > 0 and avg_loss > avg_win * 1.2 and "tp_atr_multiplier" in strat_cfg:
                old = strat_cfg["tp_atr_multiplier"]
                new = round(min(old + 0.5, self.ATR_TP_CAP), 1)
                if new != old:
                    strat_cfg["tp_atr_multiplier"] = new
                    strat_changes.append(f"tp_atr {old}→{new}")

            # Zu viele SL-Exits → SL weiter setzen
            if sl_rate > 0.65 and "sl_atr_multiplier" in strat_cfg:
                old = strat_cfg["sl_atr_multiplier"]
                new = round(min(old + 0.2, self.ATR_SL_CAP), 1)
                if new != old:
                    strat_cfg["sl_atr_multiplier"] = new
                    strat_changes.append(f"sl_atr {old}→{new}")

            # Win rate gut + wenige SL → TP noch weiter (Gewinner laufen lassen)
            if win_rate > 0.55 and sl_rate < 0.40 and "tp_atr_multiplier" in strat_cfg:
                old = strat_cfg["tp_atr_multiplier"]
                new = round(min(old + 0.3, self.ATR_TP_CAP), 1)
                if new != old:
                    strat_cfg["tp_atr_multiplier"] = new
                    strat_changes.append(f"tp_atr {old}→{new} (Gewinner)")

            if strat_changes:
                base_strat = cfg.get(strat, {})
                delta = {k: v for k, v in strat_cfg.items() if v != base_strat.get(k)}
                if delta:
                    new_tuned[strat] = {**new_tuned.get(strat, {}), **delta}
                changes.append(
                    f"<b>{strat}</b> WR={win_rate:.0%} SL={sl_rate:.0%}: "
                    + ", ".join(strat_changes)
                )
                logger.info(f"AutoTuner [{strat}] WR={win_rate:.0%}: {strat_changes}")

        if changes:
            self._save_tuned(new_tuned)
            self._hot_reload(new_tuned)
            if self.telegram:
                self.telegram.send(
                    f"🤖 <b>Auto-Tuner — {date.today()}</b>\n\n"
                    f"Parameter angepasst:\n\n"
                    + "\n".join(f"• {c}" for c in changes)
                )
        else:
            logger.info("AutoTuner: keine Anpassungen nötig")
