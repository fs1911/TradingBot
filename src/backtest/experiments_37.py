"""
Experiment #37 — risk premia instead of anomalies: the volatility risk premium.

#36 showed published calendar anomalies vanish. Theory says RISK PREMIA should not:
they are payment for bearing a risk others want to shed. The classic example is the
volatility risk premium (VRP): option buyers systematically overpay for protection,
so implied volatility (VIX) tends to exceed the volatility that is later realised —
and sellers of that insurance earn a premium in exchange for crash exposure.

  1. EXISTENCE: VIX vs realised S&P 500 volatility over the next 21 trading days,
     on non-overlapping months since 1990. Before vs after publication (Bakshi &
     Kapadia 2003) and since 2018 (after the short-vol boom and its crash).
  2. HARVESTING: CBOE PutWrite (^PUT) and BuyWrite (^BXM) indices vs the S&P 500 total
     return index — CAGR, volatility, Sharpe, max drawdown, worst month, skew, and the
     ALPHA after regressing out equity beta (is it more than disguised equity risk?).
  3. A REAL PRODUCT: SVXY (short VIX-futures ETF) — the tail risk made visible.

Monthly returns use true month-end closes. Significance: Welch/OLS t with a Bonferroni
haircut over the project's trial count. Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_35 import month_end_closes

PUB_YEAR = 2003


def _naive_series(s: pd.Series) -> pd.Series:
    s = pd.Series(s).astype(float).dropna().sort_index()
    idx = pd.to_datetime(s.index)
    s.index = idx.tz_localize(None) if idx.tz is not None else idx
    return s[~s.index.duplicated(keep="last")]


def realized_forward_vol(close: pd.Series, n: int = 21) -> pd.Series:
    """Annualised realised vol of daily log returns over the NEXT n trading days."""
    lr = np.log(close).diff()
    return (lr.rolling(n).std() * math.sqrt(252)).shift(-n)


def t_to_p(t: float) -> float:
    return float(math.erfc(abs(t) / math.sqrt(2))) if t == t else float("nan")


def vrp_table(vix: pd.Series, spx: pd.Series, n: int = 21) -> dict:
    """VRP in vol points (VIX − realised) on non-overlapping n-day samples, by period."""
    vix, spx = _naive_series(vix), _naive_series(spx)
    rv = realized_forward_vol(spx, n)
    d = pd.concat({"vix": vix / 100.0, "rv": rv}, axis=1).dropna()
    d = d.iloc[::n]
    d["vrp"] = d["vix"] - d["rv"]
    periods = {"full": d, f"before {PUB_YEAR}": d[d.index < f"{PUB_YEAR}-01-01"],
               f"after {PUB_YEAR}": d[d.index >= f"{PUB_YEAR}-01-01"],
               "since 2018": d[d.index >= "2018-01-01"]}
    out = {}
    for k, x in periods.items():
        v = x["vrp"]
        if len(v) < 12:
            out[k] = None
            continue
        t = float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))) if v.std() > 0 else float("nan")
        worst = v.idxmin()
        out[k] = {"n": len(v), "mean_pts": 100 * v.mean(), "pct_pos": 100 * (v > 0).mean(),
                  "t": t, "worst_pts": 100 * v.min(), "worst_date": worst}
    return out


def monthly_returns(close: pd.Series) -> pd.Series:
    me = month_end_closes(_naive_series(close))
    return me.pct_change().dropna()


def alpha_beta(y: pd.Series, x: pd.Series) -> dict:
    d = pd.concat({"y": y, "x": x}, axis=1).dropna()
    if len(d) < 24:
        return {"alpha": float("nan"), "t": float("nan"), "beta": float("nan"), "n": len(d)}
    X = np.column_stack([np.ones(len(d)), d["x"].to_numpy()])
    coef, *_ = np.linalg.lstsq(X, d["y"].to_numpy(), rcond=None)
    resid = d["y"].to_numpy() - X @ coef
    s2 = resid.var(ddof=2)
    cov = s2 * np.linalg.inv(X.T @ X)
    t = float(coef[0] / math.sqrt(cov[0, 0])) if cov[0, 0] > 0 else float("nan")
    return {"alpha": float(coef[0]) * 12, "t": t, "beta": float(coef[1]), "n": len(d)}


def mstats(r: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    return {"cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1), "vol": float(r.std() * math.sqrt(12)),
            "sharpe": float(r.mean() / r.std() * math.sqrt(12)) if r.std() > 0 else float("nan"),
            "maxdd": float((eq / eq.cummax() - 1).min()), "worst": float(r.min()),
            "worst_date": r.idxmin(), "skew": float(r.skew())}


def run_experiment37_report(series: dict, n_trials: int = 140) -> str:
    """series: {'VIX','GSPC','SP500TR','PUT','BXM','SVXY'} → daily close Series (may be empty)."""
    from datetime import datetime, timezone

    lines = [f"# Experiment #37 — the volatility risk premium "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    have = {k: (v is not None and len(v) > 250) for k, v in series.items()}
    lines.append("Data: " + ", ".join(
        f"{k} {'✅ ' + format(_naive_series(v).index[0], '%Y') if have[k] else '❌'}"
        for k, v in series.items()) + ".")
    lines.append("")
    crit = 0.05 / n_trials

    # 1. existence
    if have.get("VIX") and have.get("GSPC"):
        tab = vrp_table(series["VIX"], series["GSPC"])
        lines.append("## 1 — Does implied volatility exceed later realised volatility?")
        lines.append("| Period | months | VIX − realised (vol pts) | % months positive | t | "
                     "worst month (pts, date) |")
        lines.append("|---|--:|--:|--:|--:|---|")
        for k, v in tab.items():
            if v is None:
                lines.append(f"| {k} | — | — | — | — | — |")
                continue
            lines.append(f"| {k} | {v['n']} | {v['mean_pts']:+.2f} | {v['pct_pos']:.0f}% | "
                         f"{v['t']:+.2f} | {v['worst_pts']:+.1f} ({v['worst_date']:%Y-%m}) |")
        lines.append("")
    else:
        tab = {}
        lines.append("## 1 — skipped (VIX or S&P daily data missing)")
        lines.append("")

    # 2/3. harvesting
    rows = []
    if have.get("SP500TR"):
        bench = monthly_returns(series["SP500TR"])
        lines.append("## 2 — Harvesting the premium vs S&P 500 total return (monthly, common period)")
        lines.append("| Series | from | CAGR | vol | Sharpe | max DD | worst month | skew | beta | "
                     "alpha/y | alpha t | sig after haircut |")
        lines.append("|---|---|--:|--:|--:|--:|---|--:|--:|--:|--:|:--:|")
        for key, label in (("PUT", "PutWrite (^PUT)"), ("BXM", "BuyWrite (^BXM)"),
                           ("SVXY", "SVXY short-vol ETF")):
            if not have.get(key):
                lines.append(f"| {label} | — | no data | | | | | | | | | |")
                continue
            y = monthly_returns(series[key])
            common = y.index.intersection(bench.index)
            y, x = y.loc[common], bench.loc[common]
            if len(common) < 24:
                lines.append(f"| {label} | — | too short | | | | | | | | | |")
                continue
            sy, sx = mstats(y), mstats(x)
            ab = alpha_beta(y, x)
            sig = t_to_p(ab["t"]) < crit and ab["alpha"] > 0
            rows.append((label, sy, sx, ab, sig))
            f = lambda s: (f"{100*s['cagr']:+.1f}% | {100*s['vol']:.1f}% | {s['sharpe']:.2f} | "
                           f"{100*s['maxdd']:.0f}% | {100*s['worst']:+.0f}% ({s['worst_date']}) | "
                           f"{s['skew']:+.2f}")
            lines.append(f"| {label} | {common[0]} | {f(sy)} | {ab['beta']:.2f} | "
                         f"{100*ab['alpha']:+.2f}% | {ab['t']:+.2f} | {'✅' if sig else '❌'} |")
            lines.append(f"| ↳ S&P 500 TR, same months | {common[0]} | {f(sx)} | 1.00 | — | — | — |")
        lines.append("")
    else:
        lines.append("## 2 — skipped (S&P 500 total-return data missing)")
        lines.append("")

    lines.append("---")
    parts = []
    if tab.get("full"):
        parts.append(f"VRP full {tab['full']['mean_pts']:+.1f} pts (t {tab['full']['t']:+.1f}, "
                     f"{tab['full']['pct_pos']:.0f}% of months positive)")
    for k in (f"after {PUB_YEAR}", "since 2018"):
        if tab.get(k):
            parts.append(f"{k} {tab[k]['mean_pts']:+.1f} pts (t {tab[k]['t']:+.1f})")
    b, a = tab.get(f"before {PUB_YEAR}"), tab.get(f"after {PUB_YEAR}")
    if b and a and b["mean_pts"]:
        parts.append(f"post-publication size {100*a['mean_pts']/b['mean_pts']:.0f}% of pre")
    if rows:
        parts.append("harvesting alpha significant after haircut: " +
                     ", ".join(f"{l} {'yes' if s else 'no'}" for l, _, _, _, s in rows))
    lines.append("**Summary:** " + "; ".join(parts) + ".")
    return "\n".join(lines)
