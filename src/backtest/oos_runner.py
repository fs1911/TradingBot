"""
Out-of-sample backtest runner — the honest edge test.

For each strategy, run it ALONE over historical bars split into two halves:
  - In-Sample (IS): the first half (where a strategy "should" look good).
  - Out-of-Sample (OOS): the second, unseen half.

A real edge shows up in BOTH halves. An edge that only appears in-sample and
vanishes out-of-sample is overfitting/noise. All results are net of commission
and slippage (via BacktestEngine). Produces a Markdown report.
"""
from __future__ import annotations
from typing import Callable
import pandas as pd
from loguru import logger

from .engine import BacktestEngine
from ..strategies.base_strategy import BaseStrategy


def split_is_oos(df: pd.DataFrame, frac: float = 0.5):
    """Split chronologically into (in-sample, out-of-sample)."""
    df = df.sort_index()
    cut = int(len(df) * frac)
    return df.iloc[:cut], df.iloc[cut:]


def _pool(trades) -> dict:
    """Pool a list of BacktestTrade into net metrics."""
    n = len(trades)
    if n == 0:
        return {"trades": 0, "net": 0.0, "wr": 0.0, "pf": 0.0, "exp": 0.0}
    wins = [t.pnl for t in trades if t.pnl > 0]
    loss = [t.pnl for t in trades if t.pnl <= 0]
    gp = sum(wins)
    gl = abs(sum(loss))
    return {
        "trades": n,
        "net": round(sum(t.pnl for t in trades), 0),
        "wr": round(len(wins) / n * 100),
        "pf": round(gp / gl, 2) if gl > 0 else float("inf"),
        "exp": round(sum(t.pnl for t in trades) / n, 2),
    }


def _run_segment(strat: BaseStrategy, params: dict, seg: pd.DataFrame, symbol: str,
                 commission_pct: float, slippage_pct: float):
    """Run one strategy alone over one data segment; return its trades."""
    if len(seg) < 300:
        return []
    eng = BacktestEngine([strat], commission_pct=commission_pct,
                         slippage_pct=slippage_pct, use_signal_fusion=True)
    try:
        res = eng.run(seg, symbol, params)
        return res.trades
    except Exception as e:
        logger.warning(f"OOS: {strat.name}/{symbol} segment failed: {e}")
        return []


def run_and_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    active_strategies: list[str],
    registry: dict,
    strategy_cfg: dict,
    symbols: list[str],
    timeframe: str,
    limit: int = 6000,
    commission_pct: float = 0.05,
    slippage_pct: float = 0.03,
) -> str:
    """Fetch history per symbol, run each active strategy IS vs OOS, pooled
    across all symbols, and return a Markdown verdict report."""
    from datetime import datetime, timezone

    # Fetch and cache history once per symbol
    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            df = get_ohlcv(sym, timeframe, limit)
            if df is not None and len(df) >= 800:
                data[sym] = df
        except Exception as e:
            logger.warning(f"OOS: could not fetch {sym}: {e}")

    lines: list[str] = []
    lines.append(f"# Out-of-Sample Backtest — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    lines.append("")
    lines.append(f"Timeframe {timeframe} · {len(data)} symbols · net of "
                 f"{commission_pct}% commission + {slippage_pct}% slippage")
    lines.append(f"Symbols: {', '.join(data.keys()) or '—'}")
    lines.append("")
    lines.append("Each strategy run ALONE. In-Sample = first half, "
                 "Out-of-Sample = unseen second half. A real edge survives OOS.")
    lines.append("")
    lines.append("| Strategy | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|--:|---|")

    if not data:
        lines.append("| — | | | | | | | | no data fetched |")
        return "\n".join(lines)

    for name in active_strategies:
        cls = registry.get(name)
        if cls is None:
            continue
        params = strategy_cfg.get(name, {})
        is_trades, oos_trades = [], []
        for sym, df in data.items():
            is_df, oos_df = split_is_oos(df)
            is_trades += _run_segment(cls(params), params, is_df, sym, commission_pct, slippage_pct)
            oos_trades += _run_segment(cls(params), params, oos_df, sym, commission_pct, slippage_pct)
        i, o = _pool(is_trades), _pool(oos_trades)

        # Verdict: an edge must be profitable OUT of sample with enough trades.
        if o["trades"] < 20:
            verdict = "too few OOS trades"
        elif o["pf"] > 1.15 and o["exp"] > 0:
            verdict = "✅ edge survives OOS"
        elif i["pf"] > 1.2 and o["pf"] < 1.0:
            verdict = "❌ overfit (IS only)"
        else:
            verdict = "❌ no edge"
        lines.append(
            f"| {name} | {i['trades']} | {i['pf']} | {i['net']:+.0f} | "
            f"{o['trades']} | {o['pf']} | {o['net']:+.0f} | {o['wr']}% | {verdict} |"
        )

    lines.append("")
    lines.append("PF = profit factor (gross win / gross loss; >1 = profitable). "
                 "A strategy that is strong IS but weak OOS is curve-fit, not an edge.")
    return "\n".join(lines)
