"""
Experiment #99 — the Buffett indicator (stock-market value / GDP): does it predict returns, and can
one time the market with it? (requested 21.11.2026 after an article quoting it; companion to the
CAPE test #34.)

Data (pre-registered):
  Market value  FRED NCBEILQ027S — nonfinancial corporate business, corporate equities (Fed Z.1,
                quarterly, $ millions, 1945 →). The usual long-history Buffett proxy.
  GDP           FRED GDP (quarterly, $ billions SAAR, 1947 →).
  Returns       Shiller S&P 500 real total return (monthly) and a 10-year bond proxy (#34 helpers).
  Buffett indicator BI = equities / (GDP × 1000) × 100 (%). Point-in-time: a quarter's value is used
  only from the 3rd month after the quarter end (Z.1 appears ≈ 10 weeks later). Latest data vintage
  (revisions not removed — caveat).
Tests:
  1 Quintiles of BI → next 1 / 3 / 10-year real annualised S&P return; correlation and t on
    NON-overlapping windows (1 y, 10 y). Same for CAPE over the same months (head-to-head).
  2 Variant 'relative BI' = BI / its own trailing 20-year average (removes the structural rise
    from globalisation, margins and lower rates).
  3 Timing rules (monthly, real, no costs — costs only make timing worse):
      T1 100 % stocks while BI's causal percentile (vs all PAST months) < 80 %, else 50 % stocks / 50 % bonds
      T2 same with relative BI
    vs 100 % stocks and vs a static mix with the same average stock share.
  4 Share of months with BI > 100 % ('overvalued' by the usual rule) before / after 1995; latest value.
Pure, injected for CI.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .experiments_34 import real_stock_returns, real_bond_returns, forward_annualised, expanding_pct_rank, corr_t, mstats

LAG_MONTHS = 3


def buffett_monthly(equities: pd.Series, gdp: pd.Series, lag: int = LAG_MONTHS) -> pd.Series:
    """Quarterly equities ($ mn) and GDP ($ bn) → monthly BI (%) available from quarter end + lag months."""
    e = equities.dropna().astype(float)
    g = gdp.dropna().astype(float)
    if e.empty or g.empty:
        return pd.Series(dtype=float)
    if g.median() > 1e5:   # BEA tables (DBnomics) are in $ millions, FRED GDP in $ billions
        g = g / 1000.0
    e.index = pd.PeriodIndex(pd.DatetimeIndex(e.index), freq="Q")
    g.index = pd.PeriodIndex(pd.DatetimeIndex(g.index), freq="Q")
    bi = (e / (g * 1000.0) * 100.0).dropna()
    if bi.empty:
        return pd.Series(dtype=float)
    avail = {q.asfreq("M", how="end") + lag: v for q, v in bi.items()}
    s = pd.Series(avail).sort_index()
    full = pd.period_range(s.index.min(), s.index.max() + 2, freq="M")
    return s.reindex(full).ffill()


def relative(x: pd.Series, months: int = 240) -> pd.Series:
    return x / x.rolling(months, min_periods=months // 2).mean()


def _monthly(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d.index = pd.DatetimeIndex(d.index).to_period("M")
    return d.groupby(level=0).last()


def quintile_table(sig: pd.Series, fwd: dict) -> list:
    d = pd.concat([sig.rename("s")] + [v.rename(k) for k, v in fwd.items()], axis=1).dropna(subset=["s"])
    d = d[d[list(fwd)].notna().any(axis=1)]
    if len(d) < 50:
        return []
    d["q"] = pd.qcut(d["s"].rank(method="first"), 5, labels=False) + 1
    rows = []
    for q, g in d.groupby("q"):
        rows.append((int(q), g["s"].min(), g["s"].max(), len(g), *[g[k].mean() for k in fwd]))
    return rows


def nonoverlap_corr(sig: pd.Series, fwd: pd.Series, step: int) -> tuple:
    d = pd.concat([sig, fwd], axis=1).dropna()
    d = d.iloc[::step]
    return corr_t(d.iloc[:, 0], d.iloc[:, 1])


def timing(stock: pd.Series, bond: pd.Series, sig: pd.Series, cut: float = 0.8) -> tuple:
    """Stock weight 1.0 when causal percentile of sig < cut, else 0.5; decided on last month's value."""
    pct = expanding_pct_rank(sig, min_hist=120)
    w = pd.Series(np.where(pct.to_numpy() < cut, 1.0, 0.5), index=pct.index).where(pct.notna()).shift(1)
    d = pd.concat([stock.rename("s"), bond.rename("b"), w.rename("w")], axis=1).dropna()
    return d["w"] * d["s"] + (1 - d["w"]) * d["b"], d


