"""
Experiment #43 — the "Buffett factors": value, quality, low volatility / low beta.

Frazzini, Kabiller & Pedersen ("Buffett's Alpha") explain Berkshire's record largely by
cheap (value), high-quality, low-beta stocks held with ~1.6× cheap leverage. Are these
premia real, do they survive their publication, and can a private investor harvest
them long-only?

Part A — Kenneth French data library (CRSP, survivorship-free, US from 1963, Europe and
developed ex-US from 1990), monthly:
  1. Long-short factors: value HML, quality/profitability RMW, investment CMA, size SMB,
     momentum UMD, low-variance and low-beta quintile spreads. Mean, t, Sharpe, CAPM
     alpha, before vs after publication, 2010+, Bonferroni.
  2. Long-only tilts a private investor can buy (value-weighted quintiles): low variance,
     low beta, high profitability, high book/market, and a "Buffett mix" of the three —
     vs the market: excess Sharpe, CAPM alpha, paired Sharpe bootstrap, and the low-vol
     quintile levered to market volatility (financing at T-bill + 1%).
  3. International replication (Europe, developed ex-US).
Part B — own single-stock test from Yahoo prices (US large caps, SMI, DAX): low
volatility, low beta and low MAX (lottery) quintiles vs the equal-weighted universe,
BAB-style beta-neutral long-short, and a placebo of random quintiles.
Pure, injected for CI.
"""
from __future__ import annotations
import io
import math
import zipfile
import numpy as np
import pandas as pd

from .experiments_37 import alpha_beta
from .experiments_38 import _naive

FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FILES = {"ff5": "F-F_Research_Data_5_Factors_2x3_CSV.zip",
         "mom": "F-F_Momentum_Factor_CSV.zip",
         "var": "Portfolios_Formed_on_VAR_CSV.zip",
         "beta": "Portfolios_Formed_on_BETA_CSV.zip",
         "op": "Portfolios_Formed_on_OP_CSV.zip",
         "bm": "Portfolios_Formed_on_BE-ME_CSV.zip",
         "eu5": "Europe_5_Factors_CSV.zip",
         "eumom": "Europe_Mom_Factor_CSV.zip",
         "dx5": "Developed_ex_US_5_Factors_CSV.zip",
         "dxmom": "Developed_ex_US_Mom_Factor_CSV.zip"}
# publication year of the anomaly (first widely cited paper)
PUB = {"SMB (size)": 1981, "HML (value)": 1992, "UMD (momentum)": 1993,
       "RMW (quality/profitability)": 2013, "CMA (investment)": 2015,
       "Low-var − high-var quintile": 2006, "Low-beta − high-beta quintile": 1972}


# ── French library I/O ───────────────────────────────────────────────────────

