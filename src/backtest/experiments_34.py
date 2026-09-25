"""
Experiment #34 — valuation instead of price: the Shiller CAPE over ~150 years.

All 33 earlier experiments used prices only. This is the first test of a
FUNDAMENTAL valuation signal: the cyclically-adjusted P/E (CAPE / PE10 = price over
the 10-year average of inflation-adjusted earnings). Data: Shiller's monthly US
series since 1871 (price, dividend, CPI, 10y yield, PE10). Everything is in REAL
terms with dividends reinvested.

Three questions:
  1. PREDICTIVE: does a high CAPE predict lower real returns over 1, 3 and 10 years?
     Quintile table, correlation on NON-overlapping windows (honest n), and whether the
     relationship holds in both halves of history (pre/post 1950).
  2. CONDITIONAL INSURANCE: does the 10-month trend filter (stocks ↔ 10y bonds) help
     more when CAPE is high? (#33 showed the filter only pays in long bear markets.)
  3. ALLOCATION: static 100% stocks, static 60/40, CAPE-scaled equity weight, plain
     trend filter, and a CAPE-gated trend filter (filter only when CAPE is in its top
     third) — real CAGR, Sharpe, max drawdown, and a block-bootstrap significance test
     of each rule against 100% stocks with a multiple-testing haircut.

CAPE ranks are EXPANDING (only past data) and lagged one month. Bond returns are
approximated from the 10y yield (carry + duration × yield change, duration 7).
Shiller prices are monthly averages, which slightly smooths volatility. Pure/causal,
injected for CI; the bot downloads the CSV with a hard timeout.
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd

from .rigor import block_bootstrap_pvalue, deflated_ok

SOURCES = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv",
    "https://raw.githubusercontent.com/datasets/s-and-p-500/master/data/data.csv",
    "https://datahub.io/core/s-and-p-500/r/data.csv",
)


# ---------------------------------------------------------------- data

def parse_shiller_csv(text: str) -> pd.DataFrame:
    """datasets/s-and-p-500 CSV → DataFrame[price, div, cpi, gs10, cape] (monthly)."""
    import io
    try:
        raw = pd.read_csv(io.StringIO(text))
    except Exception:
        return pd.DataFrame()
    cols = {c.lower().strip(): c for c in raw.columns}
    need = {"date": "date", "sp500": "price", "dividend": "div",
            "consumer price index": "cpi", "long interest rate": "gs10", "pe10": "cape"}
    if not all(k in cols for k in need):
        return pd.DataFrame()
    df = pd.DataFrame({v: pd.to_numeric(raw[cols[k]], errors="coerce") if v != "date"
                       else pd.to_datetime(raw[cols[k]], errors="coerce")
                       for k, v in need.items()})
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    df = df.replace(0.0, np.nan)
    return df


def fetch_shiller(timeout: int = 20):
    """Download the Shiller monthly dataset; returns (DataFrame, source_url)."""
    import urllib.request
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                df = parse_shiller_csv(r.read().decode("utf-8", "replace"))
            if len(df) > 1000:
                return df, url
        except Exception:
            continue
    return pd.DataFrame(), "none"


# ---------------------------------------------------------------- building blocks

def real_stock_returns(df: pd.DataFrame) -> pd.Series:
    """Monthly real total return: (P_t + D_t/12)/P_{t-1} − 1, deflated by CPI."""
    nominal = (df["price"] + df["div"].fillna(0.0) / 12.0) / df["price"].shift(1) - 1.0
    infl = df["cpi"] / df["cpi"].shift(1)
    return ((1.0 + nominal) / infl - 1.0).rename("stock")


def real_bond_returns(df: pd.DataFrame, duration: float = 7.0) -> pd.Series:
    """10y bond approximated from its yield: carry − duration × Δyield, deflated."""
    y = df["gs10"] / 100.0
    nominal = y.shift(1) / 12.0 - duration * (y - y.shift(1))
    infl = df["cpi"] / df["cpi"].shift(1)
    return ((1.0 + nominal) / infl - 1.0).rename("bond")


def forward_annualised(r: pd.Series, months: int) -> pd.Series:
    """Annualised compound return over the NEXT `months` months (t+1 … t+months)."""
    growth = np.log1p(r).rolling(months).sum().shift(-months)
    return np.expm1(growth * 12.0 / months)


def expanding_pct_rank(x: pd.Series, min_hist: int = 120) -> pd.Series:
    """Percentile of the current value among all PAST values (causal)."""
    vals = x.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    for i in range(min_hist, len(vals)):
        past = vals[:i]
        past = past[~np.isnan(past)]
        if len(past) >= min_hist and not np.isnan(vals[i]):
            out[i] = float((past < vals[i]).mean())
    return pd.Series(out, index=x.index)


def corr_t(a: pd.Series, b: pd.Series):
    d = pd.concat([a, b], axis=1).dropna()
    if len(d) < 5:
        return float("nan"), float("nan"), len(d)
    r = float(np.corrcoef(d.iloc[:, 0], d.iloc[:, 1])[0, 1])
    t = r * np.sqrt((len(d) - 2) / max(1e-12, 1 - r * r))
    return r, float(t), len(d)


def mstats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 24:
        return {"cagr": float("nan"), "sharpe": float("nan"), "maxdd": float("nan")}
    eq = (1.0 + r).cumprod()
    return {"cagr": float(eq.iloc[-1] ** (12.0 / len(r)) - 1.0),
            "sharpe": float(r.mean() / r.std() * np.sqrt(12)) if r.std() > 0 else 0.0,
            "maxdd": float((eq / eq.cummax() - 1.0).min())}


def trend_position(stock: pd.Series, months: int = 10) -> pd.Series:
    """1 if last month's real total-return index was above its `months` SMA."""
    level = (1.0 + stock.fillna(0.0)).cumprod()
    return (level > level.rolling(months).mean()).astype(float).shift(1)


