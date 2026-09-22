"""
Experiment #28 — dated quarterly-futures calendar basis: a carry AND a signal.

This is the last genuinely-distinct structural carry, and it targets #25's weakness
head-on. A dated (quarterly) future trades at a premium (contango) to spot; buy spot,
short the future, hold to expiry where they converge — capturing the premium with
almost NO turnover (one entry, one settlement), unlike the perp carry's constant
rehedging. If the data exists, this could be the more tradeable cousin.

It serves TWO goals (per the user's Finanzradar direction):
  1. CARRY (the bot trade): the delta-neutral spot-long / future-short daily return
     through the full rigor battery.
  2. SIGNAL (for Finanzradar): the ANNUALISED BASIS is itself a clean sentiment gauge —
     high contango = leveraged/overheated (→ "Überhitzt"), backwardation = fear
     (→ "Kaufen"). We test whether a high basis predicts LOWER forward spot returns
     (contrarian froth signal), which is directly usable in a valuation traffic-light.

Data (expired dated contracts via ccxt) is often incomplete; the report says so
honestly if unavailable. Analysis is pure/causal and injected for CI.
"""
from __future__ import annotations
from typing import Callable, Optional, Tuple
import numpy as np
import pandas as pd

from .rigor import full_rigor, annualized_sharpe


def annualized_basis(spot_px: float, fut_px: float, days_to_expiry: float) -> float:
    """(future/spot − 1) annualised by time to expiry. Positive = contango."""
    if days_to_expiry <= 0 or spot_px <= 0 or not np.isfinite(fut_px):
        return float("nan")
    return (fut_px / spot_px - 1.0) * (365.0 / days_to_expiry)


def basis_carry_returns(spot: pd.Series, front_future: pd.Series,
                        rolls_per_year: int = 4, roll_cost_bps: float = 20.0) -> pd.Series:
    """Daily return of a delta-neutral long-spot / short-front-future position
    (≈ spot_ret − future_ret; cumulates the captured basis), minus amortised roll
    cost. Very low turnover: only `rolls_per_year` rolls."""
    df = pd.concat({"s": spot, "f": front_future}, axis=1).dropna()
    if len(df) < 200:
        return pd.Series(dtype=float)
    daily = (df["s"].pct_change() - df["f"].pct_change()).fillna(0.0)
    daily_cost = (rolls_per_year * roll_cost_bps / 1e4) / 252.0
    return daily - daily_cost


def basis_signal_forward_returns(spot: pd.Series, ann_basis: pd.Series,
                                 horizon: int = 30, n_buckets: int = 5) -> pd.DataFrame:
    """Finanzradar signal test: bucket days by annualised basis, report the mean
    forward `horizon`-day spot return per bucket. If high-basis buckets have LOWER
    forward returns, the basis is a usable contrarian froth gauge."""
    df = pd.concat({"basis": ann_basis, "spot": spot}, axis=1).dropna()
    if len(df) < horizon + 100:
        return pd.DataFrame()
    df["fwd"] = df["spot"].shift(-horizon) / df["spot"] - 1.0
    df = df.dropna()
    if len(df) < 100:
        return pd.DataFrame()
    try:
        df["bucket"] = pd.qcut(df["basis"], n_buckets, labels=False, duplicates="drop")
    except ValueError:
        return pd.DataFrame()
    g = df.groupby("bucket").agg(basis_lo=("basis", "min"), basis_hi=("basis", "max"),
                                 fwd_ret=("fwd", "mean"), n=("fwd", "size"))
    return g


def build_dated_basis_fetcher(exchanges=("okx", "binance", "bybit"),
                              lookback_days: int = 1400):
    """Best-effort ccxt fetcher for dated quarterly-futures basis. Returns
    fetch_basis(symbol) -> (spot, synthetic_front_future, ann_basis) or None. Expired
    dated-contract history is often unavailable publicly, so this degrades gracefully:
    if it cannot assemble ≥200 aligned days it returns None for that symbol."""
    from .experiments_24 import open_swap_exchange
    import ccxt  # lazy

    clients = {}
    for exid in exchanges:
        try:
            fut = open_swap_exchange(exid)            # markets loaded
            spot = getattr(ccxt, exid)({"enableRateLimit": True,
                                        "options": {"defaultType": "spot"}})
            spot.load_markets()
            clients[exid] = (fut, spot)
        except Exception:
            pass

    def _daily_closes(ex, symbol, since_ms):
        try:
            ohlcv = ex.fetch_ohlcv(symbol, "1d", since=since_ms, limit=1500)
        except Exception:
            return pd.Series(dtype=float)
        if not ohlcv:
            return pd.Series(dtype=float)
        s = pd.Series({pd.to_datetime(r[0], unit="ms", utc=True).normalize(): float(r[4])
                       for r in ohlcv if r[4] is not None})
        return s.sort_index()

    def fetch_basis(symbol: str):
        base = symbol.split("/")[0]
        since = None
        for exid, (fut, spot) in clients.items():
            now_ms = fut.milliseconds()
            since = now_ms - lookback_days * 86400 * 1000
            # discover dated futures for this base
            contracts = []
            for m in fut.markets.values():
                if (m.get("future") and m.get("base") == base and m.get("quote") == "USDT"
                        and m.get("expiry")):
                    contracts.append((int(m["expiry"]), m["symbol"]))
            if not contracts:
                continue
            spot_px = _daily_closes(spot, f"{base}/USDT", since)
            if len(spot_px) < 200:
                continue
            # per-date front contract close + days-to-expiry
            front_close, dte = {}, {}
            for exp_ms, csym in sorted(contracts):
                closes = _daily_closes(fut, csym, since)
                for dt, px in closes.items():
                    d2e = (pd.Timestamp(exp_ms, unit="ms", tz="UTC") - dt).days
                    if d2e <= 0:
                        continue
                    # keep the nearest (smallest positive dte) contract per date
                    if dt not in dte or d2e < dte[dt]:
                        dte[dt] = d2e
                        front_close[dt] = px
            if len(front_close) < 200:
                continue
            fc = pd.Series(front_close).sort_index()
            de = pd.Series(dte).sort_index()
            df = pd.concat({"s": spot_px, "f": fc, "d": de}, axis=1).dropna()
            if len(df) < 200:
                continue
            ann_basis = ((df["f"] / df["s"] - 1.0) * (365.0 / df["d"])).rename("ann_basis")
            # synthetic back-adjusted future price: clean daily returns, no roll jumps
            fut_ret = df["f"].pct_change()
            # zero-out implausible roll jumps (>15% one-day gap between contracts)
            fut_ret[fut_ret.abs() > 0.15] = 0.0
            synth_future = float(df["s"].iloc[0]) * (1.0 + fut_ret.fillna(0.0)).cumprod()
            return df["s"], synth_future, ann_basis
        return None

    return fetch_basis


