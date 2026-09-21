"""
Experiment #16 — two further genuinely-new categories:

  A) Volume-based signals (we have never used volume as a primary signal):
     - volume_capitulation: buy the index the day AFTER a high-volume down day
       (climax/capitulation → short-term bounce)
     - obv_trend: On-Balance-Volume trend filter — long only when OBV is rising
  B) Stocks-vs-bonds dual momentum (Antonacci GEM-style): hold whichever of SPY /
     TLT has the higher 6-month momentum, but only if it beats cash (else flat).

All causal, net of costs, judged by the full rigor battery.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor
from .xsec_momentum import _price_panel


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_index().copy()
    df.index = df.index.normalize()
    return df


def volume_capitulation_returns(df, vol_mult=1.8, lookback=20,
                                commission_pct=0.05, slippage_pct=0.03):
    """Long the next day after a down day whose volume was >= vol_mult × its
    trailing average (capitulation bounce). Causal."""
    d = _norm(df)
    r = d["close"].pct_change().fillna(0)
    vol = d["volume"]
    avg = vol.rolling(lookback).mean()
    spike = (vol >= vol_mult * avg) & (r < 0)
    pos = spike.astype(float).shift(1).fillna(0)     # act the day after the capitulation
    cost = (commission_pct + slippage_pct) / 100
    turn = pos.diff().abs().fillna(pos.abs())
    return (pos * r - turn * cost).rename("ret")


def obv_trend_returns(df, ma=20, commission_pct=0.05, slippage_pct=0.03):
    """Long only when On-Balance Volume is above its own moving average (volume
    confirms the uptrend). Causal."""
    d = _norm(df)
    r = d["close"].pct_change().fillna(0)
    sign = np.sign(d["close"].diff().fillna(0))
    obv = (sign * d["volume"]).cumsum()
    pos = (obv > obv.rolling(ma).mean()).astype(float).shift(1).fillna(0)
    cost = (commission_pct + slippage_pct) / 100
    turn = pos.diff().abs().fillna(pos.abs())
    return (pos * r - turn * cost).rename("ret")


def dual_momentum_returns(data: dict[str, pd.DataFrame], risk="SPY", bond="TLT",
                          lookback=126, commission_pct=0.05, slippage_pct=0.03):
    """GEM-style: each month hold SPY or TLT by 6-month momentum, only if positive
    (else flat/cash). Market-timing allocation. Causal."""
    if risk not in data or bond not in data:
        return pd.Series(dtype=float)
    panel = _price_panel({risk: data[risk], bond: data[bond]})
    if len(panel) < lookback + 40:
        return pd.Series(dtype=float)
    mom = panel / panel.shift(lookback) - 1
    rets = panel.pct_change().fillna(0)
    cost = (commission_pct + slippage_pct) / 100
    pos = pd.Series(0.0, index=panel.index)          # 0=cash, else weight in chosen col
    choice = np.zeros(len(panel), dtype=int)         # 0 cash, 1 risk, 2 bond
    cols = list(panel.columns)
    ri, bi = cols.index(risk), cols.index(bond)
    mv = mom.to_numpy()
    hold = 21
    cur = 0
    start = lookback
    for i in range(len(panel)):
        if i >= start and (i - start) % hold == 0 and not np.any(np.isnan(mv[i])):
            mr, mb = mv[i][ri], mv[i][bi]
            if mr <= 0 and mb <= 0:
                cur = 0
            elif mr >= mb:
                cur = 1
            else:
                cur = 2
        choice[i] = cur
    choice_s = pd.Series(choice, index=panel.index).shift(1).fillna(0).astype(int)
    rv = rets.to_numpy()
    strat = np.zeros(len(panel))
    for i in range(len(panel)):
        c = choice_s.iat[i]
        if c == 1:
            strat[i] = rv[i][ri]
        elif c == 2:
            strat[i] = rv[i][bi]
    turn = choice_s.ne(choice_s.shift(1)).astype(float).fillna(0)
    return (pd.Series(strat, index=panel.index) - turn * cost).rename("ret")


def run_experiment16_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    volume_symbols: list[str],
    dual_momentum: dict | None,
    n_trials: int = 40,
    limit: int = 2500,
) -> str:
    from datetime import datetime, timezone

    cache: dict[str, pd.DataFrame] = {}
    def _get(s):
        if s not in cache:
            try:
                cache[s] = get_ohlcv(s, "1Day", limit)
            except Exception as e:
                logger.warning(f"Exp16: fetch {s} failed: {e}")
                cache[s] = pd.DataFrame()
        return cache[s]
    def _ok(df):
        return df is not None and len(df) >= 500

    lines = [f"# Experiment #16 — volume signals + stocks/bonds dual momentum "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"New categories: volume as a primary signal, and a defensive stocks-vs-bonds "
                 f"allocation. Full rigor battery, multiple-testing haircut α/{n_trials}.")
    lines.append("")
    lines.append("| Strategy | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |")
    lines.append("|---|--:|--:|--:|--:|:--:|:--:|:--:|---|")

    results = []
    for sym in volume_symbols:
        df = _get(sym)
        if not _ok(df):
            continue
        for label, fn in [("VolCapitulation", volume_capitulation_returns),
                          ("OBVtrend", obv_trend_returns)]:
            res = full_rigor(f"{label} {sym}", fn(df), n_trials)
            results.append(res)
            lines.append(f"| {res['name']} | {res['oos_ret']:+.0f} | {res['sharpe']} | {res['t_stat']} | "
                         f"{res['p_value']} | {'yes' if res['sig_after_haircut'] else 'no'} | "
                         f"{res['wf_pct']}% | {res['regime_positive']} | {res['verdict']} |")

    if dual_momentum:
        risk, bond = dual_momentum.get("risk", "SPY"), dual_momentum.get("bond", "TLT")
        data = {risk: _get(risk), bond: _get(bond)}
        if _ok(data[risk]) and _ok(data[bond]):
            r = dual_momentum_returns(data, risk=risk, bond=bond)
            res = full_rigor(f"DualMom {risk}/{bond}", r, n_trials)
            results.append(res)
            lines.append(f"| {res['name']} | {res['oos_ret']:+.0f} | {res['sharpe']} | {res['t_stat']} | "
                         f"{res['p_value']} | {'yes' if res['sig_after_haircut'] else 'no'} | "
                         f"{res['wf_pct']}% | {res['regime_positive']} | {res['verdict']} |")

    lines.append("")
    survivors = [r for r in results if r.get("verdict", "").startswith("✅")]
    lines.append(f"**Summary:** {len(survivors)}/{len(results)} survive the full battery. "
                 + (", ".join(r["name"] for r in survivors) if survivors else
                    "None — volume and allocation signals add no robust edge either."))
    return "\n".join(lines)
