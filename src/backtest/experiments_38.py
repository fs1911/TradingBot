"""
Experiment #38 — combining a risk premium with crash insurance.

#37: the volatility risk premium (PutWrite) is real and persistent but carries a crash
tail (negative skew, −18% in Oct 2008). #32/#33/#35: the 200d trend filter does not
raise returns but reliably cuts crash drawdowns. Their crash profiles are opposite,
so the question is whether combining them is more than the sum:

  S&P 500 TR buy & hold                      (benchmark)
  PutWrite buy & hold                        (premium alone)
  PutWrite + trend filter (daily / monthly)  (harvest only while S&P is above SMA200)
  S&P 500 TR + trend filter                  (insurance alone)
  50/50 PutWrite + S&P TR                    (mix without filter — isolates mixing)
  50/50 PutWrite + trend-filtered S&P TR     (opposite crash profiles combined)

Daily data from ^PUT's start (1996), cash earns the 13-week T-bill (^IRX), 5 bps per
trend switch, 50/50 mixes rebalanced daily. Reported: CAGR, vol, Sharpe, max DD,
monthly skew/worst month, returns in the 2000–02, 2008–09, 2020 and 2022 crises, and
full rigor on the key differentials. Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .rigor import full_rigor
from .experiments_32 import perf
from .experiments_33 import cash_daily_returns, trend_position

CRISES = (("2000–02 dot-com", "2000-03-24", "2002-10-09"),
          ("2008–09 GFC", "2007-10-09", "2009-03-09"),
          ("2020 Covid", "2020-02-19", "2020-03-23"),
          ("2022 bear", "2022-01-03", "2022-10-12"))


def _naive(s: pd.Series) -> pd.Series:
    s = pd.Series(s).astype(float).dropna().sort_index()
    idx = pd.to_datetime(s.index)
    idx = idx.tz_localize(None) if idx.tz is not None else idx
    s.index = idx.normalize()
    return s[~s.index.duplicated(keep="last")]


def build_strategies(put: pd.Series, sptr: pd.Series, irx: pd.Series,
                     cost_bps: float = 5.0) -> pd.DataFrame:
    """Daily returns of all strategies on the common PUT/SP index (after SMA warm-up)."""
    put, sptr = _naive(put), _naive(sptr)
    idx = put.index.intersection(sptr.index)
    put, sptr = put.loc[idx], sptr.loc[idx]
    cash = cash_daily_returns(_naive(irx) if irx is not None and len(irx) else irx, idx)
    r_put, r_sp = put.pct_change().fillna(0.0), sptr.pct_change().fillna(0.0)

    def filtered(r: pd.Series, monthly: bool) -> pd.Series:
        pos = trend_position(sptr, 200, monthly)
        return r * pos + cash * (1 - pos) - pos.diff().abs().fillna(0.0) * cost_bps / 1e4

    sp_tf = filtered(r_sp, False)
    df = pd.DataFrame({
        "S&P 500 TR": r_sp,
        "PutWrite": r_put,
        "PutWrite + trend (daily)": filtered(r_put, False),
        "PutWrite + trend (monthly)": filtered(r_put, True),
        "S&P 500 TR + trend": sp_tf,
        "50/50 PutWrite + S&P": 0.5 * r_put + 0.5 * r_sp,
        "50/50 PutWrite + trend-S&P": 0.5 * r_put + 0.5 * sp_tf,
    })
    return df.iloc[200:]


def monthly_shape(r: pd.Series) -> tuple:
    m = (1 + r).groupby(r.index.to_period("M")).prod() - 1
    return float(m.skew()), float(m.min()), m.idxmin()


def crisis_return(r: pd.Series, a: str, b: str) -> float:
    seg = r.loc[a:b]
    return float((1 + seg).prod() - 1) if len(seg) > 5 else float("nan")


def run_experiment38_report(series: dict, n_trials: int = 150) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #38 — volatility premium + trend insurance combined "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    put, sptr, irx = series.get("PUT"), series.get("SP500TR"), series.get("IRX")
    if put is None or len(put) < 1500 or sptr is None or len(sptr) < 1500:
        lines.append("**Missing data** — need ^PUT and ^SP500TR daily history.")
        return "\n".join(lines)
    df = build_strategies(put, sptr, irx if irx is not None else pd.Series(dtype=float))
    lines.append(f"Daily, {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d} ({len(df)} days). "
                 f"Cash = 13-week T-bill "
                 f"{'(^IRX)' if irx is not None and len(irx) > 1000 else '(MISSING → 0%)'}; "
                 f"5 bps per trend switch; 50/50 rebalanced daily.")
    lines.append("")

    lines.append("## Overall")
    lines.append("| Strategy | CAGR | vol | Sharpe | max DD | monthly skew | worst month |")
    lines.append("|---|--:|--:|--:|--:|--:|---|")
    stats = {}
    for c in df.columns:
        p = perf(df[c])
        vol = float(df[c].std() * math.sqrt(252))
        sk, wm, wd = monthly_shape(df[c])
        stats[c] = p
        lines.append(f"| {c} | {100*p['cagr']:+.1f}% | {100*vol:.1f}% | {p['sharpe']:.2f} | "
                     f"{100*p['maxdd']:.0f}% | {sk:+.2f} | {100*wm:+.0f}% ({wd}) |")
    lines.append("")

    lines.append("## Crises (total return over the window)")
    lines.append("| Strategy | " + " | ".join(c[0] for c in CRISES) + " |")
    lines.append("|---|" + "--:|" * len(CRISES))
    for c in df.columns:
        vals = [crisis_return(df[c], a, b) for _, a, b in CRISES]
        lines.append(f"| {c} | " + " | ".join("—" if v != v else f"{100*v:+.0f}%" for v in vals) + " |")
    lines.append("")

    lines.append("## Rigor on the key differentials (daily, α/%d)" % n_trials)
    lines.append("| Differential | OOS ret% | Sharpe | p | sig | walk-fwd | regimes+ | verdict |")
    lines.append("|---|--:|--:|--:|:--:|--:|:--:|---|")
    pairs = (("PutWrite + trend (daily)", "PutWrite"),
             ("PutWrite + trend (daily)", "S&P 500 TR"),
             ("50/50 PutWrite + trend-S&P", "S&P 500 TR"),
             ("50/50 PutWrite + trend-S&P", "50/50 PutWrite + S&P"))
    verdicts = []
    for a, b in pairs:
        res = full_rigor(f"{a} − {b}", df[a] - df[b], n_trials)
        verdicts.append((a, b, res))
        if res.get("verdict") == "insufficient data":
            lines.append(f"| {a} − {b} | insufficient | | | | | | |")
            continue
        v = res["verdict"]
        lines.append(f"| {a} − {b} | {res['oos_ret']:+.0f} | {res['sharpe']} | {res['p_value']} | "
                     f"{'✅' if res['sig_after_haircut'] else '❌'} | {res['wf_pct']}% | "
                     f"{res['regime_positive']} | {'✅' if v.startswith('✅') else '⚠️' if v.startswith('⚠') else '❌'} |")
    lines.append("")

    best = max(stats, key=lambda k: stats[k]["sharpe"])
    sp = stats["S&P 500 TR"]
    lines.append("---")
    lines.append(
        f"**Summary:** best Sharpe: {best} ({stats[best]['sharpe']:.2f}, CAGR "
        f"{100*stats[best]['cagr']:+.1f}%, max DD {100*stats[best]['maxdd']:.0f}%) vs S&P 500 TR "
        f"({sp['sharpe']:.2f}, {100*sp['cagr']:+.1f}%, {100*sp['maxdd']:.0f}%). Differentials passing "
        f"full rigor: {sum(1 for *_, r in verdicts if r.get('verdict','').startswith('✅'))}/{len(verdicts)}.")
    return "\n".join(lines)
