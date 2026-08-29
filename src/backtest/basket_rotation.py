"""
Small-basket rotation edge test — e.g. Bitcoin / Gold / Dollar.

The hypothesis: a tiny, deliberately chosen basket representing different monetary
regimes (risk-on = BTC, fear = gold, cash-strength = dollar) can be rotated to
own whatever is winning and step aside into the dollar when risk assets weaken.

IMPORTANT: fewer assets does NOT create an edge — it RAISES overfitting risk
(fewer independent bets, easier to fit the one path history took). So the honest
bar is high: the rotation must beat every single-asset hold AND equal-weight hold
on MAR (return/|maxDD|), out-of-sample AND across walk-forward windows.

Two a-priori rules, no tuning:
  - top1: monthly, hold the single strongest by trailing `lookback` return.
  - dual: hold the stronger risk asset only if it beats the cash/dollar leg,
          else hold the dollar (defensive absolute-momentum, Antonacci-style).
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .trend_follow import _curve_stats
from .xsec_momentum import _price_panel
from .oos_runner import split_is_oos


def rotation_returns(panel: pd.DataFrame, *, mode: str, cash_col: str | None,
                     lookback: int = 63, hold: int = 21,
                     commission_pct: float = 0.05, slippage_pct: float = 0.03) -> pd.Series:
    """Daily net returns of a monthly basket rotation. `panel` columns are asset
    closes; `cash_col` names the defensive (dollar) leg for mode='dual'."""
    n_days, n_assets = panel.shape
    if n_days < lookback + hold + 5 or n_assets < 2:
        return pd.Series(dtype=float)
    cols = list(panel.columns)
    ret = panel.pct_change().fillna(0).to_numpy()
    px = panel.to_numpy()
    cost = (commission_pct + slippage_pct) / 100
    cash_idx = cols.index(cash_col) if cash_col in cols else None

    weights = np.zeros(n_assets)
    strat = np.zeros(n_days)
    start = lookback
    for i in range(n_days):
        if i >= start and (i - start) % hold == 0:
            score = px[i] / px[i - lookback] - 1
            new_w = np.zeros(n_assets)
            if mode == "top1":
                new_w[int(np.argmax(score))] = 1.0
            else:  # dual: best risk asset vs cash threshold
                risk = [j for j in range(n_assets) if j != cash_idx]
                best = max(risk, key=lambda j: score[j])
                thresh = score[cash_idx] if cash_idx is not None else 0.0
                pick = best if score[best] > thresh else (cash_idx if cash_idx is not None else best)
                new_w[pick] = 1.0
            strat[i] -= np.abs(new_w - weights).sum() * cost
            weights = new_w
        strat[i] += float((weights * ret[i]).sum())
    return pd.Series(strat, index=panel.index)


def _pct(returns: pd.Series) -> pd.Series:
    return returns


def run_rotation_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    baskets: dict[str, dict],
    limit: int = 2500,
    lookback: int = 63,
    hold: int = 21,
    window: int = 252,
    step: int = 63,
    commission_pct: float = 0.05,
    slippage_pct: float = 0.03,
) -> str:
    """For each basket: rotation (top1 & dual) vs every single-asset hold and
    equal-weight hold, on MAR, OOS + walk-forward."""
    from datetime import datetime, timezone

    p = dict(commission_pct=commission_pct, slippage_pct=slippage_pct)
    lines = [f"# Basket Rotation Edge Test — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    lines.append("Monthly rotation of a tiny basket vs holding each asset alone and equal-weight. "
                 "Net of costs. MAR = return/|maxDD|. The rotation must beat EVERY hold on MAR, "
                 "out-of-sample AND in most walk-forward windows, to count as an edge.")
    lines.append("")

    for name, spec in baskets.items():
        symbols = spec["symbols"]
        cash = spec.get("cash")
        data: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            try:
                d = get_ohlcv(sym, "1Day", limit)
                if d is not None and len(d) >= 400:
                    data[sym] = d
            except Exception as e:
                logger.warning(f"Rotation: could not fetch {sym}: {e}")
        lines.append(f"## {name}")
        if len(data) < 2:
            lines.append(f"_only {len(data)} symbols with data — skipped_\n")
            continue
        panel = _price_panel(data)
        lines.append(f"{panel.shape[1]} assets: {', '.join(panel.columns)} · common window "
                     f"{panel.index[0]:%Y-%m} → {panel.index[-1]:%Y-%m} ({len(panel)} days)")
        lines.append("")

        _, oos = split_is_oos(panel)
        # candidate strategies + benchmarks on the OOS window
        strat_rows: list[tuple[str, pd.Series]] = []
        strat_rows.append(("Rotation top1", rotation_returns(oos, mode="top1", cash_col=cash,
                                                             lookback=lookback, hold=hold, **p)))
        strat_rows.append(("Rotation dual", rotation_returns(oos, mode="dual", cash_col=cash,
                                                             lookback=lookback, hold=hold, **p)))
        for col in panel.columns:
            strat_rows.append((f"Hold {col}", oos[col].pct_change().fillna(0)))
        strat_rows.append(("Hold equal-weight", oos.pct_change().fillna(0).mean(axis=1)))

        stats = [(lbl, _curve_stats(s)) for lbl, s in strat_rows]
        best_hold_mar = max(st["mar"] for lbl, st in stats if lbl.startswith("Hold"))

        lines.append("| Strategy | OOS ret% | OOS maxDD% | OOS MAR | beats all holds? |")
        lines.append("|---|--:|--:|--:|:--:|")
        for lbl, st in stats:
            flag = ""
            if lbl.startswith("Rotation"):
                flag = "✅" if (st["mar"] > best_hold_mar and st["ret"] > 0) else "—"
            lines.append(f"| {lbl} | {st['ret']:+.0f} | {st['dd']:.0f} | {st['mar']} | {flag} |")
        lines.append("")

        # walk-forward: rotation MAR vs the best single/EW hold MAR, per window
        holds = {col: panel[col].pct_change().fillna(0) for col in panel.columns}
        holds["EW"] = panel.pct_change().fillna(0).mean(axis=1)
        for mode in ("top1", "dual"):
            rot = rotation_returns(panel, mode=mode, cash_col=cash, lookback=lookback, hold=hold, **p)
            common = rot.index
            rows, i = [], 0
            while i + window <= len(common):
                sl = slice(i, i + window)
                rmar = _curve_stats(rot.iloc[sl])
                hold_mars = [_curve_stats(h.loc[common].iloc[sl])["mar"] for h in holds.values()]
                beat = rmar["mar"] > max(hold_mars) and rmar["ret"] > 0
                rows.append(beat)
                i += step
            if rows:
                nb, n = sum(rows), len(rows)
                pct = round(100 * nb / n)
                verdict = ("✅ robust edge" if pct >= 60 else
                           "⚠️ regime-dependent" if pct >= 40 else "❌ not robust")
                lines.append(f"**Walk-forward {mode}:** beat all holds in **{nb}/{n} windows ({pct}%)** → {verdict}")
        lines.append("")

    lines.append("A rotation that doesn't beat simply holding the best single asset on MAR "
                 "isn't an edge — it's a more complicated way to underperform.")
    return "\n".join(lines)
