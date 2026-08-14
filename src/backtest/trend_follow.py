"""
Daily-bar trend-following edge test — the one retail hypothesis with documented
historical merit (time-series / absolute momentum; Faber's timing model).

Unlike the intraday indicator strategies, a trend system holds for weeks/months,
trades rarely (so costs barely bite) and tries to ride large moves in commodities
and indices. We test it the same honest way: split each symbol's daily history
into In-Sample (first half) and Out-of-Sample (unseen second half); a real edge
must survive OOS, net of commission + slippage.

Two a-priori, NON-tuned systems are tested so the result can't be curve-fit:
  1. MA20/100 + ATR(14)x3 chandelier trailing stop  (medium-term trend)
  2. Faber SMA200 timing: long while close > 200-day SMA, else flat

Long/flat only (no shorting) — realistic for a paper stock/ETF account.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .oos_runner import split_is_oos, _pool


# ─── canonical systems (fixed in advance — no optimisation) ──────────────────
SYSTEMS = [
    {"name": "MA20/100+ATR3", "fast": 20, "slow": 100, "atr_mult": 3.0, "atr_period": 14},
    {"name": "Faber SMA200",  "fast": 1,  "slow": 200, "atr_mult": 0.0, "atr_period": 14},
]


@dataclass
class TrendTrade:
    pnl: float


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low),
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def run_trend_backtest(df: pd.DataFrame, *, fast: int, slow: int, atr_mult: float,
                       atr_period: int, commission_pct: float = 0.05,
                       slippage_pct: float = 0.03, notional: float = 10_000.0) -> list[TrendTrade]:
    """Simulate a long/flat daily trend system on one symbol; return its trades.

    Entry: close > SMA(slow) and SMA(fast) > SMA(slow).
    Exit:  SMA(fast) < SMA(slow)  (trend break), or — if atr_mult>0 — a chandelier
           trailing stop (highest close since entry − atr_mult*ATR) is broken.
    fast=1 makes SMA(fast)=close, i.e. the Faber close-vs-SMA(slow) timing model.
    """
    if len(df) < slow + 60:
        return []
    df = df.sort_index().copy()
    df["sma_fast"] = df["close"].rolling(fast).mean() if fast > 1 else df["close"]
    df["sma_slow"] = df["close"].rolling(slow).mean()
    df["atr"] = _atr(df, atr_period) if atr_mult > 0 else 0.0
    df = df.dropna()
    if len(df) < 30:
        return []

    comm = commission_pct / 100
    slip = slippage_pct / 100

    trades: list[TrendTrade] = []
    in_pos = False
    entry_px = 0.0
    qty = 0.0
    peak = 0.0

    closes = df["close"].to_numpy()
    fast_a = df["sma_fast"].to_numpy()
    slow_a = df["sma_slow"].to_numpy()
    atr_a = df["atr"].to_numpy() if atr_mult > 0 else np.zeros(len(df))

    def _close_trade(exit_raw: float):
        nonlocal in_pos
        exit_px = exit_raw * (1 - slip)                    # sell into slippage
        gross = (exit_px - entry_px) * qty
        commission = (entry_px + exit_px) * qty * comm
        trades.append(TrendTrade(pnl=gross - commission))
        in_pos = False

    for i in range(len(df)):
        c, f, s, a = closes[i], fast_a[i], slow_a[i], atr_a[i]
        if not in_pos:
            if c > s and f > s:                            # trend up → enter long
                entry_px = c * (1 + slip)                  # buy into slippage
                qty = notional / entry_px
                peak = c
                in_pos = True
        else:
            peak = max(peak, c)
            trend_broken = f < s
            stop_hit = atr_mult > 0 and c < (peak - atr_mult * a)
            if trend_broken or stop_hit:
                _close_trade(c)

    if in_pos:                                             # close at last bar
        _close_trade(closes[-1])
    return trades


def run_trend_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    universes: dict[str, list[str]],
    limit: int = 1500,
    commission_pct: float = 0.05,
    slippage_pct: float = 0.03,
) -> str:
    """Fetch daily history per symbol and test each trend system IS vs OOS,
    pooled across symbols, per asset class. Returns a Markdown report."""
    from datetime import datetime, timezone

    lines = [f"# Daily Trend-Following Edge Test — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    lines.append("Timeframe 1Day · long/flat · net of "
                 f"{commission_pct}% commission + {slippage_pct}% slippage. "
                 "IS = first half of history, OOS = unseen second half. "
                 "A real trend edge survives OOS (PF > 1.15, positive expectancy).")
    lines.append("")

    for group, syms in universes.items():
        # cache daily data per symbol
        data: dict[str, pd.DataFrame] = {}
        for sym in syms:
            try:
                d = get_ohlcv(sym, "1Day", limit)
                if d is not None and len(d) >= 400:
                    data[sym] = d
            except Exception as e:
                logger.warning(f"Trend: could not fetch {sym}: {e}")

        lines.append(f"## {group.upper()}")
        lines.append(f"{len(data)} symbols with ≥400 daily bars: {', '.join(data.keys()) or '—'}")
        lines.append("")
        lines.append("| System | IS trades | IS PF | IS net$ | OOS trades | OOS PF | OOS net$ | OOS win% | Verdict |")
        lines.append("|---|--:|--:|--:|--:|--:|--:|--:|---|")
        if not data:
            lines.append("| — | | | | | | | | no data |")
            lines.append("")
            continue

        for sysdef in SYSTEMS:
            is_tr, oos_tr = [], []
            for sym, d in data.items():
                is_df, oos_df = split_is_oos(d)
                is_tr += run_trend_backtest(is_df, fast=sysdef["fast"], slow=sysdef["slow"],
                                            atr_mult=sysdef["atr_mult"], atr_period=sysdef["atr_period"],
                                            commission_pct=commission_pct, slippage_pct=slippage_pct)
                oos_tr += run_trend_backtest(oos_df, fast=sysdef["fast"], slow=sysdef["slow"],
                                             atr_mult=sysdef["atr_mult"], atr_period=sysdef["atr_period"],
                                             commission_pct=commission_pct, slippage_pct=slippage_pct)
            i, o = _pool(is_tr), _pool(oos_tr)
            if o["trades"] < 15:
                verdict = "too few OOS trades"
            elif o["pf"] > 1.15 and o["exp"] > 0:
                verdict = "✅ edge survives OOS"
            elif i["pf"] > 1.2 and o["pf"] < 1.0:
                verdict = "❌ overfit (IS only)"
            else:
                verdict = "❌ no edge"
            lines.append(
                f"| {sysdef['name']} | {i['trades']} | {i['pf']} | {i['net']:+.0f} | "
                f"{o['trades']} | {o['pf']} | {o['net']:+.0f} | {o['wr']}% | {verdict} |"
            )
        lines.append("")

    lines.append("PF = profit factor (gross win / gross loss; >1 = profitable). Trend systems "
                 "trade rarely, so OOS trade counts are small — treat marginal PFs as noise.")
    return "\n".join(lines)
