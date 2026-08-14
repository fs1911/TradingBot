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


def trend_daily_returns(df: pd.DataFrame, *, fast: int, slow: int, atr_mult: float,
                        atr_period: int, commission_pct: float = 0.05,
                        slippage_pct: float = 0.03) -> pd.DataFrame:
    """Return a daily DataFrame with columns 'ret' (net strategy return that day)
    and 'held' (1 if in a long position during the day, else 0). Position for day
    i is decided at the prior close (no look-ahead); costs are charged on the days
    the position switches on/off. Enables equity-curve and drawdown analysis."""
    empty = pd.DataFrame(columns=["ret", "held"])
    if len(df) < slow + 60:
        return empty
    df = df.sort_index().copy()
    df["sma_fast"] = df["close"].rolling(fast).mean() if fast > 1 else df["close"]
    df["sma_slow"] = df["close"].rolling(slow).mean()
    df["atr"] = _atr(df, atr_period) if atr_mult > 0 else 0.0
    df = df.dropna()
    if len(df) < 30:
        return empty

    close = df["close"].to_numpy()
    fast_a = df["sma_fast"].to_numpy()
    slow_a = df["sma_slow"].to_numpy()
    atr_a = df["atr"].to_numpy() if atr_mult > 0 else np.zeros(len(df))
    asset_ret = df["close"].pct_change().fillna(0).to_numpy()
    cost = (commission_pct + slippage_pct) / 100

    n = len(df)
    state = np.zeros(n)          # position state AT close i (after that day's decision)
    in_pos = False
    peak = 0.0
    for i in range(n):
        if not in_pos:
            if close[i] > slow_a[i] and fast_a[i] > slow_a[i]:
                in_pos, peak = True, close[i]
        else:
            peak = max(peak, close[i])
            if fast_a[i] < slow_a[i] or (atr_mult > 0 and close[i] < peak - atr_mult * atr_a[i]):
                in_pos = False
        state[i] = 1.0 if in_pos else 0.0

    held = np.concatenate([[0.0], state[:-1]])           # position DURING day i = state at close i-1
    turn = np.abs(np.diff(np.concatenate([[0.0], held])))  # 1 on days the position switches
    strat = held * asset_ret - turn * cost
    return pd.DataFrame({"ret": strat, "held": held}, index=df.index)


def _curve_stats(returns: pd.Series) -> dict:
    """Total return %, max drawdown %, and MAR (return / |maxDD|) from a daily
    return series."""
    returns = returns.dropna()
    if len(returns) < 5:
        return {"ret": 0.0, "dd": 0.0, "mar": 0.0}
    eq = (1 + returns).cumprod()
    total = float(eq.iloc[-1] - 1)
    dd = float((eq / eq.cummax() - 1).min())
    mar = (total / abs(dd)) if dd < 0 else float("inf")
    return {"ret": total * 100, "dd": dd * 100, "mar": round(mar, 2)}


def run_benchmark_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    universes: dict[str, list[str]],
    limit: int = 1500,
    commission_pct: float = 0.05,
    slippage_pct: float = 0.03,
) -> str:
    """The decisive test: does the trend system beat simply buying and holding?
    Builds an equal-weight (daily-rebalanced) portfolio per asset class over the
    unseen OOS half and compares Trend vs Buy&Hold on return AND max drawdown.
    Trend's real value is risk-adjusted (MAR = return/|maxDD|), not raw return."""
    from datetime import datetime, timezone

    lines = [f"# Trend vs Buy&Hold Benchmark — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    lines.append("Equal-weight, daily-rebalanced portfolio per asset class, on the "
                 "unseen OOS half only, net of costs. MAR = total return / |max drawdown| "
                 "(higher = better risk-adjusted). A trend edge should beat Buy&Hold on "
                 "MAR — same/greater return for much smaller drawdown.")
    lines.append("")

    for group, syms in universes.items():
        data: dict[str, pd.DataFrame] = {}
        for sym in syms:
            try:
                d = get_ohlcv(sym, "1Day", limit)
                if d is not None and len(d) >= 400:
                    data[sym] = d
            except Exception as e:
                logger.warning(f"Benchmark: could not fetch {sym}: {e}")

        lines.append(f"## {group.upper()}")
        lines.append(f"{len(data)} symbols, OOS half: {', '.join(data.keys()) or '—'}")
        lines.append("")
        lines.append("| System | Trend ret% | Trend maxDD% | Trend MAR | B&H ret% | B&H maxDD% | B&H MAR | %inMkt | Verdict |")
        lines.append("|---|--:|--:|--:|--:|--:|--:|--:|---|")
        if not data:
            lines.append("| — | | | | | | | | no data |")
            lines.append("")
            continue

        # Buy&Hold portfolio (always invested) over OOS
        bh_cols = {}
        oos_cache = {}
        for sym, d in data.items():
            _, oos = split_is_oos(d)
            oos_cache[sym] = oos
            bh_cols[sym] = oos["close"].pct_change().fillna(0)
        bh_port = pd.DataFrame(bh_cols).mean(axis=1)
        bh = _curve_stats(bh_port)

        for sysdef in SYSTEMS:
            ret_cols, held_cols = {}, {}
            for sym, oos in oos_cache.items():
                r = trend_daily_returns(oos, fast=sysdef["fast"], slow=sysdef["slow"],
                                        atr_mult=sysdef["atr_mult"], atr_period=sysdef["atr_period"],
                                        commission_pct=commission_pct, slippage_pct=slippage_pct)
                if not r.empty:
                    ret_cols[sym] = r["ret"]
                    held_cols[sym] = r["held"]
            if not ret_cols:
                continue
            port = pd.DataFrame(ret_cols).mean(axis=1)
            st = _curve_stats(port)
            in_mkt = float(pd.DataFrame(held_cols).mean(axis=1).mean() * 100)

            # Verdict: trend earns its keep only if risk-adjusted return (MAR) beats
            # holding. Raw return alone doesn't count — that can be pure market beta.
            if st["ret"] <= 0:
                verdict = "❌ loses money"
            elif st["mar"] >= bh["mar"] * 1.1:
                verdict = "✅ beats hold (risk-adj)"
            elif abs(st["dd"]) < abs(bh["dd"]) * 0.6 and st["ret"] > bh["ret"] * 0.6:
                verdict = "⚠️ less return, less risk"
            else:
                verdict = "❌ no better than holding"
            lines.append(
                f"| {sysdef['name']} | {st['ret']:+.0f} | {st['dd']:.0f} | {st['mar']} | "
                f"{bh['ret']:+.0f} | {bh['dd']:.0f} | {bh['mar']} | {in_mkt:.0f}% | {verdict} |"
            )
        lines.append("")

    lines.append("Trend-following's documented benefit is smaller drawdowns, not higher "
                 "returns. If Trend doesn't beat Buy&Hold on MAR, the profit was market beta "
                 "(the assets rose), not an edge — and the universe here is hindsight-selected.")
    return "\n".join(lines)


