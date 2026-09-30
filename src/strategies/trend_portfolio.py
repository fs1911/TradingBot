"""
Multi-asset trend portfolio (long-only) — the live implementation of the one
approach that held up in the research (#40/#41: time-series momentum across asset
classes, Moskowitz/Ooi/Pedersen 2012; Hurst/Ooi/Pedersen "A Century of Evidence").

Rule, evaluated once a month:
  signal_a  = mean over horizons (3, 6, 12 months, calendar days) of
              sign(return_a − return_cash), clipped at 0  → 0, 1/3, 2/3 or 1
  raw_a     = signal_a / annualised volatility_a (60 trading days)
  weights   = raw scaled so the portfolio's ex-ante volatility (120-day
              covariance) is `target_vol`, then capped per asset and at a total
              of `max_gross` (1.0 = no leverage). The remainder stays in cash.

Honest expectation from #40 (long-only, 2006–2025): ~5% a year at ~6.5% volatility,
max drawdown ~−20% (S&P −55%), weak since 2012. It is crash insurance for a
multi-asset portfolio, not a money machine.

Pure functions; the bot supplies prices and executes the orders.
"""
from __future__ import annotations
import math
from datetime import datetime

import numpy as np
import pandas as pd

DEFAULT_HORIZONS = (91, 182, 365)   # calendar days ≈ 3, 6, 12 months


def build_panel(closes: dict, calendar: str | None = None) -> pd.DataFrame:
    """Daily closes aligned on the trading calendar of `calendar` (e.g. SPY), so
    24/7 crypto and exchange-traded ETFs share one index. Crypto is forward-filled
    over weekends (its Friday→Monday move lands on Monday)."""
    cols = {}
    for k, s in closes.items():
        if s is None or len(s) == 0:
            continue
        s = pd.Series(s).astype(float).dropna().sort_index()
        idx = pd.to_datetime(s.index)
        idx = idx.tz_convert(None) if idx.tz is not None else idx
        s.index = idx.normalize()
        cols[k] = s[~s.index.duplicated(keep="last")]
    if not cols:
        return pd.DataFrame()
    px = pd.DataFrame(cols).sort_index()
    if calendar and calendar in px.columns:
        cal = px[calendar].dropna().index
        px = px.ffill(limit=4).reindex(cal)
    return px


def _horizon_return(s: pd.Series, asof: pd.Timestamp, days: int) -> float | None:
    past = s.loc[: asof - pd.Timedelta(days=days)].dropna()
    now = s.loc[:asof].dropna()
    if past.empty or now.empty or past.iloc[-1] <= 0:
        return None
    return float(now.iloc[-1] / past.iloc[-1] - 1)


def signals(panel: pd.DataFrame, cash_col: str | None = "BIL",
            horizons=DEFAULT_HORIZONS, max_stale_days: int = 7) -> pd.Series:
    """Long-only trend signal per asset in [0, 1] as of the panel's last date.
    Assets without a full longest-horizon history or with stale data get no signal."""
    if panel.empty:
        return pd.Series(dtype=float)
    asof = panel.index[-1]
    cash = panel[cash_col] if cash_col and cash_col in panel.columns else None
    out = {}
    for a in panel.columns:
        if a == cash_col:
            continue
        s = panel[a].dropna()
        if s.empty or (asof - s.index[-1]).days > max_stale_days:
            continue
        if (s.index[-1] - s.index[0]).days < max(horizons):
            continue
        votes = []
        for h in horizons:
            r = _horizon_return(s, asof, h)
            if r is None:
                break
            c = _horizon_return(cash, asof, h) if cash is not None else 0.0
            votes.append(np.sign(r - (c or 0.0)))
        if len(votes) == len(horizons):
            out[a] = max(0.0, float(np.mean(votes)))
    return pd.Series(out, dtype=float)


def target_weights(panel: pd.DataFrame, cash_col: str | None = "BIL",
                   horizons=DEFAULT_HORIZONS, target_vol: float = 0.10,
                   max_gross: float = 1.0, max_weight: float = 0.25,
                   caps: dict | None = None, vol_window: int = 60,
                   cov_window: int = 120) -> pd.Series:
    """Target portfolio weights (fraction of equity, ≥ 0, Σ ≤ max_gross)."""
    sig = signals(panel, cash_col, horizons)
    sig = sig[sig > 0]
    if sig.empty:
        return pd.Series(dtype=float)
    rets = panel[list(sig.index)].pct_change(fill_method=None)
    vol = rets.tail(vol_window).std() * math.sqrt(252)
    raw = (sig / vol.replace(0, np.nan)).dropna()
    raw = raw[raw > 0]
    if raw.empty:
        return pd.Series(dtype=float)
    cov = rets[raw.index].tail(cov_window).fillna(0.0).cov().to_numpy() * 252
    pv = math.sqrt(max(float(raw.to_numpy() @ cov @ raw.to_numpy()), 1e-12))
    w = raw * (target_vol / pv)
    cap = pd.Series(max_weight, index=w.index)
    for k, v in (caps or {}).items():
        if k in cap.index:
            cap[k] = min(cap[k], v)
    w = w.clip(upper=cap)
    g = float(w.sum())
    if g > max_gross:
        w = w * (max_gross / g)
    return w[w > 1e-6]


def rebalance_orders(weights: pd.Series, equity: float, prices: dict, holdings: dict,
                     min_trade_usd: float = 200.0, min_trade_pct: float = 0.01) -> list:
    """Orders to move `holdings` {symbol: qty} to `weights`. Returns
    [(symbol, delta_qty, reason)], sells first. Positions outside the targets are
    closed completely; small adjustments below the thresholds are skipped to save
    costs (full exits and new entries always go through)."""
    thr = max(min_trade_usd, min_trade_pct * equity)
    orders = []
    for sym in set(holdings) | set(weights.index):
        px = prices.get(sym)
        cur = float(holdings.get(sym, 0.0))
        tgt_w = float(weights.get(sym, 0.0))
        if not px or px <= 0:
            continue
        cur_val = cur * px
        tgt_val = tgt_w * equity
        delta_val = tgt_val - cur_val
        if tgt_w == 0.0 and cur != 0.0:
            orders.append((sym, -cur, "exit"))
        elif cur == 0.0 and tgt_val >= thr:
            orders.append((sym, tgt_val / px, "entry"))
        elif cur != 0.0 and abs(delta_val) >= thr:
            orders.append((sym, delta_val / px, "rebalance"))
    return sorted(orders, key=lambda o: o[1])   # sells (negative) first


def rebalance_due(now: datetime, last_month: str | None, market_open: bool,
                  earliest_utc_hour: int = 15) -> bool:
    """Once per calendar month, on the first market day/time it is possible:
    US market open and at least ~30 min after the open (15:00 UTC covers both
    daylight-saving regimes)."""
    if not market_open or now.hour < earliest_utc_hour:
        return False
    return last_month != now.strftime("%Y-%m")
