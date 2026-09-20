"""
Experiment #12 — the next batch of documented, data-feasible anomalies, each run
through the strong rigor battery (rigor.py). All strictly causal.

  - turn_of_month:  long only the last day + first few days of each month
  - overnight:      hold only overnight (buy at close, sell at next open) — the
                    documented "overnight drift" using our daily open/close data
  - rsi2:           Connors-style short-term reversal — long an index ETF when
                    RSI(2) is deeply oversold while above its 200-day trend
  - low_vol:        cross-sectional low-volatility anomaly — hold the lowest-vol
                    third of a universe, rebalanced monthly, vs equal weight
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor, rigor_row, RIGOR_HEADER
from .xsec_momentum import _price_panel


def _norm(s: pd.Series) -> pd.Series:
    s = s.sort_index()
    s.index = s.index.normalize()
    return s


def _rsi(closes: np.ndarray, period: int = 2) -> np.ndarray:
    out = np.full(len(closes), np.nan)
    if len(closes) < period + 1:
        return out
    d = np.diff(closes)
    g = np.where(d > 0, d, 0.0)
    l = np.where(d < 0, -d, 0.0)
    ag = g[:period].mean()
    al = l[:period].mean()
    out[period] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(period + 1, len(closes)):
        ag = (ag * (period - 1) + g[i - 1]) / period
        al = (al * (period - 1) + l[i - 1]) / period
        out[i] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def turn_of_month_returns(df, first=3, last=1, commission_pct=0.05, slippage_pct=0.03):
    c = _norm(df["close"]); r = c.pct_change().fillna(0)
    ym = c.index.tz_localize(None).to_period("M")
    pos = np.zeros(len(c))
    d = pd.DataFrame({"i": np.arange(len(c)), "ym": ym})
    for _, locs in d.groupby("ym")["i"]:
        arr = locs.to_numpy()
        for L in set(arr[:first]) | set(arr[-last:]):
            pos[L] = 1.0            # calendar known in advance → no look-ahead, no shift
    pos_s = pd.Series(pos, index=c.index)
    cost = (commission_pct + slippage_pct) / 100
    turn = pos_s.diff().abs().fillna(pos_s.abs())
    return (pos_s * r - turn * cost).rename("ret")


def overnight_returns(df, commission_pct=0.05, slippage_pct=0.03):
    o = _norm(df["open"]); c = _norm(df["close"])
    x = pd.concat({"o": o, "c": c}, axis=1).dropna()
    overnight = x["o"] / x["c"].shift(1) - 1        # close[t-1] -> open[t]
    cost = (commission_pct + slippage_pct) / 100
    return (overnight.fillna(0) - 2 * cost).rename("ret")   # in at close, out at open, every day


def rsi2_returns(df, oversold=10.0, commission_pct=0.05, slippage_pct=0.03):
    c = _norm(df["close"])
    arr = c.to_numpy()
    rsi = _rsi(arr, 2)
    sma200 = c.rolling(200).mean().to_numpy()
    sma5 = c.rolling(5).mean().to_numpy()
    pos = np.zeros(len(c))
    cur = 0
    for i in range(len(c)):
        if np.isnan(rsi[i]) or np.isnan(sma200[i]):
            pos[i] = 0; continue
        if cur == 0:
            if rsi[i] < oversold and arr[i] > sma200[i]:
                cur = 1
        elif arr[i] > sma5[i]:
            cur = 0
        pos[i] = cur
    pos_s = pd.Series(pos, index=c.index).shift(1).fillna(0)
    r = c.pct_change().fillna(0)
    cost = (commission_pct + slippage_pct) / 100
    turn = pos_s.diff().abs().fillna(pos_s.abs())
    return (pos_s * r - turn * cost).rename("ret")


def low_vol_returns(data: dict[str, pd.DataFrame], lookback=30, hold=21,
                    frac=0.34, commission_pct=0.05, slippage_pct=0.03):
    panel = _price_panel(data)
    if panel.shape[1] < 4:
        return pd.Series(dtype=float)
    rets = panel.pct_change().fillna(0)
    vol = rets.rolling(lookback).std()
    n_assets = panel.shape[1]
    k = max(1, int(round(frac * n_assets)))
    cost = (commission_pct + slippage_pct) / 100
    weights = np.zeros(n_assets)
    strat = np.zeros(len(panel))
    rv = rets.to_numpy()
    vv = vol.to_numpy()
    start = lookback
    for i in range(len(panel)):
        if i >= start and (i - start) % hold == 0 and not np.any(np.isnan(vv[i])):
            order = np.argsort(vv[i])        # lowest vol first
            nw = np.zeros(n_assets)
            nw[order[:k]] = 1.0 / k
            strat[i] -= np.abs(nw - weights).sum() * cost
            weights = nw
        strat[i] += float((weights * rv[i]).sum())
    return pd.Series(strat, index=panel.index).rename("ret")


def run_experiment12_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    index_symbols: list[str],
    lowvol_universe: list[str],
    n_trials: int = 30,
    limit: int = 2500,
) -> str:
    from datetime import datetime, timezone

    cache: dict[str, pd.DataFrame] = {}
    def _get(sym):
        if sym not in cache:
            try:
                cache[sym] = get_ohlcv(sym, "1Day", limit)
            except Exception as e:
                logger.warning(f"Exp12: fetch {sym} failed: {e}")
                cache[sym] = pd.DataFrame()
        return cache[sym]
    def _ok(df):
        return df is not None and len(df) >= 400

    lines = [f"# Experiment #12 — documented anomalies under the strong rigor battery "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"Causal strategies, realistic costs, multiple-testing haircut α/{n_trials}.")
    lines.append("")
    lines.append(RIGOR_HEADER)

    results = []
    for sym in index_symbols:
        df = _get(sym)
        if not _ok(df):
            continue
        for label, fn in [("TurnOfMonth", turn_of_month_returns),
                          ("Overnight", overnight_returns),
                          ("RSI2", rsi2_returns)]:
            res = full_rigor(f"{label} {sym}", fn(df), n_trials)
            results.append(res); lines.append(rigor_row(res))

    data = {s: _get(s) for s in lowvol_universe if _ok(_get(s))}
    if len(data) >= 4:
        res = full_rigor("LowVol universe", low_vol_returns(data), n_trials)
        results.append(res); lines.append(rigor_row(res))

    lines.append("")
    survivors = [r for r in results if r.get("verdict", "").startswith("✅")]
    lines.append(f"**Summary:** {len(survivors)}/{len(results)} survive the full battery. " +
                 (", ".join(r["name"] for r in survivors) if survivors else
                  "None — significance, walk-forward, or regime stability fails."))
    return "\n".join(lines)