def run_experiment99_report(shiller: pd.DataFrame, equities: pd.Series, gdp: pd.Series, diag: list | None = None) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #99 — Buffett indicator (market value / GDP) ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    pc = lambda x: f"{100*x:+.1f} %" if np.isfinite(x) else "—"
    f = lambda x, d=2: f"{x:+.{d}f}" if np.isfinite(x) else "—"
    bi = buffett_monthly(equities, gdp)
    if bi.empty:
        return "\n".join(L + ["No Buffett-indicator data."])
    sh = _monthly(shiller)
    stock = real_stock_returns(sh)
    bond = real_bond_returns(sh)
    cape = sh["cape"]
    fwd = {"1 y": forward_annualised(stock, 12), "3 y": forward_annualised(stock, 36), "10 y": forward_annualised(stock, 120)}
    rel = relative(bi)
    last = bi.dropna()
    L.append(f"Buffett indicator {last.index[0]}–{last.index[-1]} (monthly, available 3 months after each quarter). "
             f"**Latest: {last.iloc[-1]:.0f} %** (quarter ending ≈ {last.index[-1] - LAG_MONTHS}); "
             f"its 20-year average {bi.rolling(240).mean().dropna().iloc[-1]:.0f} %, highest ever {last.max():.0f} % ({last.idxmax()}).")
    pre = last[last.index < pd.Period("1995-01", "M")]
    post = last[last.index >= pd.Period("1995-01", "M")]
    L.append(f"Months above 100 % ('overvalued' by the usual rule): before 1995 {100*(pre > 100).mean():.0f} %, "
             f"since 1995 {100*(post > 100).mean():.0f} %. Shiller returns end {sh.index[-1]}.")
    L.append("")
    for name, sig in (("Buffett indicator (BI)", bi), ("relative BI (vs own 20-year average)", rel), ("CAPE (same months, for comparison)", cape.where(bi.reindex(cape.index).notna()))):
        L.append(f"## {name}: quintile → next real S&P return per year")
        L.append("| quintile | range | months | next 1 y | next 3 y | next 10 y |")
        L.append("|---|---|--:|--:|--:|--:|")
        for q, lo, hi, n, a, b, c in quintile_table(sig, fwd):
            L.append(f"| Q{q}{' (cheapest)' if q == 1 else ' (dearest)' if q == 5 else ''} | {lo:.2f}–{hi:.2f} | {n} | {pc(a)} | {pc(b)} | {pc(c)} |")
        r1 = nonoverlap_corr(sig, fwd["1 y"], 12)
        r10 = nonoverlap_corr(sig, fwd["10 y"], 120)
        r10b = nonoverlap_corr(sig, fwd["10 y"], 60)
        L.append(f"- correlation, non-overlapping: 1 y {f(r1[0])} (t {f(r1[1])}, n {r1[2]}); 10 y {f(r10[0])} (t {f(r10[1])}, n {r10[2]}); "
                 f"10 y every 5 y {f(r10b[0])} (t {f(r10b[1])}, n {r10b[2]}, half-overlapping)")
        L.append("")
    L.append("## Timing rules (real, monthly, no costs): 100 % stocks, or 50/50 stocks/bonds when the signal's causal percentile ≥ 80 %")
    L.append("| rule | months | real CAGR | max drawdown | Sharpe | avg stock share |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for nm, sig in (("T1 Buffett indicator", bi), ("T2 relative BI", rel)):
        r, d = timing(stock, bond, sig)
        m = mstats(r)
        L.append(f"| {nm} | {len(r)} | {pc(m['cagr'])} | {100*m['maxdd']:.0f} % | {f(m['sharpe'])} | {100*d['w'].mean():.0f} % |")
        st = d["w"].mean()
        mix = st * d["s"] + (1 - st) * d["b"]
        mm = mstats(mix)
        L.append(f"| static mix with the same {100*st:.0f} % stock share | {len(mix)} | {pc(mm['cagr'])} | {100*mm['maxdd']:.0f} % | {f(mm['sharpe'])} | {100*st:.0f} % |")
        ms = mstats(d["s"])
        L.append(f"| 100 % stocks (same months) | {len(d)} | {pc(ms['cagr'])} | {100*ms['maxdd']:.0f} % | {f(ms['sharpe'])} | 100 % |")
    L.append("")
    L.append("Reading: a valuation measure can be right about the next 10 years and still useless for timing — the "
             "question is whether rules based on it beat simply holding, or a fixed mix with the same risk.")
    L.append("Caveats: few independent 10-year windows (≈ 7 since 1951); latest-vintage Fed/GDP data (revised, not as "
             "known then); nonfinancial corporate equities only; Shiller returns may end before today.")
    return "\n".join(L)


EQUITY_SOURCES = (
    ("FRED NCBEILQ027S", "fred", "NCBEILQ027S"),
    ("DBnomics FED search 103164103", "dbnsearch", "FED?q=103164103"),
    ("DBnomics search 'nonfinancial corporate equities'", "dbnsearch", "FED?q=nonfinancial%20corporate%20business%20corporate%20equities%20liability"),
    ("Yahoo ^W5000 (Wilshire 5000 points ≈ $bn, proxy)", "w5000", "^W5000"),
)
GDP_SOURCES = (
    ("FRED GDP", "fred", "GDP"),
    ("DBnomics BEA NIPA-T10105 A191RC-Q", "dbn", "BEA/NIPA-T10105/A191RC-Q"),
)


def fetch_first(sources, log: list, timeout: int = 90) -> pd.Series:
    """Try each source in turn; returns the first non-empty quarterly Series and logs every attempt."""
    from .experiments_46 import fetch_fred, parse_dbnomics_json, _get
    for name, kind, sid in sources:
        try:
            if kind == "fred":
                errs = {}
                s = fetch_fred(sid, timeout=timeout, errors=errs)
                if errs:
                    raise RuntimeError(list(errs.values())[0])
            elif kind == "dbn":
                s = parse_dbnomics_json(_get(f"https://api.db.nomics.world/v22/series/{sid}?observations=1", timeout=timeout))
            elif kind == "dbnsearch":
                import json
                docs = json.loads(_get(f"https://api.db.nomics.world/v22/series/{sid}&observations=1&limit=20", timeout=timeout))["series"]["docs"]
                # keep quarterly level series whose name mentions corporate equities (market value)
                docs = [d for d in docs if str(d.get("series_code", "")).endswith(".Q")
                        and "equit" in str(d.get("series_name", "")).lower() and "nonfinancial corporate" in str(d.get("series_name", "")).lower()
                        and "transaction" not in str(d.get("series_name", "")).lower()]
                if not docs:
                    raise RuntimeError("no matching series")
                d = docs[0]
                name = f"{name} → {d.get('dataset_code')}/{d.get('series_code')} ({str(d.get('series_name'))[:70]})"
                s = parse_dbnomics_json(json.dumps({"series": {"docs": [d]}}))
            else:   # Wilshire 5000 full-cap index: points ≈ total US market value in $ bn → $ mn
                from .experiments_35 import fetch_yahoo_daily
                px = fetch_yahoo_daily(sid, "1970-01-01", timeout=timeout)
                if px is None or not len(px):
                    raise RuntimeError("no Yahoo data")
                idx = px.index.tz_localize(None) if getattr(px.index, "tz", None) is not None else px.index
                px = pd.Series(px.to_numpy(dtype=float), index=idx)
                q = px.groupby(px.index.to_period("Q")).last()
                s = pd.Series(q.to_numpy() * 1000.0, index=q.index.to_timestamp(how="start"))
            s = s.dropna()
            if len(s) > 100:
                log.append(f"{name}: {len(s)} values {s.index[0]:%Y}–{s.index[-1]:%Y}")
                return s
            log.append(f"{name}: only {len(s)} values")
        except Exception as e:
            log.append(f"{name}: {repr(e)[:80]}")
    return pd.Series(dtype=float)
