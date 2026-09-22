"""
Experiment #24 — crypto funding-rate carry (a structural, non-predictive premium).

Everything so far tried to *predict* prices (timing, selection) or harvest
*structure* from price paths (rebalancing). All failed. This is different in kind:
it does not forecast anything. On perpetual-futures exchanges, longs pay shorts a
periodic "funding" fee (typically every 8h), which in bull regimes is persistently
positive. A DELTA-NEUTRAL position — long spot, short the perp — carries no price
risk yet collects that funding. That is a real, documented cash-and-carry premium.

This measures the historical carry: it takes each coin's funding-rate history,
converts it to a daily carry return for the (delta-neutral) short-perp side, and runs
it through the full rigor battery across cost scenarios, plus a diversified basket.

⚠️ HONESTY — READ THIS. The rigor battery tests "was the mean positive and stable?".
Funding carry is a smooth positive drip, so it will likely LOOK strongly significant.
But the battery does NOT capture this strategy's real risks: exchange/counterparty
failure, liquidation of the short leg in a spike, and funding-regime flips (deeply
negative funding in bear markets / deleveraging). A ✅ here means "the carry was
persistently positive in-sample", NOT "risk-free money". It is also NOT tradeable on
the current broker (Alpaca has no perps) — it would need a derivatives exchange.

Data is injected (`fetch_funding`) so this stays pure-pandas in CI; the bot supplies a
ccxt-backed fetcher on the VM. Fully causal.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor, rigor_row, RIGOR_HEADER, annualized_sharpe


def page_funding_history(ex, symbol: str, lookback_days: int = 1400,
                         page_limit: int = 200) -> pd.Series:
    """Page a ccxt exchange's funding-rate history FORWARD from `lookback_days` ago
    into a UTC-indexed pd.Series. Exchanges cap ~200 rows/call, so advance `since`
    past the last returned timestamp until now. Public data — no API keys."""
    now_ms = ex.milliseconds()
    since = now_ms - lookback_days * 86400 * 1000
    rows, guard = {}, 0
    while since < now_ms and guard < 600:
        guard += 1
        try:
            batch = ex.fetch_funding_rate_history(symbol, since=since, limit=page_limit)
        except Exception:
            break
        if not batch:
            since += page_limit * 8 * 3600 * 1000        # skip an empty window
            continue
        last_ts = since
        for r in batch:
            ts, fr = r.get("timestamp"), r.get("fundingRate")
            if ts is None or fr is None:
                continue
            rows[int(ts)] = float(fr)
            last_ts = max(last_ts, int(ts))
        if last_ts <= since and len(batch) < page_limit:
            break                                        # no forward progress
        since = last_ts + 1
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series({pd.to_datetime(ts, unit="ms", utc=True): fr
                      for ts, fr in rows.items()}).sort_index()


def open_swap_exchange(exchange_id: str):
    """Open a public ccxt swap/perp exchange client (lazy import; no API keys)."""
    import ccxt  # lazy: only on the VM
    ex = getattr(ccxt, exchange_id)({"enableRateLimit": True,
                                     "options": {"defaultType": "swap"}})
    ex.load_markets()
    return ex


def build_ccxt_funding_fetcher(exchange_ids=("bybit", "binance", "okx"),
                               lookback_days: int = 1400):
    """Return (fetch_funding, exchange_id_used). Picks the first public exchange that
    returns BTC funding history, then uses it for all symbols. `fetch_funding(symbol)`
    pages the full funding-rate history into a UTC-indexed pd.Series."""
    chosen = None
    for exid in exchange_ids:
        try:
            ex = open_swap_exchange(exid)
            if len(page_funding_history(ex, "BTC/USDT:USDT", lookback_days)) > 100:
                chosen = (ex, exid)
                break
        except Exception as e:
            logger.warning(f"Exp24: exchange {exid} unusable: {e}")
    if chosen is None:
        raise RuntimeError("No public exchange returned funding history")

    ex, exid = chosen

    def fetch_funding(symbol: str) -> pd.Series:
        return page_funding_history(ex, symbol, lookback_days)

    return fetch_funding, exid


def funding_to_daily_carry(funding: pd.Series) -> pd.Series:
    """Convert a per-interval funding-rate series (positive = longs pay shorts) into
    the daily carry return earned by a delta-neutral short-perp position (= sum of
    that day's funding rates)."""
    if funding is None or len(funding) == 0:
        return pd.Series(dtype=float)
    f = pd.Series(funding).dropna().astype(float).sort_index()
    idx = pd.to_datetime(f.index)
    idx = idx.tz_localize(None) if idx.tz is not None else idx
    f.index = idx.normalize()
    return f.groupby(level=0).sum()


def carry_stats(funding: pd.Series, daily: pd.Series) -> dict:
    """Honesty diagnostics beyond the rigor battery."""
    f = pd.Series(funding).dropna().astype(float)
    cum = (1.0 + daily.fillna(0.0)).cumprod()
    peak = cum.cummax()
    max_dd = float(((cum / peak) - 1.0).min()) if len(cum) else 0.0
    return {
        "pct_negative": round(100 * float((f < 0).mean()), 1) if len(f) else float("nan"),
        "total_return_pct": round(100 * (float(cum.iloc[-1]) - 1.0), 1) if len(cum) else 0.0,
        "max_drawdown_pct": round(100 * max_dd, 1),
        "days": int(len(daily)),
    }


def run_experiment24_report(fetch_funding: Callable[[str], pd.Series],
                            symbols: list[str], n_trials: int = 78,
                            cost_scenarios_annual: tuple = (0.0, 0.02, 0.05)) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #24 — crypto funding-rate carry "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append("Delta-neutral (long spot / short perp) carry from perpetual funding. "
                 f"Daily carry through the full rigor battery; cost scenarios (annual "
                 f"drag for hedge maintenance): {', '.join(f'{c:.0%}' for c in cost_scenarios_annual)}. "
                 f"Haircut α/{n_trials}.")
    lines.append("")
    lines.append("> ⚠️ A ✅ here means the carry was persistently positive IN-SAMPLE — "
                 "NOT risk-free. The battery cannot see exchange/counterparty risk, "
                 "short-leg liquidation, or funding-regime flips in a bear market. Also "
                 "NOT tradeable on Alpaca (no perps) — research only.")
    lines.append("")

    dailies: dict[str, pd.Series] = {}
    lines.append("## Per-coin carry")
    lines.append("| Coin | days | funding<0 % | total carry% | maxDD% | Sharpe | p-value | sig | Verdict |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|:--:|---|")
    for sym in symbols:
        try:
            funding = fetch_funding(sym)
        except Exception as e:
            logger.warning(f"Exp24: fetch funding {sym} failed: {e}")
            funding = None
        daily = funding_to_daily_carry(funding) if funding is not None else pd.Series(dtype=float)
        if len(daily) < 300:
            lines.append(f"| {sym} | {len(daily)} | — | — | — | — | — | — | no/short data |")
            continue
        dailies[sym] = daily
        st = carry_stats(funding, daily)
        # rigor at the mid cost scenario (drag applied per day)
        mid = cost_scenarios_annual[min(1, len(cost_scenarios_annual) - 1)]
        res = full_rigor(f"carry {sym}", daily - mid / 252.0, n_trials)
        if res.get("verdict") == "insufficient data":
            lines.append(f"| {sym} | {st['days']} | {st['pct_negative']} | "
                         f"{st['total_return_pct']} | {st['max_drawdown_pct']} | — | — | — | insufficient |")
            continue
        vshort = ("✅" if res["verdict"].startswith("✅")
                  else "⚠️" if res["verdict"].startswith("⚠") else "❌")
        lines.append(f"| {sym} | {st['days']} | {st['pct_negative']} | {st['total_return_pct']} | "
                     f"{st['max_drawdown_pct']} | {res['sharpe']} | {res['p_value']} | "
                     f"{'y' if res['sig_after_haircut'] else 'n'} | {vshort} |")
    lines.append("")

    # diversified equal-weight basket + cost sweep
    all_results = []
    if dailies:
        basket = pd.concat(dailies.values(), axis=1).mean(axis=1).dropna()
        lines.append("## Diversified basket (equal-weight across coins), cost sweep")
        lines.append(RIGOR_HEADER)
        for c in cost_scenarios_annual:
            res = full_rigor(f"basket carry @ {c:.0%}/yr", basket - c / 252.0, n_trials)
            all_results.append(res)
            lines.append(rigor_row(res))
        lines.append("")

    survivors = [r for r in all_results if r.get("verdict", "").startswith("✅")]
    lines.append("---")
    lines.append(
        f"**Summary:** {len(dailies)} coins with usable funding history. "
        f"Basket configs surviving rigor: {len(survivors)}/{len(all_results)}. "
        "Remember: surviving rigor here = persistent positive carry in-sample, not a "
        "risk-free edge, and not executable on Alpaca. If it survives, the honest next "
        "step is a small-scale, real-cost feasibility study on a derivatives venue.")
    return "\n".join(lines)
