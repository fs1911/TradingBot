"""
Performance Reporter & Trading Journal
────────────────────────────────────────────────────────────────────────────
Generates:
- Daily/weekly/monthly performance summaries
- Per-trade journal entries (CSV + SQLite)
- Equity curve plots
- Strategy-level attribution
- Automated parameter-review recommendations
"""
from __future__ import annotations
import os
import json
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Optional
import pandas as pd
from loguru import logger


class PerformanceReporter:
    """Tracks all trades, computes metrics, and writes reports."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self._journal_path = self.log_dir / "trading_journal.csv"
        self._trades: list[dict] = []
        self._load_existing()

    # ── Trade logging ─────────────────────────────────────────────────────────

    def log_trade(
        self,
        symbol: str,
        strategy: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        qty: float,
        pnl: float,
        entry_time: datetime,
        exit_time: datetime,
        exit_reason: str = "",
        notes: str = "",
    ) -> None:
        hold_secs = round((exit_time - entry_time).total_seconds(), 1)
        record = {
            "date": exit_time.strftime("%Y-%m-%d"),
            "time_entry": entry_time.strftime("%H:%M:%S"),
            "time_exit": exit_time.strftime("%H:%M:%S"),
            "entry_time": entry_time.isoformat(),   # full ISO datetime for AutoTuner analysis
            "hold_seconds": hold_secs,
            "symbol": symbol,
            "strategy": strategy,
            "direction": direction,
            "entry_price": round(entry_price, 6),
            "exit_price": round(exit_price, 6),
            "qty": round(qty, 6),
            "pnl_usd": round(pnl, 2),
            "pnl_pct": round((exit_price - entry_price) / entry_price * 100
                             * (1 if direction == "long" else -1), 3),
            "exit_reason": exit_reason,
            "notes": notes,
        }
        self._trades.append(record)
        self._append_to_csv(record)
        logger.info(f"Trade logged: {direction} {symbol} PnL={pnl:.2f} ({exit_reason})")

    def _append_to_csv(self, record: dict) -> None:
        df = pd.DataFrame([record])
        header = not self._journal_path.exists()
        df.to_csv(self._journal_path, mode="a", header=header, index=False)

    def _load_existing(self) -> None:
        if self._journal_path.exists():
            try:
                df = pd.read_csv(self._journal_path)
                self._trades = df.to_dict("records")
            except Exception:
                self._trades = []

    # ── Reporting ─────────────────────────────────────────────────────────────

    def daily_report(self, target_date: Optional[date] = None) -> dict:
        day = str(target_date or date.today())
        day_trades = [t for t in self._trades if t.get("date") == day]

        if not day_trades:
            return {"date": day, "message": "No trades today."}

        pnl_values = [t["pnl_usd"] for t in day_trades]
        return self._build_report("Daily", day, day_trades, pnl_values)

    def weekly_report(self) -> dict:
        df = pd.DataFrame(self._trades)
        if df.empty:
            return {"message": "No trades on record."}
        df["date"] = pd.to_datetime(df["date"])
        cutoff = pd.Timestamp.today() - pd.Timedelta(days=7)
        week = df[df["date"] >= cutoff]
        if week.empty:
            return {"message": "No trades in the last 7 days."}
        return self._build_report("Weekly (7d)", "last 7 days", week.to_dict("records"),
                                  week["pnl_usd"].tolist())

    def _build_report(self, period: str, label: str, trades: list[dict], pnl_values: list) -> dict:
        total_pnl = sum(pnl_values)
        winners = [p for p in pnl_values if p > 0]
        losers = [p for p in pnl_values if p <= 0]
        win_rate = len(winners) / len(pnl_values) * 100 if pnl_values else 0
        avg_win = sum(winners) / len(winners) if winners else 0
        avg_loss = sum(losers) / len(losers) if losers else 0

        gross_profit = sum(winners)
        gross_loss = abs(sum(losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Strategy breakdown
        strat_pnl: dict[str, float] = {}
        for t in trades:
            strat = t.get("strategy", "unknown")
            strat_pnl[strat] = strat_pnl.get(strat, 0) + t.get("pnl_usd", 0)

        report = {
            "period": period,
            "label": label,
            "total_trades": len(pnl_values),
            "total_pnl_usd": round(total_pnl, 2),
            "win_rate_%": round(win_rate, 1),
            "profit_factor": round(profit_factor, 3),
            "avg_win_usd": round(avg_win, 2),
            "avg_loss_usd": round(avg_loss, 2),
            "strategy_breakdown": {k: round(v, 2) for k, v in strat_pnl.items()},
            "best_trade": round(max(pnl_values), 2) if pnl_values else 0,
            "worst_trade": round(min(pnl_values), 2) if pnl_values else 0,
            "trades": [
                {
                    "symbol": t.get("symbol", ""),
                    "direction": t.get("direction", "long"),
                    "pnl_usd": round(t.get("pnl_usd", 0), 2),
                    "pnl_pct": round(t.get("pnl_pct", 0), 2),
                    "exit_reason": t.get("exit_reason", ""),
                    "strategy": t.get("strategy", ""),
                }
                for t in trades
            ],
        }
        self._print_report(report)
        return report

    def _print_report(self, r: dict) -> None:
        logger.info(f"\n{'═'*60}")
        logger.info(f"  {r['period'].upper()} PERFORMANCE REPORT — {r['label']}")
        logger.info(f"{'─'*60}")
        for k, v in r.items():
            if k in ("period", "label"):
                continue
            if isinstance(v, dict):
                logger.info(f"  {k}:")
                for sk, sv in v.items():
                    logger.info(f"    {sk}: {sv}")
            else:
                logger.info(f"  {k}: {v}")
        logger.info(f"{'═'*60}")

    # ── Self-improvement recommendations ─────────────────────────────────────

    def generate_optimization_hints(self) -> list[str]:
        """
        Analyse trade history and emit parameter-tuning recommendations.
        These are suggestions for the next backtest cycle — not auto-applied.
        """
        hints: list[str] = []
        df = pd.DataFrame(self._trades)
        if df.empty or len(df) < 20:
            return ["Insufficient trade history — need ≥20 trades for recommendations."]

        # Win rate per strategy
        for strat in df["strategy"].unique():
            sub = df[df["strategy"] == strat]
            wr = (sub["pnl_usd"] > 0).mean() * 100
            if wr < 40:
                hints.append(
                    f"Strategy '{strat}': win rate {wr:.1f}% < 40% — "
                    "consider tightening entry conditions or relaxing TP."
                )

        # High average loss relative to average win → poor R:R
        if "pnl_usd" in df.columns:
            w = df[df["pnl_usd"] > 0]["pnl_usd"].mean()
            l = df[df["pnl_usd"] <= 0]["pnl_usd"].mean()
            if w and l and abs(l) > w:
                hints.append(
                    f"R:R ratio is unfavourable (avg win {w:.2f} < avg loss {abs(l):.2f}). "
                    "Increase TP multiplier or tighten SL."
                )

        # Exit reason analysis
        if "exit_reason" in df.columns:
            reason_counts = df["exit_reason"].value_counts(normalize=True)
            sl_pct = reason_counts.get("sl", 0) * 100
            if sl_pct > 60:
                hints.append(
                    f"{sl_pct:.0f}% of trades exit via stop-loss. "
                    "Consider widening SL ATR multiplier or adding entry filter."
                )

        if not hints:
            hints.append("Performance looks healthy — no parameter changes recommended this cycle.")

        return hints

    def export_equity_curve(self, equity: list[float], filepath: str = "") -> str:
        """Save equity curve to CSV."""
        if not filepath:
            filepath = str(self.log_dir / f"equity_{date.today()}.csv")
        pd.Series(equity, name="equity").to_csv(filepath)
        return filepath
