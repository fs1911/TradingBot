"""
Cross-sectional momentum edge test — the last genuinely untested hypothesis with
strong academic support (Jegadeesh & Titman 1993; also documented in crypto).

Unlike trend-following ("is THIS asset trending?"), cross-sectional momentum asks
"which assets are strongest RELATIVE to the others?": each month, rank the whole
universe by trailing 12-1 return, hold the top fraction equal-weighted, rebalance.
The honest benchmark is equal-weight buy-and-hold of the SAME universe — does
picking the winners beat just holding everything? Tested OOS and walk-forward.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .trend_follow import _curve_stats
from .oos_runner import split_is_oos


def _price_panel(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Align per-symbol daily closes into one panel over the window where ALL
    symbols have data (no look-ahead survivorship within the window).

    Timestamps are normalised to the calendar date first: crypto bars are stamped
    00:00 UTC while stock/ETF bars carry a market-hours time, so without this the
    index intersection of a mixed basket (e.g. BTC + GLD) is empty."""
    cols = {}
    for s, d in data.items():
        ser = d["close"].sort_index()
        ser.index = ser.index.normalize()          # drop time-of-day → align calendars
        ser = ser[~ser.index.duplicated(keep="last")]
        cols[s] = ser
    panel = pd.concat(cols, axis=1)
    panel.columns = list(cols.keys())
    return panel.dropna()


def xsec_momentum_returns(prices: pd.DataFrame, *, lookback: int = 252, skip: int = 21,
                          hold: int = 21, top_frac: float = 0.3,
                          commission_pct: float = 0.05, slippage_pct: float = 0.03) -> pd.Series:
    """Daily net returns of a long-only cross-sectional momentum portfolio.

    Every `hold` days, score each asset by its return from t-lookback to t-skip
    (12-1 momentum, skipping the most recent month to avoid short-term reversal),
    go equal-weight long the top `top_frac` of the universe, hold `hold` days.
    Turnover is charged commission+slippage on each rebalance."""
    n_days, n_assets = prices.shape
    if n_days < lookback + skip + hold + 5 or n_assets < 4:
        return pd.Series(dtype=float)
    asset_ret = prices.pct_change().fillna(0).to_numpy()
    px = prices.to_numpy()
    k = max(1, int(round(top_frac * n_assets)))
    cost = (commission_pct + slippage_pct) / 100

    weights = np.zeros(n_assets)
    strat = np.zeros(n_days)
    start = lookback + skip
    for i in range(n_days):
        if i >= start and (i - start) % hold == 0:               # rebalance day
            score = px[i - skip] / px[i - lookback] - 1
            order = np.argsort(score)[::-1]
            new_w = np.zeros(n_assets)
            new_w[order[:k]] = 1.0 / k
            strat[i] -= np.abs(new_w - weights).sum() * cost      # turnover cost
            weights = new_w
        strat[i] += float((weights * asset_ret[i]).sum())
    return pd.Series(strat, index=prices.index)


def _segment_stats(prices: pd.DataFrame, **params) -> tuple[dict, dict]:
    """Return (_curve_stats momentum, _curve_stats equal-weight-hold) on a panel."""
    mom = xsec_momentum_returns(prices, **params)
    ew = prices.pct_change().fillna(0).mean(axis=1)
    return _curve_stats(mom), _curve_stats(ew)


def run_xsec_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    universes: dict[str, list[str]],
    limit: int = 2000,
    min_symbols: int = 8,
    window: int = 252,
    step: int = 63,
    commission_pct: float = 0.05,
    slippage_pct: float = 0.03,
) -> str:
    """Per asset class with enough names: cross-sectional momentum vs equal-weight
    Buy&Hold — OOS split plus a walk-forward across rolling windows. A real edge
    beats holding on MAR out-of-sample AND in most walk-forward windows."""
    from datetime import datetime, timezone

    params = dict(commission_pct=commission_pct, slippage_pct=slippage_pct)
    lines = [f"# Cross-Sectional Momentum Edge Test — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    lines.append("Monthly rank by 12-1 return, hold the top 30% equal-weight vs equal-weight "
                 "Buy&Hold of the same universe. Net of costs. MAR = return/|maxDD|. "
                 "A real edge beats hold OOS and in most walk-forward windows.")
    lines.append("")

    for group, syms in universes.items():
        if len(syms) < min_symbols:
            continue
        data: dict[str, pd.DataFrame] = {}
        for sym in syms:
            try:
                d = get_ohlcv(sym, "1Day", limit)
                if d is not None and len(d) >= 400:
                    data[sym] = d
            except Exception as e:
                logger.warning(f"XSec: could not fetch {sym}: {e}")
        if len(data) < min_symbols:
            lines.append(f"## {group.upper()}\n_only {len(data)} symbols with data — skipped_\n")
            continue

        panel = _price_panel(data)
        lines.append(f"## {group.upper()}")
        lines.append(f"{panel.shape[1]} symbols · common window {panel.index[0]:%Y-%m} → "
                     f"{panel.index[-1]:%Y-%m} ({len(panel)} days)")
        lines.append("")

        # OOS split
        is_p, oos_p = split_is_oos(panel)
        (im, ih) = _segment_stats(is_p, **params)
        (om, oh) = _segment_stats(oos_p, **params)
        lines.append("| Segment | Mom ret% | Mom MAR | Hold ret% | Hold MAR | Mom wins? |")
        lines.append("|---|--:|--:|--:|--:|:--:|")
        for label, m, h in [("In-Sample", im, ih), ("Out-of-Sample", om, oh)]:
            win = "✅" if (m["mar"] > h["mar"] and m["ret"] > 0) else "—"
            lines.append(f"| {label} | {m['ret']:+.0f} | {m['mar']} | {h['ret']:+.0f} | {h['mar']} | {win} |")
        lines.append("")

        # Walk-forward
        mom = xsec_momentum_returns(panel, **params)
        ew = panel.pct_change().fillna(0).mean(axis=1)
        common = mom.index.intersection(ew.index)
        mom, ew = mom.loc[common], ew.loc[common]
        rows, i = [], 0
        while i + window <= len(common):
            ms = _curve_stats(mom.iloc[i:i + window])
            hs = _curve_stats(ew.iloc[i:i + window])
            beat = ms["mar"] > hs["mar"] and ms["ret"] > 0
            rows.append(beat)
            i += step
        if rows:
            nb, n = sum(rows), len(rows)
            pct = round(100 * nb / n)
            if pct >= 60:
                verdict = "✅ robust edge (beats hold in most windows)"
            elif pct >= 40:
                verdict = "⚠️ regime-dependent"
            else:
                verdict = "❌ not robust"
            lines.append(f"**Walk-forward:** momentum beat equal-weight hold in "
                         f"**{nb}/{n} windows ({pct}%)** → {verdict}")
        lines.append("")

    lines.append("If cross-sectional momentum doesn't beat equal-weight holding on MAR "
                 "out-of-sample and across windows, the profit was just market beta.")
    return "\n".join(lines)
