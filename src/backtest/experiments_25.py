"""
Experiment #25 — funding carry under REALISTIC costs, and the capital it needs.

#24 found the first real survivor: delta-neutral crypto funding carry, ~8%/yr gross,
Sharpe ~7-9 — but cost-fragile (dead by 5%/yr drag). #24 used an abstract % drag;
#25 replaces it with a concrete, defensible cost model built from an actual exchange
fee schedule, so we get the NET number that decides whether this is worth trading.

Cost components of a long-spot / short-perp carry:
  - round-trip execution: open (buy spot + sell perp) and close (sell spot + buy perp),
    each leg charged the taker (or maker) fee; amortised over the holding period.
  - rehedging: as spot moves, the 1:1 hedge drifts and must be reset; modelled as a
    per-year turnover cost proportional to realised volatility.
  - negative funding: already inside the data (negative days subtract directly).

It sweeps rotation frequency and fee tier (Bybit taker 0.055% / maker 0.02%), reports
net annual return, net Sharpe, and the capital required to earn a target income —
turning "Sharpe 7" into an honest francs-and-capital answer. Data injected; causal.
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

from .experiments_24 import funding_to_daily_carry

# Bybit-style fee schedule (fraction of notional, per leg)
FEE_TIERS = {"taker": 0.00055, "maker": 0.0002}
DEFAULT_TARGET_ANNUAL = 3650.0   # CHF/yr ≈ 10/day


def _annual_stats(daily: pd.Series):
    d = daily.dropna()
    if len(d) < 30:
        return None
    mean_ann = float(d.mean()) * 365.0
    vol_ann = float(d.std()) * np.sqrt(365.0)
    return mean_ann, vol_ann


def net_carry_model(daily_carry: pd.Series, spot_vol_annual: float,
                    rotation_days: int, fee: float,
                    rehedge_turnover_per_vol: float = 0.5) -> dict:
    """Turn a gross daily-carry series into net annual return & Sharpe under costs.

    - execution drag: 4 legs per rotation (open 2 + close 2) × fee, × rotations/yr.
    - rehedge drag: rehedge notional per year ≈ rehedge_turnover_per_vol × annual vol
      of the hedged leg; charged the fee. A rough, deliberately conservative proxy.
    """
    stats = _annual_stats(daily_carry)
    if stats is None:
        return {"insufficient": True}
    gross_ann, vol_ann = stats
    rotations = 365.0 / max(1, rotation_days)
    exec_drag = 4.0 * fee * rotations
    rehedge_drag = rehedge_turnover_per_vol * spot_vol_annual * fee * 52.0  # weekly rehedge check
    net_ann = gross_ann - exec_drag - rehedge_drag
    net_sharpe = (net_ann / vol_ann) if vol_ann > 0 else 0.0
    return {
        "gross_ann": gross_ann, "vol_ann": vol_ann,
        "exec_drag": exec_drag, "rehedge_drag": rehedge_drag,
        "net_ann": net_ann, "net_sharpe": net_sharpe,
    }


def run_experiment25_report(fetch_funding: Callable[[str], pd.Series],
                            symbols: list[str],
                            spot_vol_annual: float = 0.6,
                            target_annual: float = DEFAULT_TARGET_ANNUAL,
                            rotation_grid=(7, 30, 90),
                            rehedge_turnover_per_vol: float = 0.5) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #25 — funding carry, net of realistic costs "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append("Delta-neutral carry NET of a concrete fee model (Bybit taker "
                 f"{FEE_TIERS['taker']:.3%} / maker {FEE_TIERS['maker']:.3%} per leg), "
                 f"assumed hedge-leg annual vol {spot_vol_annual:.0%}. Sweeps rotation "
                 f"frequency and fee tier. Target income: {target_annual:,.0f} CHF/yr.")
    lines.append("")
    lines.append("> This converts the big Sharpe into francs. Net annual return × your "
                 "capital = your income; the last column is the capital needed to hit "
                 "the target. Counterparty/liquidation/basis risk are still NOT priced.")
    lines.append("")

    # diversified equal-weight basket of the coins that have usable data
    dailies = {}
    for s in symbols:
        try:
            f = fetch_funding(s)
        except Exception:
            f = None
        d = funding_to_daily_carry(f) if f is not None else pd.Series(dtype=float)
        if len(d) >= 300:
            dailies[s] = d
    if not dailies:
        lines.append("Insufficient funding data (need ≥300 daily points for any coin).")
        return "\n".join(lines)

    basket = pd.concat(dailies.values(), axis=1).mean(axis=1).dropna()
    g = _annual_stats(basket)
    lines.append(f"Basket of {len(dailies)} coins ({', '.join(dailies)}). "
                 f"Gross carry ≈ {g[0]:.1%}/yr, vol ≈ {g[1]:.1%}/yr, "
                 f"gross Sharpe ≈ {g[0]/g[1]:.1f}.")
    lines.append("")
    lines.append("| Fee tier | Rotation | Exec drag | Rehedge drag | Net return/yr | "
                 "Net Sharpe | Capital for target |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|")

    any_positive = False
    for tier, fee in FEE_TIERS.items():
        for rot in rotation_grid:
            m = net_carry_model(basket, spot_vol_annual, rot, fee,
                                rehedge_turnover_per_vol)
            if m.get("insufficient"):
                continue
            cap = (target_annual / m["net_ann"]) if m["net_ann"] > 0 else float("inf")
            cap_s = f"{cap:,.0f} CHF" if np.isfinite(cap) else "∞ (net ≤ 0)"
            if m["net_ann"] > 0:
                any_positive = True
            lines.append(
                f"| {tier} | {rot}d | {m['exec_drag']:.1%} | {m['rehedge_drag']:.1%} | "
                f"{m['net_ann']:+.1%} | {m['net_sharpe']:.1f} | {cap_s} |")
    lines.append("")

    lines.append("---")
    lines.append(
        "**Summary:** " + (
            "net carry stays positive under some cost settings — a real but modest, "
            "capital-hungry return; compare it honestly against ~4-5% risk-free cash "
            "for the operational and counterparty risk taken on."
            if any_positive else
            "net carry is ≤ 0 under realistic costs — the gross edge does not survive "
            "execution, matching #24's cost-fragility."))
    return "\n".join(lines)
