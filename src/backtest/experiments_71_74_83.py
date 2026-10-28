"""
Experiments #71, #74, #83.

#71 Stock/bond mix and rebalancing (Shiller real US data since 1871): 100/0, 80/20, 60/40,
    40/60, 20/80 with rebalancing yearly, monthly, by ±5 / ±10 pt bands, and never.
    Real CAGR, volatility, max drawdown, worst 10-year period, longest time under water.
#74 How many single stocks? σ²(n) = σ_m² + σ_e²/n — mathematically and with the #58
    calibrated market (beta 1, idiosyncratic vol 40 %, 1.5 %/yr bust risk): for 1–100 stocks
    the spread of 20-year outcomes (5 % / median / 95 %), chance to trail the index by more
    than 30 %, and chance to lose money; plus real US stocks when prices are given.
#83 Market regimes: a 2-state Gaussian hidden Markov model on monthly S&P returns (fitted
    by Baum–Welch, numpy). Are 'calm' and 'turbulent' states stable? Walk-forward: refit
    every year on past data only, be invested when the filtered probability of the calm
    state > 50 % — vs buy & hold and vs the 10-month trend rule.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


# ── #71 ──────────────────────────────────────────────────────────────────────

def mix_returns(stock: pd.Series, bond: pd.Series, w: float, rule: str, band: float = 0.05) -> pd.Series:
    s, b = stock.to_numpy(), bond.to_numpy()
    vs, vb = w, 1 - w
    out = []
    for i in range(len(s)):
        tot0 = vs + vb
        vs *= 1 + s[i]
        vb *= 1 + b[i]
        out.append((vs + vb) / tot0 - 1)
        tot = vs + vb
        cur = vs / tot if tot > 0 else w
        reb = (rule == "monthly") or (rule == "yearly" and (i + 1) % 12 == 0) or \
              (rule == "band" and abs(cur - w) > band)
        if reb:
            vs, vb = w * tot, (1 - w) * tot
    return pd.Series(out, index=stock.index)


def risk_stats(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    under, longest = 0, 0
    for v in (dd < 0).to_numpy():
        under = under + 1 if v else 0
        longest = max(longest, under)
    g10 = eq / eq.shift(120)
    return {"cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1), "vol": float(r.std() * math.sqrt(12)),
            "dd": float(dd.min()), "worst10": float(g10.min() ** 0.1 - 1), "under_years": longest / 12}


# ── #74 ──────────────────────────────────────────────────────────────────────

def portfolio_spread(w: np.ndarray, sizes=(1, 2, 5, 10, 20, 30, 50, 100), n: int = 50_000, seed: int = 74) -> list:
    rng = np.random.default_rng(seed)
    mkt = float(np.mean(w))
    out = []
    for k in sizes:
        pw = w[rng.integers(0, len(w), (n, k))].mean(axis=1)
        out.append({"k": k, "p5": float(np.percentile(pw, 5)), "med": float(np.median(pw)),
                    "p95": float(np.percentile(pw, 95)), "trail30": float((pw < 0.7 * mkt).mean()),
                    "lose": float((pw < 1).mean())})
    return out


# ── #83 ──────────────────────────────────────────────────────────────────────

def hmm_fit(x: np.ndarray, iters: int = 100, seed: int = 83):
    """2-state Gaussian HMM, Baum–Welch with scaling. Returns (pi, A, mu, sd)."""
    rng = np.random.default_rng(seed)
    n = len(x)
    mu = np.array([np.percentile(x, 70), np.percentile(x, 20)])
    sd = np.array([x.std() * 0.7, x.std() * 1.5])
    A = np.array([[0.95, 0.05], [0.10, 0.90]])
    pi = np.array([0.5, 0.5])
    for _ in range(iters):
        B = np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * math.sqrt(2 * math.pi)) + 1e-300
        al = np.zeros((n, 2)); c = np.zeros(n)
        al[0] = pi * B[0]; c[0] = al[0].sum(); al[0] /= c[0]
        for t in range(1, n):
            al[t] = (al[t - 1] @ A) * B[t]; c[t] = al[t].sum(); al[t] /= c[t]
        be = np.ones((n, 2))
        for t in range(n - 2, -1, -1):
            be[t] = (A @ (B[t + 1] * be[t + 1])) / c[t + 1]
        g = al * be; g /= g.sum(axis=1, keepdims=True)
        xi = np.zeros((2, 2))
        for t in range(n - 1):
            m = al[t][:, None] * A * (B[t + 1] * be[t + 1])[None, :] / c[t + 1]
            xi += m / m.sum()
        pi = g[0]
        A = xi / xi.sum(axis=1, keepdims=True)
        mu = (g * x[:, None]).sum(0) / g.sum(0)
        sd = np.sqrt((g * (x[:, None] - mu) ** 2).sum(0) / g.sum(0)) + 1e-6
    if sd[0] > sd[1]:                      # state 0 = calm (lower volatility)
        A = A[::-1, ::-1]; mu = mu[::-1]; sd = sd[::-1]; pi = pi[::-1]
    return pi, A, mu, sd


def hmm_filter(x: np.ndarray, pi, A, mu, sd) -> np.ndarray:
    """P(calm | data up to t)."""
    B = np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * math.sqrt(2 * math.pi)) + 1e-300
    a = pi * B[0]; a /= a.sum()
    out = [a[0]]
    for t in range(1, len(x)):
        a = (a @ A) * B[t]; a /= a.sum()
        out.append(a[0])
    return np.array(out)


def hmm_walk_forward(r: pd.Series, cash: pd.Series, start_years: int = 30, refit_every: int = 12) -> pd.Series:
    x = np.log1p(r.to_numpy())
    w = np.full(len(x), np.nan)
    params = None
    for t in range(start_years * 12, len(x)):
        if params is None or (t - start_years * 12) % refit_every == 0:
            params = hmm_fit(x[:t], iters=40)
        p = hmm_filter(x[:t], *params)[-1]          # known at the end of month t−1
        w[t] = 1.0 if p > 0.5 else 0.0
    w = pd.Series(w, index=r.index)
    c = cash.reindex(r.index).fillna(0.0)
    return (w * r + (1 - w) * c).dropna(), w


# ── report ───────────────────────────────────────────────────────────────────

def run_experiments71_74_83_report(shiller: pd.DataFrame, prices: dict | None = None) -> str:
    from datetime import datetime, timezone
    from .experiments_70_72 import real_series
    from .experiments_58 import stock_market, empirical
    L = [f"# Experiments #71 / #74 / #83 — mixes & rebalancing, number of stocks, market regimes "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    r = real_series(shiller) if shiller is not None and not shiller.empty else pd.DataFrame()
    L.append("## #71 Stock/bond mix and rebalancing (US, real, Shiller)")
    if r.empty:
        L.append("Shiller data missing.")
    else:
        L.append(f"{r.index[0]} → {r.index[-1]}.")
        L.append("| stocks/bonds | rebalancing | real CAGR | vol | max DD | worst 10 y p.a. | longest under water |")
        L.append("|---|---|--:|--:|--:|--:|--:|")
        for w in (1.0, 0.8, 0.6, 0.4, 0.2):
            for rule, band, lbl in (("yearly", 0, "yearly"), ("monthly", 0, "monthly"), ("band", 0.05, "±5 pt band"),
                                    ("band", 0.10, "±10 pt band"), ("never", 0, "never (drifts)")):
                if w == 1.0 and rule != "never":
                    continue
                s = risk_stats(mix_returns(r["stock"], r["bond"], w, rule, band))
                L.append(f"| {int(w*100)}/{int(100-w*100)} | {lbl} | {100*s['cagr']:+.2f} % | {100*s['vol']:.0f} % | "
                         f"{100*s['dd']:.0f} % | {100*s['worst10']:+.1f} % | {s['under_years']:.0f} y |")
    L.append("")
    L.append("## #74 How many single stocks? (20 years, simulated market as in #58)")
    sm = stock_market()
    L.append(f"Market (= all stocks) ×{sm['market_multiple']:.1f}. Math: with idiosyncratic σ 40 % and market σ ~16 %, "
             f"portfolio σ ≈ √(16² + 40²/n): 1 stock {math.sqrt(16**2+40**2):.0f} %, 5 → {math.sqrt(16**2+40**2/5):.0f} %, "
             f"20 → {math.sqrt(16**2+40**2/20):.0f} %, 50 → {math.sqrt(16**2+40**2/50):.0f} %.")
    L.append("| stocks held | 5 % worst | median | 95 % best | trails the market by > 30 % | loses money |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for c in portfolio_spread(sm["w"]):
        L.append(f"| {c['k']} | ×{c['p5']:.1f} | ×{c['med']:.1f} | ×{c['p95']:.1f} | {100*c['trail30']:.0f} % | {100*c['lose']:.0f} % |")
    if prices:
        e = empirical(prices)
        if e.get("n_stocks", 0) >= 50:
            mult = []
            for t, s in prices.items():
                s = pd.Series(s).dropna()
                if len(s) >= 2520 and s.iloc[0] >= 1:
                    v = s.iloc[2519] / s.iloc[0]
                    if 0 < v <= 1000:
                        mult.append(v)
            if len(mult) >= 50:
                L.append("")
                L.append(f"Real US stocks ({len(mult)} survivors, 10 years):")
                for c in portfolio_spread(np.array(mult), sizes=(1, 5, 10, 20, 50)):
                    L.append(f"- {c['k']} stocks: 5 % ×{c['p5']:.1f}, median ×{c['med']:.1f}, 95 % ×{c['p95']:.1f}, "
                             f"trails the average stock by > 30 %: {100*c['trail30']:.0f} %")
    L.append("")
    L.append("## #83 Market regimes (2-state hidden Markov model, S&P monthly)")
    if r.empty:
        L.append("Shiller data missing.")
        return "\n".join(L)
    pi, A, mu, sd = hmm_fit(np.log1p(r["stock"].to_numpy()))
    L.append(f"Full-sample fit: calm state mean {100*mu[0]*12:+.1f} %/yr, vol {100*sd[0]*math.sqrt(12):.0f} %; "
             f"turbulent mean {100*mu[1]*12:+.1f} %/yr, vol {100*sd[1]*math.sqrt(12):.0f} %; stay probability "
             f"calm {A[0,0]:.2f}, turbulent {A[1,1]:.2f} (average duration {1/(1-A[0,0]):.0f} / {1/(1-A[1,1]):.0f} months).")
    strat, w = hmm_walk_forward(r["stock"], r["cash"])
    bh = r["stock"].reindex(strat.index)
    px = (1 + r["stock"]).cumprod()
    sig = (px > px.rolling(10).mean()).astype(float).shift(1).reindex(strat.index)
    trend = sig * bh + (1 - sig) * r["cash"].reindex(strat.index)
    L.append(f"Walk-forward {strat.index[0]}–{strat.index[-1]} (refit yearly on past data only):")
    L.append("| strategy | real CAGR | vol | max DD | invested |")
    L.append("|---|--:|--:|--:|--:|")
    for nm, x, inv in (("Buy & hold", bh, 1.0), ("HMM: invested when P(calm) > 50 %", strat, float(w.dropna().mean())),
                       ("10-month trend rule", trend, float(sig.mean()))):
        s = risk_stats(x.dropna())
        L.append(f"| {nm} | {100*s['cagr']:+.2f} % | {100*s['vol']:.0f} % | {100*s['dd']:.0f} % | {100*inv:.0f} % |")
    L.append("")
    L.append("Note: Shiller monthly averages smooth prices (#35) — regime and trend results are slightly flattered.")
    return "\n".join(L)