def run_experiment28_report(fetch_basis: Callable[[str], Optional[Tuple]],
                            symbols: list[str], n_trials: int = 96,
                            horizon: int = 30) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #28 — dated-futures calendar basis: carry & signal "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append("Long spot / short quarterly future, held toward expiry (near-zero "
                 f"turnover). Carry through full rigor (α/{n_trials}); PLUS the "
                 f"annualised basis as a Finanzradar sentiment gauge (does high "
                 f"contango predict lower {horizon}d forward spot returns?).")
    lines.append("")

    carries, signal_tables, avail = {}, {}, []
    lines.append("## Carry (the delta-neutral trade)")
    lines.append("| Coin | days | avg ann.basis% | carry ann% | Sharpe | p | Verdict |")
    lines.append("|---|--:|--:|--:|--:|--:|---|")
    for sym in symbols:
        try:
            got = fetch_basis(sym)
        except Exception:
            got = None
        if not got:
            lines.append(f"| {sym} | — | — | — | — | — | no dated-futures data |")
            continue
        spot, future, ann_basis = got
        carry = basis_carry_returns(spot, future)
        if len(carry) < 200:
            lines.append(f"| {sym} | {len(carry)} | — | — | — | — | short data |")
            continue
        avail.append(sym)
        carries[sym] = carry
        sig = basis_signal_forward_returns(spot, ann_basis, horizon)
        if not sig.empty:
            signal_tables[sym] = sig
        avg_basis = 100 * float(ann_basis.dropna().mean())
        carry_ann = 100 * float(carry.mean()) * 252
        res = full_rigor(f"basis carry {sym}", carry, n_trials)
        vshort = ("✅" if res.get("verdict", "").startswith("✅")
                  else "⚠️" if res.get("verdict", "").startswith("⚠") else "❌")
        lines.append(f"| {sym} | {len(carry)} | {avg_basis:+.1f} | {carry_ann:+.1f} | "
                     f"{res.get('sharpe', '—')} | {res.get('p_value', '—')} | {vshort} |")
    lines.append("")

    if not avail:
        lines.append("---")
        lines.append("**Summary:** no dated-futures history was available via ccxt for "
                     "any symbol — the calendar-basis carry is not backtestable here. "
                     "Note: the perpetual funding rate (#24) is the perp analogue of "
                     "this same premium and IS accessible; the Finanzradar froth signal "
                     "can be built from funding instead (proposed as #29).")
        return "\n".join(lines)

    # Finanzradar signal section
    lines.append(f"## Finanzradar signal — basis vs forward {horizon}d spot return")
    lines.append("| Coin | low-basis bucket fwd% | high-basis bucket fwd% | contrarian? |")
    lines.append("|---|--:|--:|:--:|")
    contrarian_hits = 0
    for sym, g in signal_tables.items():
        lo = 100 * float(g["fwd_ret"].iloc[0])
        hi = 100 * float(g["fwd_ret"].iloc[-1])
        good = hi < lo   # high basis (overheated) → lower forward return
        contrarian_hits += int(good)
        lines.append(f"| {sym} | {lo:+.1f} | {hi:+.1f} | {'✅ yes' if good else '❌ no'} |")
    lines.append("")

    lines.append("---")
    lines.append(
        f"**Summary:** {len(avail)} coins had usable dated-futures data. "
        f"Basis-as-froth-signal is contrarian (high basis → lower forward return) in "
        f"{contrarian_hits}/{len(signal_tables)} coins — the usable Finanzradar read. "
        "The carry itself is low-turnover; judge it against #25's cost lesson, and "
        "remember the usual crypto-derivatives tail risks are unpriced here.")
    return "\n".join(lines)
