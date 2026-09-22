"""
Experiment #21 — "momentum, done properly".

Exp #20 found that plain 12-1 cross-sectional momentum was the single most
promising signal in the whole project (the only positive Sharpe, cost-robust,
positive in 2/3 regimes) yet still not statistically significant. The academic
literature says exactly *why* raw momentum underperforms its potential, and how to
fix it. This experiment tests the six best-documented refinements of that one lead,
all long/short (or long-only), monthly, at a realistic 5 bps, through full rigor:

  1. Raw 12-1                 — baseline, for comparison.
  2. Volatility-scaled        — rank by return/vol (risk-adjusted), not raw return.
  3. Residual (idiosyncratic) — momentum of the market-beta-adjusted residual
                                 (Blitz-Huij-Martens: more stable, less crash-prone).
  4. Volatility-managed       — raw signal, but exposure scaled by inverse recent
                                 strategy volatility (Barroso-Santa-Clara 2015).
  5. Regime-filtered          — hold only when the equal-weight index is above its
                                 200d average, else flat (avoids momentum crashes).
  6. Long-only top decile     — retail-tradeable variant with no shorting.

Same honesty caveat as #20: today's large caps → survivorship bias inflates results.
Pure numpy/pandas, fully causal. Reuses the #20 portfolio engine.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor, rigor_row, RIGOR_HEADER
from .experiments_20 import build_price_panel, long_short_returns


# ---- score functions -------------------------------------------------------

def score_momentum(panel_slice: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.Series:
    """Raw 12-1 momentum: return over `lookback` days, skipping the recent `skip`."""
    if len(panel_slice) <= lookback + 1:
        return pd.Series(np.nan, index=panel_slice.columns)
    return panel_slice.iloc[-1 - skip] / panel_slice.iloc[-1 - lookback] - 1.0


def score_volscaled_momentum(panel_slice: pd.DataFrame, lookback: int = 252,
                             skip: int = 21) -> pd.Series:
    """12-1 return divided by daily-return volatility over the formation window
    (risk-adjusted momentum — favours steady trends over volatile ones)."""
    if len(panel_slice) <= lookback + 1:
        return pd.Series(np.nan, index=panel_slice.columns)
    raw = panel_slice.iloc[-1 - skip] / panel_slice.iloc[-1 - lookback] - 1.0
    rets = panel_slice.pct_change().iloc[-lookback:-skip]
    vol = rets.std().replace(0.0, np.nan)
    return raw / vol


def score_residual_momentum(panel_slice: pd.DataFrame, lookback: int = 252,
                            skip: int = 21) -> pd.Series:
    """Idiosyncratic momentum (Blitz-Huij-Martens): over the formation window,
    regress each stock's daily return on the equal-weight market return, then score
    by mean(residual)/std(residual). Removes the market component that drives
    momentum crashes; historically more stable than raw momentum."""
    if len(panel_slice) <= lookback + 1:
        return pd.Series(np.nan, index=panel_slice.columns)
    rets = panel_slice.pct_change().iloc[-lookback:-skip]
    if len(rets) < 40:
        return pd.Series(np.nan, index=panel_slice.columns)
    mkt = rets.mean(axis=1)
    mkt_var = float(mkt.var())
    if mkt_var == 0 or not np.isfinite(mkt_var):
        return pd.Series(np.nan, index=panel_slice.columns)
    mkt_c = mkt - mkt.mean()
    out = {}
    for col in rets.columns:
        r = rets[col]
        if r.isna().mean() > 0.2:
            out[col] = np.nan
            continue
        r = r.fillna(0.0)
        beta = float(((r - r.mean()) * mkt_c).sum() / (mkt_c.pow(2).sum()))
        resid = r - beta * mkt
        sd = float(resid.std())
        out[col] = float(resid.mean() / sd) if sd > 0 else np.nan
    return pd.Series(out).reindex(panel_slice.columns)


# ---- return-series overlays (post-processing, fully causal) ----------------

def vol_managed(returns: pd.Series, target_ann: float = 0.10, window: int = 126,
                max_leverage: float = 3.0) -> pd.Series:
    """Barroso-Santa-Clara volatility management: scale each day's return by
    target_vol / trailing realised vol (lagged one day, so causal), capped at
    `max_leverage`. Stabilises the payoff and tames momentum crashes."""
    r = returns.copy()
    daily_target = target_ann / np.sqrt(252)
    realized = r.rolling(window).std().shift(1)
    lev = (daily_target / realized).clip(upper=max_leverage)
    lev = lev.fillna(0.0)
    return r * lev


def regime_filtered(returns: pd.Series, index_level: pd.Series, ma: int = 200) -> pd.Series:
    """Hold the strategy only on days the market index closed above its `ma`-day
    average on the PRIOR day (causal); otherwise flat. Avoids the bear-market
    reversals where momentum crashes."""
    sma = index_level.rolling(ma).mean()
    on = (index_level > sma).shift(1).reindex(returns.index).fillna(False)
    return returns.where(on, 0.0)


def _equal_weight_index(panel: pd.DataFrame) -> pd.Series:
    """Equal-weight price index of the universe (for the regime filter)."""
    daily = panel.pct_change().mean(axis=1).fillna(0.0)
    return (1.0 + daily).cumprod()


# ---- report ----------------------------------------------------------------

def run_experiment21_report(get_ohlcv: Callable[[str, str, int], pd.DataFrame],
                            universe: list[str], n_trials: int = 66,
                            limit: int = 2500, cost_bps: float = 5.0) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #21 — momentum, done properly "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    panel = build_price_panel(get_ohlcv, universe, limit=limit)
    if panel.empty or panel.shape[1] < 20:
        lines.append(f"Insufficient data: only {0 if panel.empty else panel.shape[1]} "
                     f"symbols with enough history (need ≥20).")
        return "\n".join(lines)

    n_names = panel.shape[1]
    span = f"{panel.index[0]:%Y-%m-%d} → {panel.index[-1]:%Y-%m-%d}"
    lines.append(f"Universe: {n_names} stocks. Span: {span} ({len(panel)} days). "
                 f"All monthly rebalanced, {cost_bps:.0f} bps costs, decile long/short "
                 f"(unless noted). Multiple-testing haircut α/{n_trials}.")
    lines.append("")
    lines.append("> ⚠️ Survivorship bias (today's large caps) inflates results — a "
                 "failure here is a firm negative; a marginal winner is discounted.")
    lines.append("")

    idx_level = _equal_weight_index(panel)
    raw = long_short_returns(panel, lambda ps: score_momentum(ps), "M", cost_bps=cost_bps)

    variants: dict[str, pd.Series] = {
        "1. Raw 12-1 (baseline)": raw,
        "2. Vol-scaled ranking":
            long_short_returns(panel, lambda ps: score_volscaled_momentum(ps), "M", cost_bps=cost_bps),
        "3. Residual (idiosyncratic)":
            long_short_returns(panel, lambda ps: score_residual_momentum(ps), "M", cost_bps=cost_bps),
        "4. Vol-managed (Barroso)": vol_managed(raw),
        "5. Regime-filtered (>200d)": regime_filtered(raw, idx_level),
        "6. Long-only top decile":
            long_short_returns(panel, lambda ps: score_momentum(ps), "M",
                               cost_bps=cost_bps, long_only=True),
    }

    lines.append(RIGOR_HEADER)
    all_results = []
    for name, r in variants.items():
        try:
            res = full_rigor(name, r, n_trials)
        except Exception as e:
            logger.warning(f"Exp21 {name} failed: {e}")
            res = {"name": name, "verdict": "insufficient data"}
        all_results.append(res)
        lines.append(rigor_row(res))
    lines.append("")

    survivors = [r for r in all_results if r.get("verdict", "").startswith("✅")]
    marginal = [r for r in all_results if r.get("verdict", "").startswith("⚠")]
    # best by Sharpe among those with numbers
    scored = [r for r in all_results if "sharpe" in r]
    best = max(scored, key=lambda r: r["sharpe"]) if scored else None
    lines.append("---")
    lines.append(
        f"**Summary:** 6 momentum refinements on {n_names} stocks. "
        f"Survive full rigor: {len(survivors)} "
        f"({', '.join(r['name'] for r in survivors) if survivors else 'none'}); "
        f"marginal: {len(marginal)} "
        f"({', '.join(r['name'] for r in marginal) if marginal else 'none'})."
        + (f" Best Sharpe: {best['name']} = {best['sharpe']} (p={best['p_value']})."
           if best else ""))
    return "\n".join(lines)
