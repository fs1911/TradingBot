"""
Experiment #20 — cross-sectional long/short over MANY individual stocks.

Every earlier experiment *timed* a single instrument (buy/sell SPY, GLD, BTC …).
This is a fundamentally different design: a market-neutral PORTFOLIO that, at each
rebalance, ranks a wide universe of individual stocks and goes long the top decile
and short the bottom decile. This is where the best-documented real anomalies live:

  1. Short-term reversal  — long last week's losers, short last week's winners.
  2. Cross-sectional momentum (12-1) — long the 12-month winners (skipping the last
     month), short the losers, rebalanced monthly.

Daily, dollar-neutral (long +1 / short -1), equal-weight within each leg. Costs are
charged on realised turnover and swept across levels, because reversal in particular
trades a lot and costs are the usual killer. Each portfolio's daily return series is
run through the full rigor battery.

Important honesty note: the universe is *today's* large caps, so the test carries
SURVIVORSHIP BIAS, which INFLATES results. A strategy that fails even on this
favourable, biased universe is a strong negative; a marginal winner must be
discounted for the bias. Pure numpy/pandas, fully causal.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor, rigor_row, RIGOR_HEADER


def build_price_panel(get_ohlcv: Callable[[str, str, int], pd.DataFrame],
                      symbols: list[str], limit: int = 2500,
                      min_len: int = 500, min_coverage: float = 0.8) -> pd.DataFrame:
    """Assemble a (dates x symbols) close-price panel, indexed by calendar date."""
    cols: dict[str, pd.Series] = {}
    for s in symbols:
        try:
            df = get_ohlcv(s, "1Day", limit)
        except Exception as e:
            logger.warning(f"Exp20: fetch {s} failed: {e}")
            continue
        if df is None or len(df) < min_len:
            continue
        c = df["close"].copy()
        c.index = pd.to_datetime(c.index).tz_localize(None).normalize()
        c = c[~c.index.duplicated(keep="last")]
        cols[s] = c
    if len(cols) < 20:
        return pd.DataFrame()
    panel = pd.DataFrame(cols).sort_index()
    # keep symbols present for at least `min_coverage` of the timeline
    panel = panel.dropna(axis=1, thresh=int(min_coverage * len(panel)))
    panel = panel.ffill(limit=3)
    return panel


def _decile_weights(score: pd.Series, top: float, bottom: float,
                    long_only: bool = False) -> pd.Series:
    """Equal weights: long the top-`top` fraction of `score`. If `long_only` is
    False, also short the bottom-`bottom` fraction (dollar-neutral: long leg +1,
    short leg -1). If True, only the long leg is held (sums to +1, no shorts)."""
    w = pd.Series(0.0, index=score.index)
    s = score.dropna()
    if len(s) < 10:
        return w
    n = len(s)
    k_top = max(1, int(round(n * top)))
    order = s.sort_values()
    longs = order.index[-k_top:]
    w[longs] = 1.0 / len(longs)
    if not long_only:
        k_bot = max(1, int(round(n * bottom)))
        shorts = order.index[:k_bot]
        w[shorts] = -1.0 / len(shorts)
    return w


def _rebalance_dates(dates: pd.DatetimeIndex, freq: str) -> set:
    """freq: 'D' every day, 'W' ISO-week end, 'M' month-end, 'Q' quarter-end."""
    if freq == "D":
        return set(dates)
    idx = pd.Series(dates, index=dates)
    if freq == "W":
        key = idx.index.to_period("W")
    elif freq == "Q":
        key = idx.index.to_period("Q")
    else:  # 'M'
        key = idx.index.to_period("M")
    last = idx.groupby(key).max()
    return set(pd.DatetimeIndex(last.values))


def long_short_returns(panel: pd.DataFrame, score_fn: Callable[[pd.DataFrame], pd.Series],
                       rebalance: str = "M", top: float = 0.1, bottom: float = 0.1,
                       cost_bps: float = 5.0, long_only: bool = False) -> pd.Series:
    """Backtest a decile long/short portfolio (dollar-neutral, or long-only if
    `long_only`). `score_fn(panel_slice)` returns a per-symbol attractiveness score
    using data up to and including the rebalance day (long high score, short low
    score). Weights set at a rebalance close start earning the NEXT day; costs are
    charged on realised turnover. Returns a daily return series."""
    rets = panel.pct_change()
    dates = panel.index
    rb = _rebalance_dates(dates, rebalance)
    current = pd.Series(0.0, index=panel.columns)
    out = pd.Series(0.0, index=dates)
    for i in range(1, len(dates)):
        # today's P&L from weights held since the previous rebalance
        day_ret = float((current * rets.iloc[i].fillna(0.0)).sum())
        cost = 0.0
        if dates[i] in rb:
            score = score_fn(panel.iloc[: i + 1])          # causal: through today
            new_w = _decile_weights(score.reindex(panel.columns), top, bottom, long_only)
            turnover = float((new_w - current).abs().sum())  # one-way units traded
            cost = turnover * cost_bps / 1e4
            current = new_w
        out.iloc[i] = day_ret - cost
    return out


# ---- signal functions ------------------------------------------------------

def score_reversal(panel_slice: pd.DataFrame, lookback: int = 5) -> pd.Series:
    """Short-term reversal: attractive = negative of the recent return (buy losers)."""
    if len(panel_slice) <= lookback:
        return pd.Series(np.nan, index=panel_slice.columns)
    past = panel_slice.iloc[-1] / panel_slice.iloc[-1 - lookback] - 1.0
    return -past


def score_momentum(panel_slice: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.Series:
    """12-1 momentum: return over `lookback` days, skipping the most recent `skip`."""
    if len(panel_slice) <= lookback + 1:
        return pd.Series(np.nan, index=panel_slice.columns)
    p_now = panel_slice.iloc[-1 - skip]
    p_then = panel_slice.iloc[-1 - lookback]
    return p_now / p_then - 1.0


# ---- report ----------------------------------------------------------------

def run_experiment20_report(get_ohlcv: Callable[[str, str, int], pd.DataFrame],
                            universe: list[str], n_trials: int = 60,
                            limit: int = 2500,
                            cost_levels_bps: tuple = (1.0, 5.0, 10.0)) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #20 — cross-sectional long/short over individual stocks "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    panel = build_price_panel(get_ohlcv, universe, limit=limit)
    if panel.empty or panel.shape[1] < 20:
        lines.append(f"Insufficient data: only {0 if panel.empty else panel.shape[1]} "
                     f"symbols with enough history (need ≥20). Universe requested: "
                     f"{len(universe)}.")
        return "\n".join(lines)

    n_names = panel.shape[1]
    span = f"{panel.index[0]:%Y-%m-%d} → {panel.index[-1]:%Y-%m-%d}"
    lines.append(f"Universe: {n_names} stocks with ≥2y history. Span: {span} "
                 f"({len(panel)} trading days). Dollar-neutral, decile long/short, "
                 f"equal weight. Multiple-testing haircut α/{n_trials}.")
    lines.append("")
    lines.append("> ⚠️ Survivorship bias: the universe is *today's* large caps, which "
                 "INFLATES back-tested returns. A strategy that fails even here is a "
                 "firm negative; a marginal winner must be discounted for the bias.")
    lines.append("")

    strategies = {
        "Short-term reversal (5d, daily rebal)":
            (lambda ps: score_reversal(ps, lookback=5), "D"),
        "Cross-sectional momentum (12-1, monthly rebal)":
            (lambda ps: score_momentum(ps, lookback=252, skip=21), "M"),
    }

    all_results = []
    for name, (fn, freq) in strategies.items():
        lines.append(f"## {name}")
        lines.append(RIGOR_HEADER)
        for cost in cost_levels_bps:
            try:
                r = long_short_returns(panel, fn, rebalance=freq, cost_bps=cost)
                res = full_rigor(f"{name} @ {cost:.0f}bps", r, n_trials)
            except Exception as e:
                logger.warning(f"Exp20 {name} @ {cost}bps failed: {e}")
                res = {"name": f"{name} @ {cost:.0f}bps", "verdict": "insufficient data"}
            all_results.append(res)
            lines.append(rigor_row(res))
        lines.append("")

    survivors = [r for r in all_results if r.get("verdict", "").startswith("✅")]
    marginal = [r for r in all_results if r.get("verdict", "").startswith("⚠")]
    lines.append("---")
    lines.append(
        f"**Summary:** {len(all_results)} portfolio configs tested on {n_names} stocks. "
        f"Survive full rigor: {len(survivors)} "
        f"({', '.join(r['name'] for r in survivors) if survivors else 'none'}); "
        f"marginal: {len(marginal)} "
        f"({', '.join(r['name'] for r in marginal) if marginal else 'none'}). "
        f"Note the survivorship bias above — real, tradeable results would be weaker.")
    return "\n".join(lines)