def run_walkforward_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    symbols: list[str],
    window: int = 252,
    step: int = 63,
    limit: int = 2500,
    commission_pct: float = 0.05,
    slippage_pct: float = 0.03,
) -> str:
    """Robustness test: slide a `window`-day window (stepped by `step` days) across
    the full daily history and, in each window, compare the trend portfolio vs
    Buy&Hold on MAR. A robust edge beats B&H in MOST windows — not just the latest
    one. Systems are fixed (no per-window optimisation), so this measures how the
    live system would have held up across many regimes."""
    from datetime import datetime, timezone

    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            d = get_ohlcv(sym, "1Day", limit)
            if d is not None and len(d) >= 400:
                data[sym] = d
        except Exception as e:
            logger.warning(f"Walk-forward: could not fetch {sym}: {e}")

    lines = [f"# Metals Walk-Forward — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    lines.append(f"{len(data)} symbols · {window}-day rolling windows stepped {step} days · "
                 "equal-weight portfolio · net of costs. Each window: Trend vs Buy&Hold MAR "
                 "(return/|maxDD|). A robust edge beats B&H in most windows, not just recently.")
    lines.append(f"Symbols: {', '.join(data.keys()) or '—'}")
    lines.append("")
    if not data:
        lines.append("_no data_")
        return "\n".join(lines)

    bh_port = pd.DataFrame({s: d["close"].pct_change().fillna(0) for s, d in data.items()}).mean(axis=1)

    for sysdef in SYSTEMS:
        tr_cols = {}
        for sym, d in data.items():
            r = trend_daily_returns(d, fast=sysdef["fast"], slow=sysdef["slow"],
                                    atr_mult=sysdef["atr_mult"], atr_period=sysdef["atr_period"],
                                    commission_pct=commission_pct, slippage_pct=slippage_pct)
            if not r.empty:
                tr_cols[sym] = r["ret"]
        if not tr_cols:
            continue
        tr_port = pd.DataFrame(tr_cols).mean(axis=1)
        common = tr_port.index.intersection(bh_port.index)
        tr, bh = tr_port.loc[common], bh_port.loc[common]

        rows = []
        i = 0
        while i + window <= len(common):
            ts = _curve_stats(tr.iloc[i:i + window])
            bs = _curve_stats(bh.iloc[i:i + window])
            beat = ts["mar"] > bs["mar"] and ts["ret"] > 0
            rows.append((common[i], common[i + window - 1], ts, bs, beat))
            i += step

        n = len(rows)
        n_beat = sum(1 for r in rows if r[4])
        n_pos = sum(1 for r in rows if r[2]["ret"] > 0)
        if n == 0:
            lines.append(f"## {sysdef['name']}\n_history too short for {window}-day windows_\n")
            continue
        pct_beat = round(100 * n_beat / n)
        pct_pos = round(100 * n_pos / n)
        if pct_beat >= 60 and pct_pos >= 60:
            verdict = "✅ robust edge (beats hold in most windows)"
        elif pct_beat >= 40:
            verdict = "⚠️ regime-dependent"
        else:
            verdict = "❌ not robust — recent luck"

        lines.append(f"## {sysdef['name']} — {verdict}")
        lines.append(f"Beat Buy&Hold in **{n_beat}/{n} windows ({pct_beat}%)** · "
                     f"positive in {n_pos}/{n} ({pct_pos}%)")
        lines.append("")
        lines.append("| Window | Trend ret% | Trend MAR | B&H ret% | B&H MAR | Trend wins? |")
        lines.append("|---|--:|--:|--:|--:|:--:|")
        for start, end, ts, bs, beat in rows:
            lines.append(f"| {start:%Y-%m} → {end:%Y-%m} | {ts['ret']:+.0f} | {ts['mar']} | "
                         f"{bs['ret']:+.0f} | {bs['mar']} | {'✅' if beat else '—'} |")
        lines.append("")

    lines.append("A single favourable window is luck; an edge that survives most windows across "
                 "different regimes is real. MAR = return / |max drawdown|.")
    return "\n".join(lines)


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
