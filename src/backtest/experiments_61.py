"""
Experiment #61 — predictability map: how much of the next return can the past explain,
across asset classes and horizons from one day to ten years?

  A Return-on-return predictability, 20 assets (equity indices, sectors, bonds, credit,
    gold, oil, currencies incl. CHF, real estate, Bitcoin/Ether), non-overlapping returns
    at 1 day, 1 week, 1 month, 3 months, 12 months:
      - lag-1 autocorrelation ρ with t = ρ·√n
      - sign persistence (does the next period have the same sign?) vs its base rate
      - OUT-OF-SAMPLE R² (Campbell–Thompson): expanding regression r(t+1) ~ r(t) vs the
        expanding historical mean, first third of the sample as burn-in. Positive = the
        past return helps beyond 'average'; negative = it hurts.
    Summary: how many asset×horizon cells have |t| > 2 (≈ 5 % expected by chance) and
    the median OOS R² per horizon.
  B Valuation predictability (Shiller S&P 1881→): real returns over the next 1 / 5 / 10
    years on log CAPE and log dividend yield — in-sample R² vs out-of-sample R²
    (expanding from 1930, one forecast per year), the Welch–Goyal (2008) test.
  C Minutes: reference to #60 (minute bars, 8 symbols).
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

ASSETS = {  # name → (Yahoo symbol, start)
    "S&P 500": ("^GSPC", "1928-01-01"), "Nasdaq": ("^IXIC", "1971-01-01"), "DAX": ("^GDAXI", "1988-01-01"),
    "SMI": ("^SSMI", "1990-11-01"), "Nikkei": ("^N225", "1965-01-01"), "Emerging mkts": ("EEM", "2003-04-01"),
    "Tech sector": ("XLK", "1999-01-01"), "Energy sector": ("XLE", "1999-01-01"),
    "US Treasuries 20y+": ("TLT", "2002-08-01"), "US Treasuries 7–10y": ("IEF", "2002-08-01"),
    "High yield bonds": ("HYG", "2007-05-01"), "Real estate": ("VNQ", "2004-10-01"),
    "Gold": ("GC=F", "2000-09-01"), "Crude oil": ("CL=F", "2000-09-01"),
    "EUR/USD": ("EURUSD=X", "2003-12-01"), "USD/CHF": ("CHF=X", "2003-12-01"), "USD/JPY": ("JPY=X", "1996-11-01"),
    "Bitcoin": ("BTC-USD", "2014-09-17"), "Ether": ("ETH-USD", "2017-11-09"),
    "S&P 500 total return fund": ("VFINX", "1980-01-01"),
}
HORIZONS = {"1 day": 1, "1 week": 5, "1 month": 21, "3 months": 63, "12 months": 252}


def nonoverlap(log_px: pd.Series, k: int) -> pd.Series:
    """Non-overlapping k-trading-day log returns."""
    s = log_px.dropna()
    s = s.iloc[::k]
    return s.diff().dropna()


def oos_r2(r: pd.Series, burn: float = 1 / 3) -> float:
    """Campbell–Thompson OOS R² of r(t+1) ~ a + b·r(t) (expanding OLS) vs the expanding mean.
    Running sums → O(n)."""
    x, y = r.to_numpy()[:-1].astype(float), r.to_numpy()[1:].astype(float)
    n = len(y)
    start = max(int(n * burn), 10)
    if n - start < 10:
        return float("nan")
    cx, cy = np.cumsum(x), np.cumsum(y)
    cxx, cxy = np.cumsum(x * x), np.cumsum(x * y)
    t = np.arange(start, n)                      # forecast y[t] with data 0..t-1
    k = t.astype(float)
    sx, sy, sxx, sxy = cx[t - 1], cy[t - 1], cxx[t - 1], cxy[t - 1]
    mx, my = sx / k, sy / k
    vx = sxx / k - mx ** 2
    cov = sxy / k - mx * my
    b = np.where(vx > 0, cov / np.where(vx > 0, vx, 1), 0.0)
    a = my - b * mx
    se_m = ((y[t] - (a + b * x[t])) ** 2).sum()
    se_h = ((y[t] - my) ** 2).sum()
    return float(1 - se_m / se_h) if se_h > 0 else float("nan")


def cell(r: pd.Series) -> dict:
    n = len(r)
    if n < 30:
        return {"n": n}
    rho = float(r.autocorr(1))
    s = np.sign(r.to_numpy())
    same = float((s[1:] == s[:-1]).mean())
    p_up = float((s > 0).mean())
    base = p_up ** 2 + (1 - p_up) ** 2          # same-sign rate if signs were independent
    return {"n": n, "rho": rho, "t": rho * math.sqrt(n), "same": same, "base": base, "oos": oos_r2(r)}


def predictability_map(prices: dict) -> dict:
    out = {}
    for name, s in prices.items():
        if s is None or len(s) < 500:
            continue
        lp = np.log(pd.Series(s).astype(float).where(lambda x: x > 0)).dropna()
        out[name] = {h: cell(nonoverlap(lp, k)) for h, k in HORIZONS.items()}
    return out


def valuation_test(shiller: pd.DataFrame, horizons=(1, 5, 10), oos_start: int = 1930) -> list:
    """Predict real S&P returns over the next h years with log CAPE and log D/P (annual,
    January observations). In-sample R² and expanding OOS R² (Welch–Goyal)."""
    d = shiller.copy()
    d.index = pd.to_datetime(d.index)
    d = d[d.index.month == 1]
    d = d[~d.index.year.duplicated()]
    real_px = d["price"] / d["cpi"]
    dy = (d["div"] / d["price"]).where(lambda x: x > 0)
    real_tr = (real_px * (1 + dy).cumprod().shift(1).fillna(1.0))
    years = d.index.year
    rows = []
    for h in horizons:
        fwd = np.log(real_tr.shift(-h) / real_tr) / h
        for name, pred in (("log CAPE", np.log(d["cape"].where(d["cape"] > 0))), ("log dividend yield", np.log(dy))):
            z = pd.DataFrame({"x": pred.to_numpy(), "y": fwd.to_numpy()}, index=years).dropna()
            if len(z) < 40:
                continue
            b, a = np.polyfit(z["x"], z["y"], 1)
            r2_in = 1 - ((z["y"] - (a + b * z["x"])) ** 2).sum() / ((z["y"] - z["y"].mean()) ** 2).sum()
            se_m = se_h = 0.0
            n_oos = 0
            for yr in z.index[z.index >= oos_start]:
                train = z[z.index <= yr - h]       # only outcomes already known at year yr
                if len(train) < 20:
                    continue
                bb, aa = np.polyfit(train["x"], train["y"], 1)
                se_m += (z.at[yr, "y"] - (aa + bb * z.at[yr, "x"])) ** 2
                se_h += (z.at[yr, "y"] - train["y"].mean()) ** 2
                n_oos += 1
            rows.append({"h": h, "pred": name, "n": len(z), "slope": float(b), "r2_in": float(r2_in),
                         "r2_oos": float(1 - se_m / se_h) if se_h > 0 else float("nan"), "n_oos": n_oos})
    return rows


def run_experiment61_report(prices: dict, shiller: pd.DataFrame | None) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #61 — predictability map: assets × horizons ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("Non-overlapping log returns. ρ = lag-1 autocorrelation (t = ρ·√n). 'same sign' = share of periods "
             "with the same sign as the previous one vs what independent signs would give. OOS R² = out-of-sample "
             "gain of 'use the last return' over 'use the historical average' (Campbell–Thompson); 1 % OOS R² is "
             "already economically meaningful at monthly horizons.")
    L.append("")
    m = predictability_map(prices)
    L.append("## A Return-on-return predictability")
    L.append("| asset | from | " + " | ".join(HORIZONS) + " |")
    L.append("|---|---|" + "---|" * len(HORIZONS))
    for name, cells in m.items():
        start = pd.Series(prices[name]).dropna().index[0]
        parts = []
        for h in HORIZONS:
            c = cells[h]
            if c.get("n", 0) < 30:
                parts.append("—")
                continue
            star = "**" if abs(c["t"]) > 2 else ""
            parts.append(f"{star}ρ {c['rho']:+.2f} (t {c['t']:+.1f}){star}, OOS R² {100*c['oos']:+.1f} %")
        L.append(f"| {name} | {pd.Timestamp(start):%Y} | " + " | ".join(parts) + " |")
    L.append("")
    L.append("| horizon | cells | |t| > 2 | expected by chance | median ρ | median OOS R² | cells with OOS R² > 1 % | same-sign minus base (median) |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|")
    for h in HORIZONS:
        cs = [c[h] for c in m.values() if c[h].get("n", 0) >= 30]
        if not cs:
            continue
        sig = sum(abs(c["t"]) > 2 for c in cs)
        oos = [c["oos"] for c in cs if np.isfinite(c["oos"])]
        L.append(f"| {h} | {len(cs)} | {sig} | {0.05*len(cs):.1f} | {np.median([c['rho'] for c in cs]):+.3f} | "
                 f"{100*np.median(oos):+.2f} % | {sum(o > 0.01 for o in oos)} | "
                 f"{100*np.median([c['same'] - c['base'] for c in cs]):+.1f} pt |")
    L.append("")
    L.append("## B Valuation predicts long-run returns? (Shiller S&P, real total return, one observation per January)")
    if shiller is None or shiller.empty:
        L.append("Shiller data missing.")
    else:
        L.append("| horizon | predictor | years | slope | in-sample R² | out-of-sample R² (from 1930) | OOS forecasts |")
        L.append("|---|---|--:|--:|--:|--:|--:|")
        for r in valuation_test(shiller):
            L.append(f"| {r['h']} y | {r['pred']} | {r['n']} | {r['slope']:+.3f} | {100*r['r2_in']:.0f} % | "
                     f"**{100*r['r2_oos']:+.0f} %** | {r['n_oos']} |")
        L.append("")
        L.append("Overlapping multi-year windows inflate in-sample R² (few independent decades). The out-of-sample "
                 "column is what a forecaster could actually have achieved in real time.")
    L.append("")
    L.append("## C Minutes")
    L.append("See #60: 1-minute returns have significant negative autocorrelation (bid–ask bounce, ρ ≈ −0.01 for "
             "stocks, −0.2 for crypto), but the break-even cost is 0.02–0.2 bp per side — far below any real cost.")
    return "\n".join(L)