def fetch_french(fname: str, timeout: int = 30) -> str:
    import urllib.request
    try:
        req = urllib.request.Request(FRENCH + fname, headers={"User-Agent": "Mozilla/5.0 (research)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            return z.read(z.namelist()[0]).decode("latin-1")
    except Exception:
        return ""


def parse_french_monthly(text: str) -> pd.DataFrame:
    """First monthly block (YYYYMM rows) of a French CSV → decimals, Period index.
    For portfolio files the first block is the value-weighted one. −99.99 → NaN."""
    rows, header, started = [], None, False
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        first = parts[0]
        if len(first) == 6 and first.isdigit():
            started = True
            rows.append(parts)
        elif started:
            break
        elif len(parts) > 1 and first == "":
            header = parts[1:]
    if not rows or header is None:
        return pd.DataFrame()
    idx = pd.PeriodIndex([f"{r[0][:4]}-{r[0][4:]}" for r in rows], freq="M")
    vals = []
    for r in rows:
        v = []
        for p in r[1:len(header) + 1]:
            try:
                v.append(float(p))
            except ValueError:
                v.append(np.nan)
        vals.append(v + [np.nan] * (len(header) - len(v)))
    df = pd.DataFrame(vals, index=idx, columns=header)
    return df.where(df > -99.0) / 100.0


# ── monthly statistics ──────────────────────────────────────────────────────

def mt(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 24 or r.std() == 0:
        return {"mean": float("nan"), "t": float("nan"), "sharpe": float("nan"), "n": len(r)}
    return {"mean": float(r.mean() * 12), "t": float(r.mean() / r.std() * math.sqrt(len(r))),
            "sharpe": float(r.mean() / r.std() * math.sqrt(12)), "n": len(r)}


def p_two_sided(t: float) -> float:
    return float(math.erfc(abs(t) / math.sqrt(2))) if np.isfinite(t) else float("nan")


def sharpe_diff_monthly(a: pd.Series, b: pd.Series, n: int = 3000, block: int = 12, seed: int = 0) -> dict:
    """Paired block bootstrap of Sharpe(a) − Sharpe(b) on monthly EXCESS returns."""
    d = pd.concat({"a": a, "b": b}, axis=1).dropna()
    A, B = d["a"].to_numpy(), d["b"].to_numpy()
    sh = lambda z: z.mean() / z.std() * math.sqrt(12) if z.std() > 0 else 0.0
    obs = sh(A) - sh(B)
    rng = np.random.default_rng(seed)
    T = len(A)
    nb = int(np.ceil(T / block))
    diffs = np.empty(n)
    for i in range(n):
        st = rng.integers(0, T - block + 1, nb)
        ix = np.concatenate([np.arange(s, s + block) for s in st])[:T]
        diffs[i] = sh(A[ix]) - sh(B[ix])
    return {"obs": float(obs), "lo": float(np.percentile(diffs, 2.5)), "hi": float(np.percentile(diffs, 97.5)),
            "p": float(np.mean((diffs - obs) >= obs))}


def maxdd(r: pd.Series) -> float:
    eq = (1 + r.dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min())


def cagr(r: pd.Series) -> float:
    r = r.dropna()
    return float((1 + r).prod() ** (12 / len(r)) - 1) if len(r) else float("nan")


# ── Part A ──────────────────────────────────────────────────────────────────

def factor_table(data: dict) -> dict:
    """Long-short factor return series from the French frames."""
    out = {}
    ff5, mom = data.get("ff5"), data.get("mom")
    if ff5 is not None and not ff5.empty:
        for col, lbl in (("SMB", "SMB (size)"), ("HML", "HML (value)"),
                         ("RMW", "RMW (quality/profitability)"), ("CMA", "CMA (investment)")):
            if col in ff5:
                out[lbl] = ff5[col]
    if mom is not None and not mom.empty:
        out["UMD (momentum)"] = mom.iloc[:, 0]
    for key, lbl in (("var", "Low-var − high-var quintile"), ("beta", "Low-beta − high-beta quintile")):
        df = data.get(key)
        if df is not None and {"Lo 20", "Hi 20"} <= set(df.columns):
            out[lbl] = df["Lo 20"] - df["Hi 20"]
    return out


def long_only_tilts(data: dict) -> dict:
    tilts = {}
    for key, col, lbl in (("var", "Lo 20", "Low variance quintile"), ("beta", "Lo 20", "Low beta quintile"),
                          ("op", "Hi 20", "High profitability quintile"), ("bm", "Hi 20", "High book/market (value) quintile")):
        df = data.get(key)
        if df is not None and col in df.columns:
            tilts[lbl] = df[col]
    parts = [tilts[k] for k in ("Low variance quintile", "High profitability quintile",
                                "High book/market (value) quintile") if k in tilts]
    if len(parts) == 3:
        tilts["Buffett mix (low-var + profitable + value, 1/3 each)"] = pd.concat(parts, axis=1).mean(axis=1)
    return tilts


def part_a(data: dict, n_trials: int) -> list:
    L = ["## Part A — Kenneth French data (survivorship-free)", ""]
    ff5 = data.get("ff5")
    if ff5 is None or ff5.empty:
        return L + ["French 5-factor file unavailable — Part A skipped.", ""]
    rf, mkt_x = ff5["RF"], ff5["Mkt-RF"]
    crit = 0.05 / n_trials
    L.append(f"US data {ff5.index[0]} → {ff5.index[-1]}. Market excess: mean {100*mt(mkt_x)['mean']:.1f}% p.a., "
             f"Sharpe {mt(mkt_x)['sharpe']:.2f}. Bonferroni α/{n_trials} = {crit:.5f} (two-sided t).")
    L.append("")
    L.append("### A1 — Long-short factors (US)")
    L.append("| Factor | mean p.a. | t | p | sig | Sharpe | CAPM α p.a. (t) | pub. | mean before | mean after | "
             "Sharpe after | 2010+ mean (t) |")
    L.append("|---|--:|--:|--:|:--:|--:|--:|--:|--:|--:|--:|--:|")
    n_sig = 0
    for lbl, r in factor_table(data).items():
        s = mt(r)
        p = p_two_sided(s["t"])
        sig = p < crit and s["mean"] > 0
        n_sig += int(sig)
        ab = alpha_beta(r, mkt_x)
        py = PUB.get(lbl, 2000)
        pre, post = mt(r.loc[:f"{py}-12"]), mt(r.loc[f"{py + 1}-01":])
        rec = mt(r.loc["2010-01":])
        L.append(f"| {lbl} | {100*s['mean']:+.1f}% | {s['t']:.2f} | {p:.4f} | {'✅' if sig else '❌'} | "
                 f"{s['sharpe']:.2f} | {100*ab['alpha']:+.1f}% ({ab['t']:.1f}) | {py} | "
                 f"{100*pre['mean']:+.1f}% | {100*post['mean']:+.1f}% | {post['sharpe']:.2f} | "
                 f"{100*rec['mean']:+.1f}% ({rec['t']:.1f}) |")
    L.append("")

    L.append("### A2 — Long-only tilts a private investor can buy (value-weighted US quintiles)")
    L.append("| Portfolio | CAGR | vol | excess Sharpe | max DD | CAPM α p.a. (t) | β | ΔSharpe vs market [95% CI] | p | "
             "sig | 2010+ ΔSharpe |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|")
    mkt = mkt_x + rf
    rows = {"Market": mkt}
    rows.update(long_only_tilts(data))
    lv = rows.get("Low variance quintile")
    if lv is not None:
        d = pd.concat({"lv": lv, "rf": rf, "m": mkt}, axis=1).dropna()
        lev = (d["m"].rolling(36).std() / d["lv"].rolling(36).std()).shift(1).clip(0.5, 2.5).fillna(1.0)
        rows["Low variance levered to market vol (≤2.5×, T-bill+1%)"] = \
            d["rf"] + lev * (d["lv"] - d["rf"]) - (lev - 1).clip(lower=0) * 0.01 / 12
    tilt_sig = 0
    for lbl, r in rows.items():
        r = r.dropna()
        x = r - rf.reindex(r.index)
        s = mt(x)
        ab = alpha_beta(x, mkt_x)
        if lbl == "Market":
            L.append(f"| {lbl} | {100*cagr(r):.1f}% | {100*r.std()*math.sqrt(12):.1f}% | {s['sharpe']:.2f} | "
                     f"{100*maxdd(r):.0f}% | — | 1.00 | — | — | | — |")
            continue
        bt = sharpe_diff_monthly(x, mkt_x.reindex(x.index))
        rec = sharpe_diff_monthly(x.loc["2010-01":], mkt_x.loc["2010-01":], n=1000)
        sig = bt["p"] < crit and bt["obs"] > 0
        tilt_sig += int(sig)
        L.append(f"| {lbl} | {100*cagr(r):.1f}% | {100*r.std()*math.sqrt(12):.1f}% | {s['sharpe']:.2f} | "
                 f"{100*maxdd(r):.0f}% | {100*ab['alpha']:+.1f}% ({ab['t']:.1f}) | {ab['beta']:.2f} | "
                 f"{bt['obs']:+.2f} [{bt['lo']:+.2f}, {bt['hi']:+.2f}] | {bt['p']:.4f} | {'✅' if sig else '❌'} | "
                 f"{rec['obs']:+.2f} |")
    L.append("")

    L.append("### A3 — International replication (long-short factors)")
    L.append("| Region | Factor | mean p.a. | t | Sharpe | 2010+ mean (t) |")
    L.append("|---|---|--:|--:|--:|--:|")
    intl_pos = intl_n = 0
    for reg, k5, km in (("Europe", "eu5", "eumom"), ("Developed ex-US", "dx5", "dxmom")):
        df, mo = data.get(k5), data.get(km)
        if df is None or df.empty:
            L.append(f"| {reg} | (data unavailable) | | | | |")
            continue
        series = {c: df[c] for c in ("SMB", "HML", "RMW", "CMA") if c in df}
        if mo is not None and not mo.empty:
            series["UMD"] = mo.iloc[:, 0]
        for c, r in series.items():
            s, rec = mt(r), mt(r.loc["2010-01":])
            intl_n += 1
            intl_pos += int(s["t"] > 2)
            L.append(f"| {reg} ({r.dropna().index[0]}→) | {c} | {100*s['mean']:+.1f}% | {s['t']:.2f} | "
                     f"{s['sharpe']:.2f} | {100*rec['mean']:+.1f}% ({rec['t']:.1f}) |")
    L.append("")
    L.append(f"**Part A summary:** US long-short factors significant after haircut: {n_sig}; long-only "
             f"tilts with significant Sharpe gain vs market: {tilt_sig}; international factors with t > 2: "
             f"{intl_pos}/{intl_n}.")
    L.append("")
    return L


# ── Part B: own single-stock panel ──────────────────────────────────────────

def monthly_panel(prices: dict) -> pd.DataFrame:
    cols = {k: _naive(v) for k, v in prices.items() if v is not None and len(v) > 300}
    return pd.DataFrame(cols).sort_index() if cols else pd.DataFrame()


def month_scores(daily_px: pd.DataFrame, index_px: pd.Series | None, score: str) -> list:
    """Per month-end: eligible names, their score (vol / beta / max), betas and next
    month's returns. Computed once so the placebo only has to reshuffle."""
    r = daily_px.pct_change(fill_method=None)
    if index_px is not None and len(index_px):
        ir = _naive(index_px).reindex(daily_px.index).ffill().pct_change(fill_method=None)
    else:
        ir = r.mean(axis=1)
    per = r.index.to_period("M")
    me = pd.Series(r.index, index=r.index).groupby(per).last()
    mret = (1 + r.fillna(0.0)).groupby(per).prod() - 1
    valid = r.notna().groupby(per).sum()
    out = []
    for i in range(len(me) - 1):
        d, nxt = me.iloc[i], me.index[i + 1]
        hist = r.loc[:d].tail(252)
        if len(hist) < 240:
            continue
        ok = [c for c in hist.columns[hist.notna().sum() >= 240] if valid.loc[nxt, c] >= 10]
        if not ok:
            continue
        h = hist[ok]
        ih = ir.loc[:d].tail(252)
        hd = (h - h.mean()).fillna(0.0)
        idm = (ih - ih.mean()).fillna(0.0)
        var_i = float((idm ** 2).sum())
        beta = (hd.mul(idm, axis=0).sum() / var_i) if var_i > 0 else pd.Series(np.nan, index=ok)
        sc = {"vol": h.std(), "beta": beta, "max": h.tail(21).max()}[score].dropna()
        out.append({"month": nxt, "score": sc, "beta": beta, "ret": mret.loc[nxt, ok]})
    return out


def quintile_backtest(months: list, q: float = 0.2, rng=None, min_names: int = 10) -> pd.DataFrame:
    """Monthly EW portfolios: 'low' = lowest-score quintile, 'high' = highest,
    'all' = EW universe, 'bab_raw' = long low / short high, each scaled to β=1.
    rng → random quintiles (placebo)."""
    rows = []
    for m in months:
        sc = m["score"]
        if len(sc) < min_names:
            continue
        if rng is not None:
            sc = pd.Series(rng.permutation(sc.to_numpy()), index=sc.index)
        k = max(2, int(round(q * len(sc))))
        lo, hi = sc.nsmallest(k).index, sc.nlargest(k).index
        nr, beta = m["ret"], m["beta"]
        bl, bh = float(beta[lo].mean()), float(beta[hi].mean())
        low, high = float(nr[lo].mean()), float(nr[hi].mean())
        bab = (low / bl - high / bh) if bl > 0.1 and bh > 0.1 else np.nan
        rows.append({"month": m["month"], "low": low, "high": high, "all": float(nr.mean()),
                     "bab_raw": bab, "beta_low": bl, "beta_high": bh})
    return pd.DataFrame(rows).set_index("month") if rows else pd.DataFrame()


def part_b(regions: dict, rf_m: pd.Series | None, n_trials: int, n_placebo: int = 100) -> list:
    """regions: {name: (prices dict, index Series)}."""
    L = ["## Part B — own single-stock test (Yahoo, today's large caps → survivorship-biased)", ""]
    crit = 0.05 / n_trials
    L.append("| Region | Score | months | low-quintile CAGR | EW universe CAGR | low β | ΔSharpe low vs EW [95% CI] | "
             "placebo p | BAB mean p.a. (t) | sig |")
    L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|:--:|")
    n_sig = 0
    for reg, (prices, idx_px) in regions.items():
        px = monthly_panel(prices)
        if px.shape[1] < 10:
            L.append(f"| {reg} | (only {px.shape[1]} stocks) | | | | | | | | |")
            continue
        for score, lbl in (("vol", "low volatility"), ("beta", "low beta"), ("max", "low MAX (no lottery)")):
            months = month_scores(px, idx_px, score)
            bt = quintile_backtest(months)
            if bt.empty or len(bt) < 36:
                L.append(f"| {reg} | {lbl} | {len(bt)} | | | | | | | |")
                continue
            rf = rf_m.reindex(bt.index).fillna(0.0) if rf_m is not None else pd.Series(0.0, index=bt.index)
            xl, xa = bt["low"] - rf, bt["all"] - rf
            sd = sharpe_diff_monthly(xl, xa, n=1000)
            sh = lambda z: z.mean() / z.std() * math.sqrt(12) if z.std() > 0 else 0.0
            real = sh(xl) - sh(xa)
            rng = np.random.default_rng(43)
            plc = []
            for _ in range(n_placebo):
                pb = quintile_backtest(months, rng=rng)
                plc.append(sh(pb["low"] - rf.reindex(pb.index).fillna(0.0)) - sh(pb["all"] - rf.reindex(pb.index).fillna(0.0)))
            p_plc = float(np.mean(np.array(plc) >= real))
            bab = mt(bt["bab_raw"])
            sig = p_plc < max(crit, 1.0 / n_placebo) and real > 0 and sd["lo"] > 0
            n_sig += int(sig)
            L.append(f"| {reg} ({bt.index[0]}→) | {lbl} | {len(bt)} | {100*cagr(bt['low']):.1f}% | "
                     f"{100*cagr(bt['all']):.1f}% | {bt['beta_low'].mean():.2f} | "
                     f"{sd['obs']:+.2f} [{sd['lo']:+.2f}, {sd['hi']:+.2f}] | {p_plc:.2f} | "
                     f"{100*bab['mean']:+.1f}% ({bab['t']:.1f}) | {'✅' if sig else '❌'} |")
    L.append("")
    L.append(f"**Part B summary:** {n_sig} region/score cells with a Sharpe gain that beats the random-quintile "
             f"placebo and has a CI above zero. Placebo p floor = 1/{n_placebo}.")
    L.append("")
    return L


def run_experiment43_report(french: dict, regions: dict, n_trials: int = 190, n_placebo: int = 100) -> str:
    """french: {key: parsed DataFrame}; regions: {name: (prices dict, index Series)}."""
    from datetime import datetime, timezone
    L = [f"# Experiment #43 — Buffett factors: value, quality, low volatility "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    have = [k for k, v in french.items() if v is not None and not v.empty]
    L.append(f"French files loaded: {len(have)}/{len(FILES)} ({', '.join(have) or 'none'}). "
             f"Project trial count for haircut: {n_trials}.")
    L.append("")
    L += part_a(french, n_trials)
    ff5 = french.get("ff5")
    rf_m = ff5["RF"] if ff5 is not None and not ff5.empty else None
    L += part_b(regions, rf_m, n_trials, n_placebo)
    return "\n".join(L)
