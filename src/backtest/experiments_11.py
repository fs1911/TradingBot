"""
Experiment #11 — a batch of economically-grounded hypotheses, each run through the
stronger rigor battery (src/backtest/rigor.py): significance p-value with a
multiple-testing haircut, regime stability, Sharpe/t-stat, walk-forward.

All strategies are strictly causal (only past data decides today's position):
  - seasonality:   long in calendar months that were positive in ALL prior years
  - lead_lag:      long a target the day after a "leader" asset rose
  - term_structure: hold short-vol (SVXY) only when the VIX curve is in contango
                    (mid-term VIXM above short-term VXX) — a real roll-yield signal
  - weekday:       long only on weekdays that were historically positive (crypto)
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor, rigor_row, RIGOR_HEADER


def _norm(df: pd.DataFrame) -> pd.Series:
    s = df["close"].sort_index()
    s.index = s.index.normalize()
    return s


def seasonality_returns(df: pd.DataFrame, commission_pct=0.05, slippage_pct=0.08) -> pd.Series:
    c = _norm(df)
    r = c.pct_change().fillna(0)
    d = pd.DataFrame({"r": r.values, "m": c.index.month, "y": c.index.year}, index=c.index)
    pos = np.zeros(len(c))
    for i in range(len(c)):
        m, y = d["m"].iat[i], d["y"].iat[i]
        prior = d["r"][(d["m"] == m) & (d["y"] < y)]
        if len(prior) >= 15 and prior.mean() > 0:
            pos[i] = 1.0
    pos_s = pd.Series(pos, index=c.index).shift(1).fillna(0)
    cost = (commission_pct + slippage_pct) / 100
    turn = pos_s.diff().abs().fillna(pos_s.abs())
    return (pos_s * r - turn * cost).rename("ret")


def lead_lag_returns(leader: pd.DataFrame, target: pd.DataFrame,
                     commission_pct=0.05, slippage_pct=0.08) -> pd.Series:
    df = pd.concat({"L": _norm(leader), "T": _norm(target)}, axis=1).dropna()
    if len(df) < 60:
        return pd.Series(dtype=float)
    rl = df["L"].pct_change().fillna(0)
    rt = df["T"].pct_change().fillna(0)
    pos = (rl > 0).astype(float).shift(1).fillna(0)      # leader up yesterday -> long target today
    cost = (commission_pct + slippage_pct) / 100
    turn = pos.diff().abs().fillna(pos.abs())
    return (pos * rt - turn * cost).rename("ret")


def term_structure_returns(front: pd.DataFrame, back: pd.DataFrame, trade: pd.DataFrame,
                           commission_pct=0.05, slippage_pct=0.08) -> pd.Series:
    """Hold `trade` (short-vol ETF) only when the vol curve is in contango: mid-term
    (back, e.g. VIXM) above short-term (front, e.g. VXX). Causal."""
    df = pd.concat({"f": _norm(front), "b": _norm(back), "t": _norm(trade)}, axis=1).dropna()
    if len(df) < 60:
        return pd.Series(dtype=float)
    contango = (df["b"] > df["f"]).astype(float)
    pos = contango.shift(1).fillna(0)
    rt = df["t"].pct_change().fillna(0)
    cost = (commission_pct + slippage_pct) / 100
    turn = pos.diff().abs().fillna(pos.abs())
    return (pos * rt - turn * cost).rename("ret")


def weekday_returns(df: pd.DataFrame, commission_pct=0.05, slippage_pct=0.08) -> pd.Series:
    c = _norm(df)
    r = c.pct_change().fillna(0)
    wd = c.index.dayofweek
    pos = np.zeros(len(c))
    rv = r.values
    for i in range(len(c)):
        if i < 60:
            continue
        mask = wd[:i] == wd[i]
        prior = rv[:i][mask]
        if len(prior) >= 30 and prior.mean() > 0:
            pos[i] = 1.0
    pos_s = pd.Series(pos, index=c.index).shift(1).fillna(0)
    cost = (commission_pct + slippage_pct) / 100
    turn = pos_s.diff().abs().fillna(pos_s.abs())
    return (pos_s * r - turn * cost).rename("ret")


def run_experiment11_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    seasonality_symbols: list[str],
    lead_lag_pairs: list[tuple[str, str]],
    term_structure: dict | None,
    weekday_symbols: list[str],
    n_trials: int = 20,
    limit: int = 2500,
) -> str:
    from datetime import datetime, timezone

    cache: dict[str, pd.DataFrame] = {}
    def _get(sym):
        if sym not in cache:
            try:
                cache[sym] = get_ohlcv(sym, "1Day", limit)
            except Exception as e:
                logger.warning(f"Exp11: fetch {sym} failed: {e}")
                cache[sym] = pd.DataFrame()
        return cache[sym]
    def _ok(df):
        return df is not None and len(df) >= 400

    lines = [f"# Experiment #11 — batch of hypotheses under the STRONG rigor battery "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"Each strategy is causal and judged by: OOS return, Sharpe, t-stat, a "
                 f"block-bootstrap p-value with a multiple-testing haircut (α/{n_trials}), "
                 f"walk-forward, and regime stability (all 3 thirds positive). Realistic costs.")
    lines.append("")
    lines.append(RIGOR_HEADER)

    results: list[dict] = []

    for sym in seasonality_symbols:
        df = _get(sym)
        if _ok(df):
            res = full_rigor(f"Seasonality {sym}", seasonality_returns(df), n_trials)
            results.append(res); lines.append(rigor_row(res))

    for lead, tgt in lead_lag_pairs:
        dl, dt = _get(lead), _get(tgt)
        if _ok(dl) and _ok(dt):
            res = full_rigor(f"LeadLag {lead}->{tgt}", lead_lag_returns(dl, dt), n_trials)
            results.append(res); lines.append(rigor_row(res))

    if term_structure:
        f, b, t = term_structure.get("front"), term_structure.get("back"), term_structure.get("trade")
        df_f, df_b, df_t = _get(f), _get(b), _get(t)
        if _ok(df_f) and _ok(df_b) and _ok(df_t):
            res = full_rigor(f"TermStruct {f}/{b}->{t}",
                             term_structure_returns(df_f, df_b, df_t), n_trials)
            results.append(res); lines.append(rigor_row(res))
        else:
            lines.append(f"| TermStruct {f}/{b}->{t} | data unavailable (needs vol ETFs) |||||||")

    for sym in weekday_symbols:
        df = _get(sym)
        if _ok(df):
            res = full_rigor(f"Weekday {sym}", weekday_returns(df), n_trials)
            results.append(res); lines.append(rigor_row(res))

    lines.append("")
    survivors = [r for r in results if r.get("verdict", "").startswith("✅")]
    lines.append(f"**Summary:** {len(survivors)} of {len(results)} hypotheses survive the full "
                 f"rigor battery. " + (", ".join(r["name"] for r in survivors) if survivors else
                 "None — all fail significance, walk-forward, or regime stability."))
    return "\n".join(lines)
