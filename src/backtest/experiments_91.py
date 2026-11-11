"""
Experiment #91 — case study: the Nvidia drop of Oct/Nov 2026 (requested 11.11.2026).

1. News timeline (Alpaca/Benzinga, NVDA, from mid-September): articles per day, word-list tone
   (#87 lists), the most negative / positive headlines, and NVDA's move on the day and the next day.
2. Trend rules — when would each have turned red after the 6 Oct 2026 peak, and what did it save
   by today? Rules (signal from closes up to day t, acted on at the close of day t):
     A close < 200-day average (daily)        B month-end close < 10-month average (monthly)
     C 50-day average < 200-day average       D trailing stop: 20 % below the running high,
                                                re-entry when the close is back above the 200-day avg.
3. Cross-check over every NVDA drawdown ≥ 25 % since 2015: return of each rule vs buy & hold over the
   episode (peak → trough) AND over the 12 months after the trough (cost of being out of the rebound),
   plus full-period CAGR, max drawdown and number of trades.
4. Position size: what the drop means for a portfolio holding 5 / 10 / 25 / 100 % in NVDA.
Pure, injected for CI.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .experiments_87 import text_tone


def rule_signals(px: pd.Series) -> dict:
    """{name: 0/1 Series (1 = invested)} using only information up to each day."""
    px = px.astype(float)
    sma50, sma200 = px.rolling(50).mean(), px.rolling(200).mean()
    a = (px >= sma200).astype(float).where(sma200.notna())
    # B: monthly 10-month average, held until the next month end
    me = px.resample("ME").last()
    sig_m = (me >= me.rolling(10).mean()).astype(float).where(me.rolling(10).mean().notna())
    b = sig_m.reindex(px.index, method="ffill")
    c = (sma50 >= sma200).astype(float).where(sma200.notna())
    # D: trailing stop with re-entry above the 200-day average
    d, inv, hi = [], 1.0, -np.inf
    for p, s2 in zip(px.to_numpy(), sma200.to_numpy()):
        if inv:
            hi = max(hi, p)
            if p <= 0.8 * hi:
                inv = 0.0
        elif np.isfinite(s2) and p > s2:
            inv, hi = 1.0, p
        d.append(inv)
    d = pd.Series(d, index=px.index)
    return {"A close < 200-day avg": a, "B month-end < 10-month avg": b, "C 50-day < 200-day avg": c,
            "D −20 % trailing stop": d}


def strategy_returns(px: pd.Series, sig: pd.Series) -> pd.Series:
    r = px.pct_change()
    return (sig.shift(1).fillna(1.0) * r).fillna(0.0)


def stats(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    yrs = max((r.index[-1] - r.index[0]).days / 365.25, 1e-9)
    return {"cagr": float(eq.iloc[-1] ** (1 / yrs) - 1), "maxdd": float((eq / eq.cummax() - 1).min())}


def drawdown_episodes(px: pd.Series, threshold: float = 0.25) -> list:
    """Non-overlapping (peak, trough) pairs with a fall ≥ threshold; peak = high before the trough."""
    out, peak_d, peak_v, trough_d, trough_v, in_dd = [], px.index[0], px.iloc[0], None, None, False
    for d, v in px.items():
        if v > peak_v and not in_dd:
            peak_d, peak_v = d, v
        dd = v / peak_v - 1
        if dd <= -threshold:
            in_dd = True
            if trough_v is None or v < trough_v:
                trough_d, trough_v = d, v
        if in_dd and v >= peak_v:  # recovered → close episode
            out.append((peak_d, trough_d)); in_dd = False
            peak_d, peak_v, trough_d, trough_v = d, v, None, None
    if in_dd:
        out.append((peak_d, trough_d))
    return out


def period_ret(r: pd.Series, a, b) -> float:
    x = r[(r.index > a) & (r.index <= b)]
    return float((1 + x).prod() - 1)


def news_timeline(arts: pd.DataFrame, px: pd.Series, top: int = 2) -> list:
    """arts: [ts, headline] → rows (date, n, tone, worst headline, best headline, ret day, ret next day)."""
    if arts.empty:
        return []
    df = arts.copy()
    df["day"] = df["ts"].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    df["tone"] = [text_tone(h) for h in df["headline"]]
    ret = px.pct_change()
    rows = []
    for day, g in df.groupby("day"):
        g = g.sort_values("tone")
        k = px.index.searchsorted(day)
        r0 = float(ret.iloc[k]) if k < len(px) and px.index[k] == day else np.nan
        k1 = px.index.searchsorted(day, side="right")
        r1 = float(ret.iloc[k1]) if k1 < len(px) else np.nan
        rows.append((day, len(g), float(g["tone"].mean()), g["headline"].iloc[0][:110], g["headline"].iloc[-1][:110], r0, r1))
    return rows


def run_experiment91_report(px: pd.Series, spy: pd.Series, arts: pd.DataFrame, peak: str = "2026-10-06",
                            diag: list | None = None) -> str:
    from datetime import datetime, timezone
    px = px.astype(float).dropna()
    L = [f"# Experiment #91 — case study Nvidia, Oct/Nov 2026 ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    pk = px.loc[pd.Timestamp(peak) - pd.Timedelta(days=10):pd.Timestamp(peak) + pd.Timedelta(days=10)].idxmax()
    last = px.index[-1]
    L.append(f"Peak {pk:%Y-%m-%d} close {px[pk]:.2f} → {last:%Y-%m-%d} close {px[last]:.2f} "
             f"(**{100*(px[last]/px[pk]-1):+.1f} %**; S&P 500 ETF {100*(spy.asof(last)/spy.asof(pk)-1):+.1f} %).")
    L.append("")
    # 1 news
    L.append("## 1 News timeline (Benzinga via Alpaca; tone = word lists from #87, −1 … +1)")
    tl = news_timeline(arts, px)
    if not tl:
        L.append("No articles available.")
    else:
        L.append("| day (NY) | articles | tone | NVDA that day | next day | most negative headline |")
        L.append("|---|--:|--:|--:|--:|---|")
        for day, n, t, worst, best, r0, r1 in tl:
            if day < pk - pd.Timedelta(days=21):
                continue
            f = lambda x: f"{100*x:+.1f} %" if np.isfinite(x) else "closed"
            L.append(f"| {day:%a %d.%m.} | {n} | {t:+.2f} | {f(r0)} | {f(r1)} | {worst.replace('|', '/')} |")
    L.append("")
    # 2 rules in the current episode
    sigs = rule_signals(px)
    L.append(f"## 2 Trend rules after the peak of {pk:%d.%m.%Y}")
    L.append("| rule | turned red on | close then | fall from peak at exit | NVDA since exit | saved vs holding |")
    L.append("|---|---|--:|--:|--:|--:|")
    for name, s in sigs.items():
        after = s[s.index > pk]
        red = after[after == 0]
        if len(red) == 0:
            L.append(f"| {name} | still invested | — | — | — | 0 |")
            continue
        d = red.index[0]
        L.append(f"| {name} | {d:%a %d.%m.%Y} | {px[d]:.2f} | {100*(px[d]/px[pk]-1):+.1f} % | "
                 f"{100*(px[last]/px[d]-1):+.1f} % | {100*(px[d]/px[pk] - px[last]/px[pk]):+.1f} %-pts |")
    L.append("")
    # 3 history
    eps = drawdown_episodes(px[px.index < pk - pd.Timedelta(days=1)])
    L.append(f"## 3 Cross-check: every NVDA drawdown ≥ 25 % from {px.index[0]:%Y} to the peak (n {len(eps)})")
    bh = px.pct_change().fillna(0.0)
    rs = {name: strategy_returns(px, s) for name, s in sigs.items()}
    L.append("| episode (peak → trough) | buy & hold | " + " | ".join(n.split(" ")[0] for n in rs) + " | B&H next 12 M after trough | "
             + " | ".join(n.split(" ")[0] + " next 12 M" for n in rs) + " |")
    L.append("|---|--:|" + "--:|" * len(rs) + "--:|" + "--:|" * len(rs))
    for a, b in eps:
        c12 = b + pd.Timedelta(days=365)
        L.append(f"| {a:%m.%Y} → {b:%m.%Y} | {100*period_ret(bh, a, b):+.0f} % | "
                 + " | ".join(f"{100*period_ret(r, a, b):+.0f} %" for r in rs.values())
                 + f" | {100*period_ret(bh, b, c12):+.0f} % | " + " | ".join(f"{100*period_ret(r, b, c12):+.0f} %" for r in rs.values()) + " |")
    L.append("")
    L.append("Whole period (to today, before costs and taxes):")
    L.append("| | CAGR | max drawdown | switches |")
    L.append("|---|--:|--:|--:|")
    st = stats(bh)
    L.append(f"| buy & hold | {100*st['cagr']:+.1f} % | {100*st['maxdd']:.0f} % | 0 |")
    for name, r in rs.items():
        st = stats(r)
        sw = int(sigs[name].fillna(1).diff().abs().sum())
        L.append(f"| {name} | {100*st['cagr']:+.1f} % | {100*st['maxdd']:.0f} % | {sw} |")
    L.append("")
    # 4 position size
    fall = px[last] / px[pk] - 1
    L.append("## 4 Position size — effect of this fall on the whole portfolio (rest unchanged)")
    L.append("| NVDA share of portfolio | 5 % | 10 % | 25 % | 100 % |")
    L.append("|---|--:|--:|--:|--:|")
    L.append("| portfolio change | " + " | ".join(f"{100*w*fall:+.1f} %" for w in (0.05, 0.10, 0.25, 1.0)) + " |")
    L.append("")
    L.append("Caveats: one stock, one episode; trend rules are judged on all NVDA drawdowns above, not on this one. "
             "Prices are closes (a weekend news gap cannot be avoided by any rule).")
    return "\n".join(L)
