"""
Experiment #17 — regime-conditional mean reversion.

Experiments #12/#13/#15 all found the SAME real-but-weak effect: short-term
mean-reversion (RSI(2)) in equity indices. The literature says this reversal is
strongest in HIGH-volatility regimes (panic/overreaction) and weak-to-absent in
calm trends. So instead of testing a new signal, we condition the KNOWN one:
apply RSI(2) only when volatility is elevated. If conditioning lifts it over the
strict bar, we would have — for the first time — a robust, motivated edge. If not,
the effect is genuinely too weak even where it should be strongest.

Causal throughout (vol regime uses only past data). Full rigor battery.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor
from .experiments_12 import _rsi, _norm


def regime_rsi2_returns(df, oversold=10.0, exit_sma=5, regime="high",
                        vol_lookback=20, median_window=252,
                        commission_pct=0.05, slippage_pct=0.03):
    """RSI(2) long/flat, but only allowed to ENTER when the volatility regime
    matches: 'high' = realized vol above its trailing median, 'low' = below,
    'all' = no gate. Regime threshold uses only past data (causal)."""
    c = _norm(df["close"])
    arr = c.to_numpy()
    r = c.pct_change().fillna(0)
    rsi = _rsi(arr, 2)
    sma_exit = c.rolling(exit_sma).mean().to_numpy()
    vol = r.rolling(vol_lookback).std()
    thresh = vol.rolling(median_window).median().shift(1)
    if regime == "high":
        regime_ok = (vol > thresh)
    elif regime == "low":
        regime_ok = (vol < thresh)
    else:
        regime_ok = pd.Series(True, index=c.index)
    regime_ok = regime_ok.fillna(False).to_numpy()

    pos = np.zeros(len(c))
    cur = 0
    for i in range(len(c)):
        if np.isnan(rsi[i]) or np.isnan(sma_exit[i]):
            pos[i] = 0; continue
        if cur == 0:
            if regime_ok[i] and rsi[i] < oversold:
                cur = 1
        elif arr[i] > sma_exit[i]:
            cur = 0
        pos[i] = cur
    pos_s = pd.Series(pos, index=c.index).shift(1).fillna(0)
    cost = (commission_pct + slippage_pct) / 100
    turn = pos_s.diff().abs().fillna(pos_s.abs())
    return (pos_s * r - turn * cost).rename("ret")


def run_experiment17_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    symbols: list[str],
    n_trials: int = 45,
    limit: int = 2500,
) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #17 — regime-conditional RSI(2) mean reversion "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"Apply the known RSI(2) reversal only in a volatility regime (high vs low), where "
                 f"theory says reversal is strongest. Can conditioning rescue the real-but-weak "
                 f"effect? Full rigor battery, multiple-testing haircut α/{n_trials}.")
    lines.append("")
    lines.append("| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |")
    lines.append("|---|--:|--:|--:|--:|:--:|:--:|:--:|---|")

    results = []
    for sym in symbols:
        df = get_ohlcv(sym, "1Day", limit)
        if df is None or len(df) < 600:
            lines.append(f"| {sym} | insufficient data |||||||")
            continue
        for regime in ("high", "low"):
            res = full_rigor(f"RSI2-{regime}vol {sym}",
                             regime_rsi2_returns(df, regime=regime), n_trials)
            results.append(res)
            lines.append(f"| {res['name']} | {res['oos_ret']:+.0f} | {res['sharpe']} | {res['t_stat']} | "
                         f"{res['p_value']} | {'yes' if res['sig_after_haircut'] else 'no'} | "
                         f"{res['wf_pct']}% | {res['regime_positive']} | {res['verdict']} |")

    lines.append("")
    survivors = [r for r in results if r.get("verdict", "").startswith("✅")]
    hi = [r for r in results if "highvol" in r["name"] and r.get("oos_ret", 0) > 0]
    lines.append(f"**Summary:** {len(survivors)}/{len(results)} survive the full battery. "
                 + (", ".join(r["name"] for r in survivors) if survivors else
                    "None — conditioning on the high-vol regime does not lift the mean-reversion "
                    "effect over the strict bar. The effect is real but genuinely too weak to trade."))
    return "\n".join(lines)