# ---------------------------------------------------------------- report

def run_experiment34_report(df: pd.DataFrame, source: str = "", n_trials: int = 120) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #34 — Shiller CAPE over ~150 years "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if df is None or len(df) < 1000:
        lines.append("**No Shiller data could be loaded** (all sources failed) — nothing "
                     "to test.")
        return "\n".join(lines)

    stock = real_stock_returns(df)
    bond = real_bond_returns(df)
    cape = df["cape"]
    valid = pd.concat([stock, bond, cape], axis=1).dropna().index
    lines.append(f"Source: {source}. Months with price/CPI: {df['price'].notna().sum()}, "
                 f"with CAPE: {cape.notna().sum()} ({cape.first_valid_index():%Y-%m} → "
                 f"{cape.last_valid_index():%Y-%m}). All returns REAL (after inflation), "
                 f"dividends reinvested.")
    lines.append("")

    # 1. predictive
    lines.append("## 1 — Does high CAPE predict lower real returns?")
    lines.append("| Horizon | cheapest-quintile fwd | dearest-quintile fwd | corr (non-overl.) | "
                 "t | n | corr pre-1950 / post-1950 |")
    lines.append("|---|--:|--:|--:|--:|--:|---|")
    pred = {}
    for h in (12, 36, 120):
        fwd = forward_annualised(stock, h)
        d = pd.concat({"cape": cape, "fwd": fwd}, axis=1).dropna()
        if len(d) < 200:
            continue
        q = pd.qcut(d["cape"], 5, labels=False, duplicates="drop")
        by = d.groupby(q)["fwd"].mean()
        nov = d.iloc[::h]
        r, t, n = corr_t(nov["cape"], nov["fwd"])
        pre = d[d.index < "1950-01-01"].iloc[::h]
        post = d[d.index >= "1950-01-01"].iloc[::h]
        r1, _, _ = corr_t(pre["cape"], pre["fwd"])
        r2, _, _ = corr_t(post["cape"], post["fwd"])
        pred[h] = (r, t, r1, r2)
        lines.append(f"| {h//12}y | {100*by.iloc[0]:+.1f}%/y | {100*by.iloc[-1]:+.1f}%/y | "
                     f"{r:+.2f} | {t:+.2f} | {n} | {r1:+.2f} / {r2:+.2f} |")
    lines.append("")

    # 2. conditional insurance
    pct = expanding_pct_rank(cape).shift(1)
    pos = trend_position(stock)
    trend = pos * stock + (1 - pos) * bond
    diff = (trend - stock)
    d2 = pd.concat({"pct": pct, "diff": diff}, axis=1).dropna()
    hi, lo = d2[d2["pct"] >= 2 / 3]["diff"], d2[d2["pct"] < 2 / 3]["diff"]
    lines.append("## 2 — Does the 10-month trend filter help more when CAPE is high?")
    lines.append("| CAPE regime (causal, top third vs rest) | months | trend − stocks, %/y | t |")
    lines.append("|---|--:|--:|--:|")
    for name, s in (("CAPE high (top third)", hi), ("CAPE normal/low", lo)):
        t = s.mean() / (s.std() / np.sqrt(len(s))) if len(s) > 2 and s.std() > 0 else float("nan")
        lines.append(f"| {name} | {len(s)} | {100*12*s.mean():+.2f} | {t:+.2f} |")
    lines.append("")

    # 3. allocation rules
    w_cape = (1.0 - 0.7 * pct).clip(0.3, 1.0)
    gated = pos.where(pct >= 2 / 3, 1.0)
    rules = {
        "100% stocks": stock,
        "60/40 stocks/bonds": 0.6 * stock + 0.4 * bond,
        "CAPE-scaled (30–100% stocks)": w_cape * stock + (1 - w_cape) * bond,
        "Trend filter (10m SMA)": trend,
        "CAPE-gated trend (filter only if CAPE top third)": gated * stock + (1 - gated) * bond,
    }
    start = pd.concat([pct, pos], axis=1).dropna().index.min()
    lines.append(f"## 3 — Allocation rules (real, from {start:%Y-%m})")
    lines.append("| Rule | real CAGR | Sharpe | max DD | vs 100% stocks: p | sig after haircut | "
                 "better in both halves |")
    lines.append("|---|--:|--:|--:|--:|:--:|:--:|")
    base = stock.loc[start:]
    mid = base.index[len(base) // 2]
    results = {}
    for name, r in rules.items():
        r = r.loc[start:].dropna()
        st = mstats(r)
        if name == "100% stocks":
            lines.append(f"| {name} | {100*st['cagr']:+.2f}% | {st['sharpe']:.2f} | "
                         f"{100*st['maxdd']:.0f}% | — | — | — |")
            continue
        d = (r - base.reindex(r.index)).dropna()
        p = block_bootstrap_pvalue(d, block=12)
        sig = deflated_ok(p, n_trials)
        halves = bool(d.loc[:mid].mean() > 0 and d.loc[mid:].mean() > 0)
        results[name] = (st, p, sig, halves)
        lines.append(f"| {name} | {100*st['cagr']:+.2f}% | {st['sharpe']:.2f} | "
                     f"{100*st['maxdd']:.0f}% | {p:.3f} | {'✅' if sig else '❌'} | "
                     f"{'✅' if halves else '❌'} |")
    lines.append("")

    lines.append("---")
    s10 = pred.get(120)
    s1 = pred.get(12)
    lines.append(
        "**Summary:** " +
        (f"10y: corr {s10[0]:+.2f} (t {s10[1]:+.1f}), pre/post-1950 {s10[2]:+.2f}/{s10[3]:+.2f}. "
         if s10 else "") +
        (f"1y: corr {s1[0]:+.2f} (t {s1[1]:+.1f}). " if s1 else "") +
        f"Trend filter excess when CAPE high {100*12*hi.mean():+.2f}%/y vs otherwise "
        f"{100*12*lo.mean():+.2f}%/y. Allocation rules significant vs 100% stocks after "
        f"haircut: {sum(1 for v in results.values() if v[2])}/{len(results)}; "
        f"positive in both halves: {sum(1 for v in results.values() if v[3])}/{len(results)}.")
    return "\n".join(lines)
