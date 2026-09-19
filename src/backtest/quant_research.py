"""
Quant research module — the "research first" approach.

Instead of imposing a strategy and testing it, this measures the STATISTICAL
STRUCTURE of the data to find where (if anywhere) prices are non-random and
exploitable — then tests the one market-neutral, mathematically-grounded strategy
that structure enables: statistical-arbitrage pairs trading on a mean-reverting
(cointegrated) spread.

Two parts:
  1. Market-structure diagnostics per asset: Hurst exponent, variance ratio,
     lag-1 return autocorrelation → is this asset mean-reverting / trending /
     random walk?
  2. Pairs stat-arb: for each pair, a causal rolling hedge ratio (cov/var of log
     prices) forms a spread; if the spread mean-reverts (short half-life), trade
     its z-score market-neutral. Tested OOS + walk-forward, net of costs.

Pure numpy/pandas — no statsmodels. Everything is causal (rolling, past-only).
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .trend_follow import _curve_stats
from .xsec_momentum import _price_panel
from .oos_runner import split_is_oos


# ─── market-structure diagnostics ────────────────────────────────────────────
def hurst_exponent(prices: pd.Series, max_lag: int = 60) -> float:
    """H<0.5 mean-reverting, H≈0.5 random walk, H>0.5 trending. Via the scaling of
    the std of lagged log-price differences."""
    p = np.log(prices.dropna().to_numpy())
    if len(p) < max_lag * 2:
        return float("nan")
    lags = range(2, max_lag)
    tau = [np.std(p[lag:] - p[:-lag]) for lag in lags]
    tau = np.array(tau)
    if np.any(tau <= 0):
        return float("nan")
    return float(np.polyfit(np.log(list(lags)), np.log(tau), 1)[0])


def variance_ratio(prices: pd.Series, q: int = 5) -> float:
    """Lo-MacKinlay-style VR(q): Var(q-period returns)/(q·Var(1-period)). ~1 random
    walk, <1 mean-reverting, >1 trending/persistent."""
    r = np.log(prices).diff().dropna().to_numpy()
    n = len(r)
    if n < q * 3:
        return float("nan")
    var1 = np.var(r, ddof=1)
    rq = np.add.reduceat(r, np.arange(0, n - n % q, q))
    varq = np.var(rq, ddof=1)
    return float(varq / (q * var1)) if var1 > 0 else float("nan")


def lag1_autocorr(prices: pd.Series) -> float:
    r = np.log(prices).diff().dropna()
    return float(r.autocorr(lag=1)) if len(r) > 10 else float("nan")


def analyze_structure(data: dict[str, pd.DataFrame]) -> list[dict]:
    out = []
    for sym, d in data.items():
        c = d["close"].sort_index()
        h = hurst_exponent(c)
        vr = variance_ratio(c)
        ac = lag1_autocorr(c)
        if np.isnan(h):
            verdict = "n/a"
        elif h < 0.45:
            verdict = "mean-reverting"
        elif h > 0.55:
            verdict = "trending"
        else:
            verdict = "random walk"
        out.append({"symbol": sym, "hurst": round(h, 2) if not np.isnan(h) else None,
                    "var_ratio": round(vr, 2) if not np.isnan(vr) else None,
                    "autocorr": round(ac, 3) if not np.isnan(ac) else None,
                    "verdict": verdict})
    return out


# ─── pairs statistical arbitrage ─────────────────────────────────────────────
def _half_life(spread: pd.Series) -> float:
    """Half-life of mean reversion via an Ornstein-Uhlenbeck (AR1) fit:
    Δs_t = a + b·s_{t-1}; half-life = -ln(2)/b (only meaningful if b<0)."""
    s = spread.dropna()
    if len(s) < 30:
        return float("inf")
    s_lag = s.shift(1).dropna()
    ds = (s - s.shift(1)).dropna()
    s_lag, ds = s_lag.align(ds, join="inner")
    x = s_lag.to_numpy()
    y = ds.to_numpy()
    if np.var(x) == 0:
        return float("inf")
    b = np.polyfit(x, y, 1)[0]
    if b >= 0:
        return float("inf")
    return float(-np.log(2) / b)


def pair_spread(log_a: pd.Series, log_b: pd.Series, beta_window: int) -> tuple[pd.Series, pd.Series]:
    """Causal rolling hedge ratio beta = Cov(a,b)/Var(b) over the trailing window;
    spread = log_a − beta·log_b. Uses only past data at each point."""
    cov = log_a.rolling(beta_window).cov(log_b)
    var = log_b.rolling(beta_window).var()
    beta = (cov / var).replace([np.inf, -np.inf], np.nan)
    spread = log_a - beta * log_b
    return spread, beta


def backtest_pair(a: pd.Series, b: pd.Series, *, beta_window: int = 120, z_window: int = 60,
                  entry: float = 2.0, exit: float = 0.5, commission_pct: float = 0.05,
                  slippage_pct: float = 0.03, borrow_pct_annual: float = 0.0) -> pd.Series:
    """Market-neutral z-score mean-reversion on the pair spread. Fully causal.
    Returns daily net strategy returns (as a fraction of the gross leg exposure).

    borrow_pct_annual models the cost of shorting one leg: a daily drag applied
    whenever a position is open (the honest cost the first backtest ignored)."""
    df = pd.concat({"a": a, "b": b}, axis=1).dropna()
    if len(df) < beta_window + z_window + 40:
        return pd.Series(dtype=float)
    la, lb = np.log(df["a"]), np.log(df["b"])
    spread, beta = pair_spread(la, lb, beta_window)
    mu = spread.rolling(z_window).mean()
    sd = spread.rolling(z_window).std()
    z = (spread - mu) / sd

    ra, rb = la.diff(), lb.diff()
    cost = (commission_pct + slippage_pct) / 100
    borrow_daily = (borrow_pct_annual / 100) / 252

    pos = np.zeros(len(df))          # +1 long spread (long A, short B); -1 short spread
    zz = z.to_numpy()
    cur = 0
    for i in range(len(df)):
        if np.isnan(zz[i]):
            pos[i] = 0
            continue
        if cur == 0:
            if zz[i] > entry:
                cur = -1
            elif zz[i] < -entry:
                cur = 1
        elif cur == 1 and zz[i] >= -exit:
            cur = 0
        elif cur == -1 and zz[i] <= exit:
            cur = 0
        pos[i] = cur

    pos_s = pd.Series(pos, index=df.index).shift(1).fillna(0)     # act next bar
    # spread return ≈ ra − beta·rb; normalise leg exposure to ~1 (a + |beta|·b)
    beta_f = beta.reindex(df.index).ffill().fillna(0)
    gross = (1 + beta_f.abs()).replace(0, 1)
    spread_ret = (ra - beta_f * rb).fillna(0) / gross
    turn = pos_s.diff().abs().fillna(pos_s.abs())
    borrow = borrow_daily * pos_s.abs()                          # short-leg carry while in a trade
    return (pos_s * spread_ret - turn * cost - borrow).rename("ret")


def find_pairs(data: dict[str, pd.DataFrame], beta_window: int = 120,
               max_pairs: int = 8) -> list[tuple[str, str, float]]:
    """Rank pairs by spread mean-reversion speed (half-life) on the in-sample half.
    Returns [(sym_a, sym_b, half_life)] for the most tradeable pairs."""
    panel = _price_panel(data)
    is_p, _ = split_is_oos(panel)
    syms = list(panel.columns)
    scored = []
    for i in range(len(syms)):
        for j in range(i + 1, len(syms)):
            la, lb = np.log(is_p[syms[i]]), np.log(is_p[syms[j]])
            spread, _ = pair_spread(la, lb, beta_window)
            hl = _half_life(spread)
            if 2 <= hl <= 60:               # fast enough to trade, not noise
                scored.append((syms[i], syms[j], round(hl, 1)))
    scored.sort(key=lambda t: t[2])         # shortest half-life first
    return scored[:max_pairs]


def find_pairs_grouped(data: dict[str, pd.DataFrame], groups: dict[str, list[str]],
                       beta_window: int = 120, max_pairs: int = 12) -> list[tuple[str, str, float]]:
    """Like find_pairs but only pairs WITHIN the same economic group (index ETFs,
    banks, big tech, metals, crypto) — removes economically nonsensical spurious
    pairs (e.g. AMD/BTC). Ranked by in-sample spread half-life."""
    panel = _price_panel(data)
    is_p, _ = split_is_oos(panel)
    have = set(panel.columns)
    scored = []
    for _, members in groups.items():
        ms = [m for m in members if m in have]
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                la, lb = np.log(is_p[ms[i]]), np.log(is_p[ms[j]])
                spread, _ = pair_spread(la, lb, beta_window)
                hl = _half_life(spread)
                if 2 <= hl <= 60:
                    scored.append((ms[i], ms[j], round(hl, 1)))
    scored.sort(key=lambda t: t[2])
    return scored[:max_pairs]


# Cost scenarios for the stress test: (label, commission%, slippage%, borrow%/yr)
COST_SCENARIOS = [
    ("optimistic", 0.02, 0.02, 0.0),
    ("base",       0.05, 0.03, 1.0),
    ("realistic",  0.05, 0.08, 3.0),
    ("harsh",      0.10, 0.15, 8.0),
]


def _pool_pairs(panel: pd.DataFrame, pairs, comm, slip, borrow) -> pd.DataFrame | None:
    cols = {}
    for a, b, _ in pairs:
        r = backtest_pair(panel[a], panel[b], commission_pct=comm, slippage_pct=slip,
                          borrow_pct_annual=borrow)
        if not r.empty:
            cols[f"{a}/{b}"] = r
    if not cols:
        return None
    return pd.DataFrame(cols)


def run_pairs_stress_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    groups: dict[str, list[str]],
    limit: int = 2000,
    window: int = 252,
    step: int = 63,
) -> str:
    """Stress-test the pairs stat-arb edge: economically-sensible pairs only, a
    cost-sensitivity sweep (incl. short borrow fees), and a leave-one-out
    robustness check. Returns Markdown."""
    from datetime import datetime, timezone

    symbols = sorted({s for members in groups.values() for s in members})
    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            d = get_ohlcv(sym, "1Day", limit)
            if d is not None and len(d) >= 400:
                data[sym] = d
        except Exception as e:
            logger.warning(f"Stress: could not fetch {sym}: {e}")

    lines = [f"# Pairs Stat-Arb Stress Test — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    if len(data) < 4:
        lines.append("_not enough data_")
        return "\n".join(lines)

    pairs = find_pairs_grouped(data, groups)
    lines.append("Economically-sensible pairs only (within index / banks / big-tech / metals / crypto).")
    lines.append("")
    if not pairs:
        lines.append("_no within-group mean-reverting pairs found — the earlier edge was spurious cross-domain pairs_")
        return "\n".join(lines)
    lines.append(f"**{len(pairs)} pairs:** {', '.join(f'{a}/{b}({hl}d)' for a, b, hl in pairs)}")
    lines.append("")

    panel = _price_panel(data)

    # 1) Cost sensitivity sweep
    lines.append("## Cost sensitivity — where does the edge die?")
    lines.append("| Scenario | comm/slip/borrow | OOS ret% | OOS MAR | Walk-fwd (MAR>0.5) |")
    lines.append("|---|---|--:|--:|:--:|")
    base_oos_mar = None
    for label, comm, slip, borrow in COST_SCENARIOS:
        pooled = _pool_pairs(panel, pairs, comm, slip, borrow)
        if pooled is None:
            lines.append(f"| {label} | {comm}/{slip}/{borrow}% | — | — | — |")
            continue
        port = pooled.mean(axis=1)
        _, oos = split_is_oos(port.to_frame("r"))
        st = _curve_stats(oos["r"])
        rows, i = [], 0
        while i + window <= len(port):
            ws = _curve_stats(port.iloc[i:i + window])
            rows.append(ws["ret"] > 0 and ws["mar"] > 0.5)
            i += step
        wf = f"{sum(rows)}/{len(rows)} ({round(100*sum(rows)/len(rows))}%)" if rows else "—"
        if label == "base":
            base_oos_mar = st["mar"]
        lines.append(f"| {label} | {comm}/{slip}/{borrow}% | {st['ret']:+.0f} | {st['mar']} | {wf} |")
    lines.append("")

    # 2) Leave-one-out robustness at realistic costs
    lines.append("## Robustness — is it driven by one lucky pair? (realistic costs)")
    pooled = _pool_pairs(panel, pairs, 0.05, 0.08, 3.0)
    if pooled is not None and pooled.shape[1] >= 2:
        def _oos_mar(dfcols: pd.DataFrame) -> float:
            port = dfcols.mean(axis=1)
            _, oos = split_is_oos(port.to_frame("r"))
            return _curve_stats(oos["r"])["mar"]
        full = _oos_mar(pooled)
        lines.append(f"Full portfolio OOS MAR (realistic costs): **{full}**")
        lines.append("")
        lines.append("| Pair | its OOS ret% | portfolio OOS MAR without it |")
        lines.append("|---|--:|--:|")
        for col in pooled.columns:
            _, oos_one = split_is_oos(pooled[[col]].rename(columns={col: "r"}))
            solo = _curve_stats(oos_one["r"])["ret"]
            without = _oos_mar(pooled.drop(columns=[col]))
            lines.append(f"| {col} | {solo:+.0f} | {without} |")
        lines.append("")
        lines.append("If removing any single pair collapses the MAR, the 'edge' rests on one pair (fragile).")
    lines.append("")
    lines.append("Verdict rule: a real, tradeable edge stays positive at REALISTIC costs, keeps a decent "
                 "walk-forward %, and does not depend on a single pair.")
    return "\n".join(lines)


def run_quant_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    symbols: list[str],
    limit: int = 2000,
    window: int = 252,
    step: int = 63,
    commission_pct: float = 0.05,
    slippage_pct: float = 0.03,
) -> str:
    from datetime import datetime, timezone

    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            d = get_ohlcv(sym, "1Day", limit)
            if d is not None and len(d) >= 400:
                data[sym] = d
        except Exception as e:
            logger.warning(f"Quant: could not fetch {sym}: {e}")

    lines = [f"# Quant Research — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    if len(data) < 3:
        lines.append("_not enough data_")
        return "\n".join(lines)

    # 1) market-structure diagnostics
    lines.append("## Market structure (is any asset non-random?)")
    lines.append("Hurst <0.45 = mean-reverting · >0.55 = trending · ~0.5 = random walk (no edge).")
    lines.append("")
    lines.append("| Symbol | Hurst | VarRatio | lag1 autocorr | verdict |")
    lines.append("|---|--:|--:|--:|---|")
    for r in analyze_structure(data):
        lines.append(f"| {r['symbol']} | {r['hurst']} | {r['var_ratio']} | {r['autocorr']} | {r['verdict']} |")
    lines.append("")

    # 2) pairs stat-arb
    pairs = find_pairs(data)
    lines.append("## Statistical-arbitrage pairs (market-neutral mean reversion)")
    if not pairs:
        lines.append("_no pairs with a tradeable mean-reverting spread found_")
        return "\n".join(lines)
    lines.append(f"Top pairs by spread half-life (in-sample): "
                 f"{', '.join(f'{a}/{b} ({hl}d)' for a, b, hl in pairs)}")
    lines.append("")

    # Pool the selected pairs into one equal-weight market-neutral portfolio
    panel = _price_panel(data)
    pair_rets = {}
    for a, b, _ in pairs:
        r = backtest_pair(panel[a], panel[b], commission_pct=commission_pct, slippage_pct=slippage_pct)
        if not r.empty:
            pair_rets[f"{a}/{b}"] = r
    if not pair_rets:
        lines.append("_pairs produced no tradeable series_")
        return "\n".join(lines)
    port = pd.DataFrame(pair_rets).mean(axis=1)

    is_r, oos_r = split_is_oos(port.to_frame("r"))
    is_s, oos_s = _curve_stats(is_r["r"]), _curve_stats(oos_r["r"])
    lines.append("| Segment | ret% | maxDD% | MAR |")
    lines.append("|---|--:|--:|--:|")
    lines.append(f"| In-Sample | {is_s['ret']:+.0f} | {is_s['dd']:.0f} | {is_s['mar']} |")
    lines.append(f"| Out-of-Sample | {oos_s['ret']:+.0f} | {oos_s['dd']:.0f} | {oos_s['mar']} |")
    lines.append("")

    # walk-forward: is the pairs portfolio positive with decent MAR across windows?
    rows, i = [], 0
    r = port
    while i + window <= len(r):
        st = _curve_stats(r.iloc[i:i + window])
        rows.append(st["ret"] > 0 and st["mar"] > 0.5)
        i += step
    if rows:
        nb, n = sum(rows), len(rows)
        pct = round(100 * nb / n)
        verdict = ("✅ robust market-neutral edge" if pct >= 60 else
                   "⚠️ regime-dependent" if pct >= 40 else "❌ not robust")
        lines.append(f"**Walk-forward:** positive with MAR>0.5 in **{nb}/{n} windows ({pct}%)** → {verdict}")
    lines.append("")
    lines.append("Pairs trading is market-neutral: it does not predict direction, only that a "
                 "mean-reverting spread returns to its mean. A robust edge stays positive across windows.")
    return "\n".join(lines)
