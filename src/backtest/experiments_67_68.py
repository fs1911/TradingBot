"""
Experiments #67 / #68 — a Swiss investor's currency questions.

#67 Currency hedging: US stocks (S&P 500 total return, VFINX) and German stocks (DAX,
    a total-return index) held by a CHF investor, unhedged vs hedged into CHF.
      unhedged: (1 + r_local) · FX_t / FX_{t−1} − 1
      hedged:   r_local + (r_CHF − r_foreign)/12   (covered interest parity; short rates
                approximated by central-bank policy rates, previous month)
    CAGR, volatility, max drawdown IN CHF, share of rolling 10-year windows in which
    hedging won, and how much of the return the currency took or gave.
#68 Home bias: Swiss stocks (SPI total return, ^SSHI) vs US stocks unhedged in CHF — mixes
    0 … 100 % Switzerland: return, volatility, Sharpe (vs CHF cash), max drawdown, and
    whether the best mix of the first half was also good in the second half.
Data: BIS via DBnomics (exchange rates since the 1950s, policy rates) with Yahoo fallbacks;
the report lists which source was used.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

DBN = "https://api.db.nomics.world/v22/series/{}?observations=1&format=json"
SERIES = {  # name → candidate DBnomics series ids
    "CHF per USD": ["BIS/WS_XRU/M.CH.CHF.A", "BIS/WS_XRU/M.CH.CHF.E"],
    "EUR per USD": ["BIS/WS_XRU/M.XM.EUR.A", "BIS/WS_XRU/M.XM.EUR.E"],
    "CH policy rate": ["BIS/WS_CBPOL/M.CH", "BIS/WS_CBPOL/D.CH"],
    "US policy rate": ["BIS/WS_CBPOL/M.US", "BIS/WS_CBPOL/D.US"],
    "EA policy rate": ["BIS/WS_CBPOL/M.XM", "BIS/WS_CBPOL/D.XM"],
}


def fetch_dbnomics(get, log=None) -> tuple:
    """→ ({name: monthly Series (Period index)}, {name: source})."""
    from .experiments_46 import parse_dbnomics_json
    out, src = {}, {}
    for name, ids in SERIES.items():
        for sid in ids:
            try:
                s = parse_dbnomics_json(get(DBN.format(sid)))
            except Exception as e:
                s = pd.Series(dtype=float)
                if log:
                    log(f"#67 {sid}: {repr(e)[:80]}")
            if len(s) > 100:
                m = s.groupby(s.index.to_period("M")).last()
                out[name], src[name] = m, f"DBnomics {sid}"
                break
    return out, src


def monthly(s: pd.Series) -> pd.Series:
    s = pd.Series(s).dropna().astype(float)
    idx = pd.to_datetime(s.index)
    s.index = (idx.tz_localize(None) if idx.tz is not None else idx).to_period("M")
    return s.groupby(level=0).last()


def unhedged(r_local: pd.Series, fx: pd.Series) -> pd.Series:
    """fx = CHF per unit of the foreign currency."""
    g = fx / fx.shift(1)
    return ((1 + r_local) * g.reindex(r_local.index) - 1).dropna()


def hedged(r_local: pd.Series, r_chf: pd.Series, r_for: pd.Series) -> pd.Series:
    diff = (r_chf - r_for).shift(1) / 100 / 12
    return (r_local + diff.reindex(r_local.index)).dropna()


def stats(r: pd.Series, cash: pd.Series | None = None) -> dict:
    r = r.dropna()
    if len(r) < 36:
        return {"n": len(r)}
    eq = (1 + r).cumprod()
    c = (cash.reindex(r.index).fillna(0) / 100 / 12) if cash is not None else 0.0
    ex = r - c
    return {"n": len(r), "cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1), "vol": float(r.std() * math.sqrt(12)),
            "dd": float((eq / eq.cummax() - 1).min()),
            "sharpe": float(ex.mean() / ex.std() * math.sqrt(12)) if ex.std() > 0 else float("nan")}


def rolling_win(a: pd.Series, b: pd.Series, months: int = 120) -> float:
    d = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
    ga = (1 + d["a"]).rolling(months).apply(np.prod, raw=True)
    gb = (1 + d["b"]).rolling(months).apply(np.prod, raw=True)
    ok = ga.notna()
    return float((ga[ok] > gb[ok]).mean()) if ok.any() else float("nan")


def _p(x):
    return "—" if x is None or not np.isfinite(x) else f"{100*x:+.1f} %"


def run_experiments67_68_report(macro: dict, src: dict, vfinx: pd.Series, dax: pd.Series, spi: pd.Series,
                                yahoo_fx: dict) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiments #67 / #68 — currency hedging and home bias for a CHF investor "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    chf_usd = macro.get("CHF per USD")
    if chf_usd is None and yahoo_fx.get("USDCHF") is not None:
        chf_usd, src["CHF per USD"] = monthly(yahoo_fx["USDCHF"]), "Yahoo CHF=X"
    eur_usd = macro.get("EUR per USD")
    chf_eur = (chf_usd / eur_usd).dropna() if chf_usd is not None and eur_usd is not None else None
    if chf_eur is None and yahoo_fx.get("EURCHF") is not None:
        chf_eur, src["CHF per EUR"] = monthly(yahoo_fx["EURCHF"]), "Yahoo EURCHF=X"
    L.append("Sources: " + "; ".join(f"{k}: {v}" for k, v in src.items()) + ".")
    L.append("")
    r_ch, r_us, r_ea = macro.get("CH policy rate"), macro.get("US policy rate"), macro.get("EA policy rate")
    L.append("## #67 Hedge the currency or not? (returns in CHF)")
    L.append("| asset | period | unhedged CAGR | hedged CAGR | unhedged vol | hedged vol | unhedged max DD | hedged max DD | 10-y windows hedging won |")
    L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|")
    pairs = [("S&P 500 TR (USD)", vfinx, chf_usd, r_us), ("DAX (EUR)", dax, chf_eur, r_ea)]
    us_unh = None
    for name, px, fx, rf in pairs:
        if px is None or len(px) < 500 or fx is None:
            L.append(f"| {name} | — | no data | | | | | | |")
            continue
        r = monthly(px).pct_change().dropna()
        u = unhedged(r, fx)
        if name.startswith("S&P"):
            us_unh = u
        h = hedged(r, r_ch, rf) if r_ch is not None and rf is not None else pd.Series(dtype=float)
        common = u.index.intersection(h.index) if len(h) else u.index
        su, sh = stats(u.reindex(common)), stats(h.reindex(common)) if len(h) else {"n": 0}
        if su.get("n", 0) < 36:
            L.append(f"| {name} | — | too short | | | | | | |")
            continue
        ok_h = sh.get("n", 0) >= 36
        hv = f"{100*sh['vol']:.0f} %" if ok_h else "—"
        hd = f"{100*sh['dd']:.0f} %" if ok_h else "—"
        hw = f"{100*rolling_win(h, u):.0f} %" if ok_h else "—"
        L.append(f"| {name} | {common[0]}–{common[-1]} | {_p(su['cagr'])} | {_p(sh.get('cagr'))} | {100*su['vol']:.0f} % | "
                 f"{hv} | {100*su['dd']:.0f} % | {hd} | {hw} |")
        loc = stats(r.reindex(common))
        L.append(f"| … in local currency | | {_p(loc['cagr'])} | | {100*loc['vol']:.0f} % | | {100*loc['dd']:.0f} % | | |")
    L.append("")
    L.append("Hedged ≈ local return + (CHF rate − foreign rate): the CHF usually had LOWER rates, so hedging costs "
             "roughly that gap every year; unhedged, the investor carries the currency moves instead.")
    L.append("")
    L.append("## #68 Home bias: Swiss stocks (SPI TR) vs US stocks unhedged in CHF")
    if spi is None or len(spi) < 500 or us_unh is None:
        L.append("SPI or US data missing.")
        return "\n".join(L)
    rs = monthly(spi).pct_change().dropna()
    d = pd.concat([rs, us_unh], axis=1, keys=["ch", "us"]).dropna()
    half = d.index[len(d) // 2]
    L.append(f"{d.index[0]}–{d.index[-1]}, monthly rebalanced; Sharpe vs Swiss policy rate.")
    L.append("| share Switzerland | CAGR (CHF) | vol | Sharpe | max DD | 1st half Sharpe | 2nd half Sharpe |")
    L.append("|---|--:|--:|--:|--:|--:|--:|")
    best = None
    for w in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0):
        p = w * d["ch"] + (1 - w) * d["us"]
        s, s1, s2 = stats(p, r_ch), stats(p[p.index < half], r_ch), stats(p[p.index >= half], r_ch)
        L.append(f"| {int(w*100)} % | {_p(s['cagr'])} | {100*s['vol']:.0f} % | {s['sharpe']:.2f} | {100*s['dd']:.0f} % | "
                 f"{s1['sharpe']:.2f} | {s2['sharpe']:.2f} |")
        if best is None or s1["sharpe"] > best[1]:
            best = (w, s1["sharpe"], s2["sharpe"])
    L.append("")
    L.append(f"Best mix in the first half: {int(best[0]*100)} % Switzerland (Sharpe {best[1]:.2f}); in the second half "
             f"it reached {best[2]:.2f}. Correlation CH vs US (in CHF): {d['ch'].corr(d['us']):+.2f}.")
    return "\n".join(L)
