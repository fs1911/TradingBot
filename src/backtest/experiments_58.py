"""
Experiment #58 — luck simulation: how many "successful investors" does pure chance produce?

Every simulated person here has ZERO skill. Whatever they achieve is luck.

  A Coin-flip gurus: 68 gurus × ~97 forecasts each, each forecast right with p = 0.5
    (setup of the CXO Advisory "Guru Grades" 2005–2012: 6,582 forecasts, average
    accuracy 47 %). How wide is the spread of accuracies from luck alone?
  B Skill-less fund managers: 10,000 managers, yearly excess return vs the index
    ~ Normal(−fee, tracking error). Fee 1 %, tracking error 6 %. How many beat the
    index 5 / 10 / 15 years in a row, and how many have a 10-year t-stat > 2
    ("proven skill") by pure chance?
  C Random stock pickers, simulated stock market: 10,000 stocks over 20 years.
    Market +7 %/yr on its expected path; each stock: beta 1, idiosyncratic volatility 40 % (sensitivity 35/45 %),
    1.5 %/yr chance of going to zero. Calibrated to Bessembinder (2018): most single
    stocks lose against T-bills over their life, a few create almost all wealth.
    Random investors buy 1 / 5 / 20 stocks: how many make ×10, ×100, how many lose?
  D Empirical check with real US stock prices (Yahoo, 2009 → today; upward-biased
    because delisted stocks are missing): random 1- and 5-stock portfolios, 10-year
    multiples.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


def coin_gurus(n_gurus: int = 68, n_forecasts: int = 97, seed: int = 58, n_sims: int = 2000) -> dict:
    rng = np.random.default_rng(seed)
    acc = rng.binomial(n_forecasts, 0.5, (n_sims, n_gurus)) / n_forecasts
    best, worst = acc.max(axis=1), acc.min(axis=1)
    return {"best_median": float(np.median(best)), "worst_median": float(np.median(worst)),
            "share_ge_60": float((acc >= 0.60).mean()), "share_le_40": float((acc <= 0.40).mean()),
            "p_best_ge_65": float((best >= 0.65).mean()), "p_worst_le_30": float((worst <= 0.30).mean())}


def managers(n: int = 10_000, years: int = 15, fee: float = 0.01, te: float = 0.06, seed: int = 58) -> dict:
    rng = np.random.default_rng(seed)
    ex = rng.normal(-fee, te, (n, years))
    win = ex > 0
    streak = np.zeros(n, int)
    cur = np.zeros(n, int)
    for y in range(years):
        cur = np.where(win[:, y], cur + 1, 0)
        streak = np.maximum(streak, cur)
    first10 = ex[:, :10]
    t10 = first10.mean(axis=1) / (first10.std(axis=1, ddof=1) / math.sqrt(10))
    cum15 = (1 + ex).prod(axis=1) - 1
    return {"n": n, "fee": fee, "te": te,
            "beat_5_in_row_first5": int(win[:, :5].all(axis=1).sum()),
            "beat_10_in_row_first10": int(win[:, :10].all(axis=1).sum()),
            "max_streak_ge_5": int((streak >= 5).sum()), "max_streak_ge_8": int((streak >= 8).sum()),
            "t10_gt_2": int((t10 > 2).sum()), "share_behind_after_15y": float((cum15 < 0).mean()),
            "top1pct_cum15": float(np.percentile(cum15, 99))}


def stock_market(n_stocks: int = 10_000, years: int = 20, mu_m: float = 0.07, vol_m: float = 0.16,
                 idio: float = 0.40, death: float = 0.015, rf: float = 0.03, seed: int = 58) -> dict:
    """Monthly simulation → wealth multiples per stock after `years` (0 = went bust)."""
    rng = np.random.default_rng(seed)
    T = years * 12
    # Market on its expected path (one random path would make the result path luck);
    # survivors earn the death hazard back so the whole market returns mu_m on average.
    m = np.full(T, (math.log(1 + mu_m) + death) / 12)
    e = rng.normal(-idio ** 2 / 24, idio / math.sqrt(12), (n_stocks, T))
    logw = (m[None, :] + e).cumsum(axis=1)
    alive = rng.random((n_stocks, T)) > death / 12
    alive = np.cumprod(alive, axis=1).astype(bool)
    w = np.where(alive[:, -1], np.exp(logw[:, -1]), 0.0)
    mkt = float(np.exp(m.sum()))
    return {"w": w, "market_multiple": float(np.mean(w)), "index_path_multiple": mkt,
            "tbill_multiple": (1 + rf) ** years}


def pickers(w: np.ndarray, sizes=(1, 5, 20), n: int = 100_000, seed: int = 58) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for k in sizes:
        idx = rng.integers(0, len(w), (n, k))
        pw = w[idx].mean(axis=1)
        out[k] = {"x10": float((pw >= 10).mean()), "x100": float((pw >= 100).mean()),
                  "lost": float((pw < 1).mean()), "median": float(np.median(pw)), "p99": float(np.percentile(pw, 99))}
    return out


def wealth_concentration(w: np.ndarray, tbill: float) -> dict:
    gain = w - 1.0
    order = np.sort(gain)[::-1]
    total = order[order > 0].sum() + order[order <= 0].sum()
    cum = np.cumsum(order)
    k = int(np.searchsorted(cum, total)) + 1 if total > 0 else len(order)
    return {"share_below_tbill": float((w < tbill).mean()), "share_bust": float((w == 0).mean()),
            "share_lose_money": float((w < 1).mean()), "top_share_all_net_wealth": k / len(w),
            "best": float(w.max()), "n_x100": int((w >= 100).sum()), "n_x1000": int((w >= 1000).sum())}


def empirical(prices: dict, years: int = 10, n: int = 50_000, seed: int = 58) -> dict:
    """Real stocks: 10-year multiples from the first available month ≥ 2009 (survivors only)."""
    mult = {}
    for t, s in prices.items():
        s = pd.Series(s).dropna()
        if len(s) < 250 * years:
            continue
        idx = pd.to_datetime(s.index)
        s.index = idx.tz_localize(None) if idx.tz is not None else idx
        start = s.index[0]
        end_v = s[s.index <= start + pd.DateOffset(years=years)]
        # penny stocks / broken adjusted prices (e.g. ×1,000,000 artefacts) are excluded
        if len(end_v) and s.iloc[0] >= 1.0 and 0 < end_v.iloc[-1] / s.iloc[0] <= 1000:
            mult[t] = float(end_v.iloc[-1] / s.iloc[0])
    if len(mult) < 50:
        return {"n_stocks": len(mult)}
    w = np.array(list(mult.values()))
    res = {"n_stocks": len(w), "share_x10": float((w >= 10).mean()), "share_lose": float((w < 1).mean()),
           "median": float(np.median(w)), "best": max(mult, key=mult.get), "best_multiple": float(w.max())}
    res["pickers"] = pickers(w, sizes=(1, 5), n=n, seed=seed)
    return res


def run_experiment58_report(prices: dict | None = None, spy: pd.Series | None = None) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #58 — luck simulation: zero-skill investors ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("Nobody simulated here has any skill. Every 'success' below is luck.")
    L.append("")
    g = coin_gurus()
    L.append("## A Coin-flip gurus (68 gurus × 97 forecasts, each a coin flip)")
    L.append(f"- Best guru (median over 2,000 simulated worlds): **{100*g['best_median']:.0f}% right**; worst: "
             f"**{100*g['worst_median']:.0f}%**.")
    L.append(f"- Share of gurus ≥ 60 % right: {100*g['share_ge_60']:.1f}%; ≤ 40 %: {100*g['share_le_40']:.1f}%.")
    L.append(f"- Chance that at least one guru reaches ≥ 65 %: {100*g['p_best_ge_65']:.0f}%; at least one ≤ 30 %: "
             f"{100*g['p_worst_le_30']:.0f}%.")
    L.append("- Compare CXO Advisory (real gurus 2005–2012): average 47 %. A spread like this is what pure chance "
             "produces — a 'star' guru with 65 % is expected even if nobody can forecast.")
    L.append("")
    m = managers()
    L.append(f"## B {m['n']:,} skill-less fund managers (fee {100*m['fee']:.0f} %, tracking error {100*m['te']:.0f} %)")
    L.append(f"- Beat the index **5 years in a row** (years 1–5): **{m['beat_5_in_row_first5']}** managers.")
    L.append(f"- Beat the index **10 years in a row**: **{m['beat_10_in_row_first10']}**.")
    L.append(f"- A winning streak of ≥ 5 years somewhere in 15 years: {m['max_streak_ge_5']}; ≥ 8 years: {m['max_streak_ge_8']}.")
    L.append(f"- 'Statistically proven' skill after 10 years (t > 2): **{m['t10_gt_2']}** — all pure luck.")
    L.append(f"- Behind the index after 15 years: **{100*m['share_behind_after_15y']:.0f}%** (fees). "
             f"Top 1 % are ahead by {100*m['top1pct_cum15']:+.0f}% — and would be on magazine covers.")
    L.append("")
    sm = stock_market()
    wc = wealth_concentration(sm["w"], sm["tbill_multiple"])
    L.append("## C Simulated stock market: 10,000 stocks, 20 years, no skill anywhere")
    L.append(f"Average stock (= equal-weight index) ×{sm['market_multiple']:.1f}; T-bills ×{sm['tbill_multiple']:.1f}.")
    L.append(f"- Stocks below T-bills after 20 years: **{100*wc['share_below_tbill']:.0f}%**; lost money: "
             f"{100*wc['share_lose_money']:.0f}%; went bust: {100*wc['share_bust']:.0f}%.")
    L.append(f"- The best **{100*wc['top_share_all_net_wealth']:.1f}%** of stocks create ALL net wealth of the market "
             f"(Bessembinder: ~4 % for US 1926–2016).")
    L.append(f"- ×100 stocks: {wc['n_x100']}; ×1000: {wc['n_x1000']}; best ×{wc['best']:.0f} — produced by luck in a "
             f"market where nobody can forecast.")
    L.append("")
    L.append("| random investor holds | made ×10 | made ×100 | lost money | median multiple | top 1 % multiple |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for k, v in pickers(sm["w"]).items():
        L.append(f"| {k} stock{'s' if k > 1 else ''} | {100*v['x10']:.1f}% | {100*v['x100']:.2f}% | {100*v['lost']:.0f}% | "
                 f"×{v['median']:.1f} | ×{v['p99']:.0f} |")
    L.append(f"| the whole market | — | — | — | ×{sm['market_multiple']:.1f} | — |")
    L.append("")
    sens = []
    for iv in (0.35, 0.45):
        s2 = stock_market(idio=iv)
        w2 = wealth_concentration(s2["w"], s2["tbill_multiple"])
        sens.append(f"idio {int(iv*100)} %: below T-bills {100*w2['share_below_tbill']:.0f}%, top "
                    f"{100*w2['top_share_all_net_wealth']:.1f}% create all net wealth")
    L.append("Sensitivity: " + "; ".join(sens) + ".")
    L.append("")
    L.append("Reading: a 1-stock investor has the best chance of a spectacular story AND the highest chance of losing. "
             "Social media shows the winners; the many losers made the same 'analysis'.")
    L.append("")
    L.append("## D Reality check with real US stocks (Yahoo, survivors only → biased upwards)")
    if prices:
        e = empirical(prices)
        if e.get("n_stocks", 0) >= 50:
            L.append(f"{e['n_stocks']:,} stocks with ≥ 10 years of data: ×10 or more: **{100*e['share_x10']:.1f}%**, "
                     f"lost money: {100*e['share_lose']:.0f}%, median ×{e['median']:.1f}, best {e['best']} ×{e['best_multiple']:.0f}.")
            for k, v in e["pickers"].items():
                L.append(f"- random {k}-stock portfolio: ×10 {100*v['x10']:.1f}%, lost {100*v['lost']:.0f}%, median ×{v['median']:.1f}")
            if spy is not None and len(spy) > 2500:
                s = pd.Series(spy).dropna()
                L.append(f"- SPY over the same kind of window (first 10 years of data): ×{s.iloc[min(len(s)-1, 2520)] / s.iloc[0]:.1f}")
        else:
            L.append(f"Too few stocks with 10 years of data ({e.get('n_stocks', 0)}).")
    else:
        L.append("No price data.")
    L.append("")
    L.append("Parameters in B and C are assumptions (stated above), chosen to be realistic, not favourable to any thesis.")
    return "\n".join(L)
