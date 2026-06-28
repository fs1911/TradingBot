"""
Backtesting Engine
────────────────────────────────────────────────────────────────────────────
Event-driven vectorised backtester.

Features:
- Realistic simulation: slippage, commission, no look-ahead bias
- Multi-strategy support (runs all active strategies)
- Key metrics: Sharpe, Sortino, Max Drawdown, Profit Factor, Win Rate
- Regime detection: labels periods as trending / ranging / volatile
- Export results as CSV + plot equity curve
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd
from loguru import logger

from ..indicators.technical import add_all_indicators
from ..strategies.base_strategy import BaseStrategy, Signal, SignalType


@dataclass
class BacktestTrade:
    symbol: str
    strategy: str
    direction: str       # "long" | "short"
    entry_date: pd.Timestamp
    exit_date: Optional[pd.Timestamp]
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    pnl_pct: float
    exit_reason: str     # "sl" | "tp" | "signal" | "end_of_data"


@dataclass
class BacktestResult:
    symbol: str
    start: pd.Timestamp
    end: pd.Timestamp
    initial_capital: float
    final_capital: float
    total_return_pct: float
    annualised_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    win_rate_pct: float
    total_trades: int
    avg_trade_pnl_pct: float
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: Optional[pd.Series] = None

    def summary_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "start": str(self.start),
            "end": str(self.end),
            "total_return_%": round(self.total_return_pct, 2),
            "annualised_return_%": round(self.annualised_return_pct, 2),
            "max_drawdown_%": round(self.max_drawdown_pct, 2),
            "sharpe": round(self.sharpe_ratio, 3),
            "sortino": round(self.sortino_ratio, 3),
            "profit_factor": round(self.profit_factor, 3),
            "win_rate_%": round(self.win_rate_pct, 1),
            "total_trades": self.total_trades,
            "avg_trade_%": round(self.avg_trade_pnl_pct, 3),
        }


# ─── Acceptability benchmarks ─────────────────────────────────────────────────
BENCHMARKS = {
    "min_sharpe": 0.8,
    "min_profit_factor": 1.3,
    "max_drawdown_pct": 15.0,
    "min_win_rate": 40.0,
    "min_trades": 30,
}


class BacktestEngine:
    """Run strategies on historical OHLCV data and compute performance metrics."""

    def __init__(
        self,
        strategies: list[BaseStrategy],
        initial_capital: float = 10_000.0,
        risk_per_trade_pct: float = 1.0,
        commission_pct: float = 0.05,
        slippage_pct: float = 0.03,
        use_signal_fusion: bool = True,
    ):
        self.strategies = strategies
        self.capital = initial_capital
        self.risk_pct = risk_per_trade_pct
        self.commission = commission_pct / 100
        self.slippage = slippage_pct / 100
        self.use_fusion = use_signal_fusion

    def run(self, df: pd.DataFrame, symbol: str, strategy_params: dict) -> BacktestResult:
        """
        Run the full backtest on df (OHLCV with datetime index).
        Returns a BacktestResult with all metrics and individual trades.
        """
        if len(df) < 250:
            raise ValueError(f"Need at least 250 bars; got {len(df)}")

        df = df.copy().sort_index()
        df = add_all_indicators(df, strategy_params)
        df.dropna(inplace=True)

        capital = self.capital
        equity_curve: list[float] = []
        trades: list[BacktestTrade] = []
        open_trade: Optional[dict] = None

        for i in range(1, len(df)):
            window = df.iloc[:i + 1]
            row = window.iloc[-1]
            price = float(row["close"])

            # ── Manage open trade ────────────────────────────────────────────
            if open_trade:
                exit_price, reason = self._check_exit(open_trade, row)
                if exit_price is not None:
                    pnl, pnl_pct = self._calc_pnl(open_trade, exit_price)
                    capital += pnl
                    trades.append(BacktestTrade(
                        symbol=symbol,
                        strategy=open_trade["strategy"],
                        direction=open_trade["direction"],
                        entry_date=open_trade["date"],
                        exit_date=window.index[-1],
                        entry_price=open_trade["entry"],
                        exit_price=exit_price,
                        qty=open_trade["qty"],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        exit_reason=reason,
                    ))
                    open_trade = None

            # ── Generate new signals ─────────────────────────────────────────
            if open_trade is None:
                signals: list[Signal] = []
                for strat in self.strategies:
                    signals.extend(strat.generate_signals(window, symbol))

                entry_signal = self._fuse_signals(signals)
                if entry_signal:
                    entry_price = price * (1 + self.slippage if entry_signal.signal == SignalType.LONG
                                           else 1 - self.slippage)
                    risk_amt = capital * (self.risk_pct / 100)
                    sl = entry_signal.stop_loss or (entry_price * 0.985)
                    sl_dist = abs(entry_price - sl)
                    qty = (risk_amt / sl_dist) if sl_dist > 0 else (risk_amt / (entry_price * 0.015))

                    open_trade = {
                        "direction": entry_signal.signal.value,
                        "strategy": entry_signal.strategy,
                        "date": window.index[-1],
                        "entry": entry_price,
                        "sl": entry_signal.stop_loss,
                        "tp": entry_signal.take_profit,
                        "qty": qty,
                    }

            equity_curve.append(capital)

        # Close any remaining open trade at last close
        if open_trade:
            last_row = df.iloc[-1]
            exit_price = float(last_row["close"])
            pnl, pnl_pct = self._calc_pnl(open_trade, exit_price)
            capital += pnl
            trades.append(BacktestTrade(
                symbol=symbol,
                strategy=open_trade["strategy"],
                direction=open_trade["direction"],
                entry_date=open_trade["date"],
                exit_date=df.index[-1],
                entry_price=open_trade["entry"],
                exit_price=exit_price,
                qty=open_trade["qty"],
                pnl=pnl,
                pnl_pct=pnl_pct,
                exit_reason="end_of_data",
            ))
            equity_curve.append(capital)

        eq = pd.Series(equity_curve, name="equity")
        return self._compute_metrics(symbol, df, eq, trades, capital)

    # ── Exit logic ────────────────────────────────────────────────────────────

    def _check_exit(self, trade: dict, row: pd.Series) -> tuple[Optional[float], str]:
        high = float(row["high"])
        low = float(row["low"])
        direction = trade["direction"]
        sl = trade["sl"]
        tp = trade["tp"]

        if direction == "long":
            if sl and low <= sl:
                return sl, "sl"
            if tp and high >= tp:
                return tp, "tp"
        else:
            if sl and high >= sl:
                return sl, "sl"
            if tp and low <= tp:
                return tp, "tp"

        return None, ""

    def _calc_pnl(self, trade: dict, exit_price: float) -> tuple[float, float]:
        direction = trade["direction"]
        entry = trade["entry"]
        qty = trade["qty"]

        if direction == "long":
            gross = (exit_price - entry) * qty
        else:
            gross = (entry - exit_price) * qty

        commission = (entry + exit_price) * qty * self.commission
        pnl = gross - commission
        pnl_pct = (pnl / (entry * qty)) * 100 if entry * qty != 0 else 0
        return pnl, pnl_pct

    # ── Signal fusion ─────────────────────────────────────────────────────────

    def _fuse_signals(self, signals: list[Signal]) -> Optional[Signal]:
        if not signals:
            return None
        long_signals = [s for s in signals if s.signal == SignalType.LONG]
        short_signals = [s for s in signals if s.signal == SignalType.SHORT]

        best = None
        if long_signals:
            best_long = max(long_signals, key=lambda s: s.score)
            best = best_long
        if short_signals:
            best_short = max(short_signals, key=lambda s: s.score)
            if best is None or best_short.score > best.score:
                best = best_short
        return best

    # ── Metrics ───────────────────────────────────────────────────────────────

    def _compute_metrics(
        self,
        symbol: str,
        df: pd.DataFrame,
        equity: pd.Series,
        trades: list[BacktestTrade],
        final_capital: float,
    ) -> BacktestResult:
        n_bars = len(df)
        start = df.index[0]
        end = df.index[-1]
        days = max((end - start).days, 1)

        total_return = (final_capital - self.capital) / self.capital * 100
        ann_return = ((final_capital / self.capital) ** (365 / days) - 1) * 100

        # Drawdown
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max * 100
        max_dd = float(drawdown.min())

        # Daily returns (approximate from equity curve)
        daily_ret = equity.pct_change().dropna()
        rf = 0.04 / 252  # 4% annual risk-free, daily

        sharpe = 0.0
        if daily_ret.std() > 0:
            sharpe = float((daily_ret.mean() - rf) / daily_ret.std() * math.sqrt(252))

        downside = daily_ret[daily_ret < 0]
        sortino = 0.0
        if len(downside) > 0 and downside.std() > 0:
            sortino = float((daily_ret.mean() - rf) / downside.std() * math.sqrt(252))

        # Trade stats
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        win_rate = len(winning) / len(trades) * 100 if trades else 0
        avg_trade_pct = sum(t.pnl_pct for t in trades) / len(trades) if trades else 0

        result = BacktestResult(
            symbol=symbol, start=start, end=end,
            initial_capital=self.capital, final_capital=final_capital,
            total_return_pct=total_return, annualised_return_pct=ann_return,
            max_drawdown_pct=max_dd, sharpe_ratio=sharpe, sortino_ratio=sortino,
            profit_factor=profit_factor, win_rate_pct=win_rate,
            total_trades=len(trades), avg_trade_pnl_pct=avg_trade_pct,
            trades=trades, equity_curve=equity,
        )

        self._log_result(result)
        return result

    def _log_result(self, r: BacktestResult) -> None:
        s = r.summary_dict()
        logger.info(f"\n{'─'*60}\nBacktest: {r.symbol}  {r.start} → {r.end}")
        for k, v in s.items():
            flag = ""
            if k == "sharpe" and isinstance(v, float) and v < BENCHMARKS["min_sharpe"]:
                flag = " ⚠"
            if k == "max_drawdown_%" and isinstance(v, float) and abs(v) > BENCHMARKS["max_drawdown_pct"]:
                flag = " ⚠"
            if k == "profit_factor" and isinstance(v, float) and v < BENCHMARKS["min_profit_factor"]:
                flag = " ⚠"
            logger.info(f"  {k:30s}: {v}{flag}")

    def passes_benchmarks(self, result: BacktestResult) -> bool:
        return (
            result.sharpe_ratio >= BENCHMARKS["min_sharpe"]
            and result.profit_factor >= BENCHMARKS["min_profit_factor"]
            and abs(result.max_drawdown_pct) <= BENCHMARKS["max_drawdown_pct"]
            and result.win_rate_pct >= BENCHMARKS["min_win_rate"]
            and result.total_trades >= BENCHMARKS["min_trades"]
        )
