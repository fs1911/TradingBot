"""
Experiment #100 — following anonymous public trading accounts (requested 24.11.2026).

A  Robinhood herding (Robintrack, 2018-05 → 2020-08: number of Robinhood accounts holding each stock,
   hourly; the site is gone, the server looks for the export in the Internet Archive).
   Literature: Barber, Huang, Odean & Schwarz (2022) — stocks with Robinhood buying herds underperform.
   Pre-registered:
     herd event  users at day-end ≥ 1.5 × users the previous day-end, previous ≥ 100 users,
                 price ≥ 1 $; entry at the close of the NEXT trading day.
     outcome     1 / 5 / 20 trading days, minus SPY; t clustered by event date; random-day control
                 (same stocks, all their days).
     weekly      each Friday, top vs bottom decile of 1-week user growth (stocks ≥ 1000 users) →
                 next-week return spread vs SPY (t over weeks).
B  Crypto exchange flows (CoinMetrics community, BTC and ETH): net flow onto exchanges over the last
   7 days ÷ exchange supply. Inflow is read as selling pressure (negative expected), outflow as buying.
     IC          month-end signal vs next 30 days return (Spearman, permutation p, non-overlapping).
     events      top 5 % net-inflow days and top 5 % net-outflow days (30-day quiet period) →
                 next 7 / 30 days vs all days.
Holm over the primary tests (A herd 5 d, A herd 20 d, B BTC IC, B ETH IC).
Pure, injected for CI; network helpers are thin.
"""
from __future__ import annotations
import io
import math
import tarfile
import numpy as np
import pandas as pd

from .experiments_88_90 import monthly_ic, perm_p, first_cross

HERD_RATIO, HERD_MIN = 1.5, 100
CM_FLOW_METRICS = ("FlowInExNtv", "FlowOutExNtv", "SplyExNtv", "PriceUSD")


# ---------------------------------------------------------------- A: Robintrack

def parse_robintrack_tar(fileobj, min_max_users: int = 100) -> pd.DataFrame:
    """Robintrack export (tar.gz of <TICKER>.csv with timestamp, users_holding) → daily DataFrame
    (index date, columns tickers, value = users at the last observation of the day)."""
    cols = {}
    with tarfile.open(fileobj=fileobj, mode="r|gz") as tf:
        for m in tf:
            if not m.isfile() or not m.name.lower().endswith(".csv"):
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                d = pd.read_csv(io.BytesIO(f.read()))
            except Exception:
                continue
            if d.shape[1] < 2:
                continue
            ts = pd.to_datetime(d.iloc[:, 0], errors="coerce", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
            u = pd.to_numeric(d.iloc[:, 1], errors="coerce")
            s = pd.Series(u.to_numpy(), index=ts).dropna()
            s = s[s.index.notna()]
            if s.empty or s.max() < min_max_users:
                continue
            tk = m.name.rsplit("/", 1)[-1][:-4].upper()
            cols[tk] = s.groupby(s.index.normalize()).last().astype("float32")
    return pd.DataFrame(cols).sort_index()


def herd_events(users: pd.DataFrame, ratio: float = HERD_RATIO, min_prev: int = HERD_MIN) -> pd.DataFrame:
    prev = users.shift(1)
    hit = (users >= ratio * prev) & (prev >= min_prev)
    rows = [(d, t) for t in users.columns for d in users.index[hit[t].fillna(False).to_numpy()]]
    return pd.DataFrame(rows, columns=["date", "ticker"])


def event_returns(ev: pd.DataFrame, px: dict, spy: pd.Series, horizons=(1, 5, 20), min_price: float = 1.0) -> pd.DataFrame:
    """Entry at the close of the first trading day AFTER the event date."""
    out = []
    for d, t in ev.itertuples(index=False):
        p = px.get(t)
        if p is None or len(p) < 30:
            continue
        i = p.index.searchsorted(d, side="right")
        if i >= len(p) or p.iloc[i] < min_price:
            continue
        j = spy.index.searchsorted(p.index[i])
        if j >= len(spy):
            continue
        row = {"date": d, "ticker": t}
        for h in horizons:
            if i + h < len(p) and j + h < len(spy):
                row[h] = p.iloc[i + h] / p.iloc[i] - 1 - (spy.iloc[j + h] / spy.iloc[j] - 1)
            else:
                row[h] = np.nan
        out.append(row)
    return pd.DataFrame(out)


def random_day_returns(px: dict, spy: pd.Series, tickers, horizons=(1, 5, 20), per: int = 60, seed: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for t in tickers:
        p = px.get(t)
        if p is None or len(p) < 60:
            continue
        for d in rng.choice(p.index[:-25], size=min(per, len(p) - 25), replace=False):
            rows.append((pd.Timestamp(d), t))
    return event_returns(pd.DataFrame(rows, columns=["date", "ticker"]), px, spy, horizons)


def clustered_t(df: pd.DataFrame, col) -> tuple:
    x = df[["date", col]].dropna()
    if len(x) < 10:
        return np.nan, np.nan, 0
    g = x.groupby("date")[col].mean()
    if len(g) < 5 or g.std() == 0:
        return float(x[col].mean()), np.nan, len(x)
    return float(x[col].mean()), float(g.mean() / g.std(ddof=1) * math.sqrt(len(g))), len(x)


def weekly_spread(users: pd.DataFrame, px: dict, spy: pd.Series, min_users: int = 1000) -> pd.Series:
    """Friday sort on 1-week user growth; top − bottom decile next-week return (vs SPY)."""
    fri = users.resample("W-FRI").last()
    growth = fri / fri.shift(1) - 1
    big = fri.shift(1) >= min_users
    pxw = pd.DataFrame({t: p.resample("W-FRI").last() for t, p in px.items() if t in users.columns})
    spyw = spy.resample("W-FRI").last()
    nxt = pxw.pct_change().shift(-1).sub(spyw.pct_change().shift(-1), axis=0)
    out = {}
    for w in growth.index:
        g = growth.loc[w][big.loc[w].fillna(False)].dropna()
        if w not in nxt.index:
            continue
        r = nxt.loc[w].reindex(g.index).dropna()
        g = g.reindex(r.index)
        if len(g) < 50:
            continue
        q = g.rank(pct=True)
        out[w] = r[q >= 0.9].mean() - r[q <= 0.1].mean()
    return pd.Series(out)


# ---------------------------------------------------------------- B: crypto flows

def flow_signal(df: pd.DataFrame, days: int = 7) -> pd.Series:
    """Net exchange inflow over `days` ÷ exchange supply (positive = coins moving ONTO exchanges)."""
    if not {"FlowInExNtv", "FlowOutExNtv"} <= set(df.columns):
        return pd.Series(dtype=float)
    net = (df["FlowInExNtv"] - df["FlowOutExNtv"]).rolling(days).sum()
    den = df["SplyExNtv"] if "SplyExNtv" in df else df["FlowInExNtv"].rolling(365, min_periods=60).sum()
    return (net / den).replace([np.inf, -np.inf], np.nan)


def flow_events(sig: pd.Series, px: pd.Series, q: float, above: bool, horizons=(7, 30)) -> dict:
    s = sig.dropna()
    if len(s) < 400:
        return {}
    thr = s.quantile(q)
    days = first_cross(s, (lambda v: v >= thr) if above else (lambda v: v <= thr), quiet=30)
    res = {"n": len(days)}
    for h in horizons:
        ev = [px.asof(d + pd.Timedelta(days=h)) / px.asof(d) - 1 for d in days
              if d + pd.Timedelta(days=h) <= px.index[-1] and px.asof(d) > 0]
        allr = (px.shift(-h) / px - 1).dropna()
        res[h] = (float(np.mean(ev)) if ev else np.nan, float(allr.mean()))
    return res


def holm(p: dict) -> dict:
    items = sorted((v, k) for k, v in p.items() if np.isfinite(v))
    m, out, run = len(items), {}, 0.0
    for i, (v, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    return out


def _p_from_t(t: float) -> float:
    return float(math.erfc(abs(t) / math.sqrt(2))) if np.isfinite(t) else float("nan")


def run_experiment100_report(users: pd.DataFrame | None, px: dict, spy: pd.Series | None, flows: dict,
                             diag: list | None = None) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #100 — following anonymous public trading accounts ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if diag:
        L += [" ".join(diag), ""]
    pc = lambda x: f"{100*x:+.2f} %" if np.isfinite(x) else "—"
    f = lambda x, d=2: f"{x:+.{d}f}" if np.isfinite(x) else "—"
    pv = {}
    # A
    L.append("## A Robinhood herding (Robintrack)")
    if users is None or users.empty or spy is None:
        L += ["Robintrack data not available — part A not run.", ""]
    else:
        ev = herd_events(users)
        er = event_returns(ev, px, spy)
        L.append(f"{users.shape[1]:,} stocks with ≥ {HERD_MIN} users, {users.index[0]:%Y-%m-%d} → {users.index[-1]:%Y-%m-%d}; "
                 f"{len(ev):,} herd events, {len(er):,} with prices.")
        ctrl = random_day_returns(px, spy, sorted(set(er["ticker"])) if len(er) else [])
        L.append("| horizon | herd events: mean vs SPY | t (clustered by day) | median | random days of the same stocks |")
        L.append("|---|--:|--:|--:|--:|")
        for h in (1, 5, 20):
            if len(er) == 0:
                break
            m, t, n = clustered_t(er, h)
            c = ctrl[h].mean() if len(ctrl) else np.nan
            L.append(f"| {h} d | {pc(m)} (n {n:,}) | {f(t)} | {pc(er[h].median())} | {pc(c)} |")
            if h in (5, 20):
                pv[f"A herd {h} d"] = _p_from_t(t)
        ws = weekly_spread(users, px, spy)
        if len(ws) > 10:
            tw = ws.mean() / ws.std(ddof=1) * math.sqrt(len(ws))
            L.append(f"- Weekly: top − bottom decile of user growth, next week vs SPY: {pc(ws.mean())} per week (t {f(tw)}, {len(ws)} weeks).")
        L.append("")
    # B
    L.append("## B Crypto exchange flows (CoinMetrics community)")
    if not flows:
        L += ["No flow data available — part B not run.", ""]
    for asset, df in flows.items():
        sig = flow_signal(df)
        if sig.dropna().empty or "PriceUSD" not in df:
            L.append(f"- {asset}: flow metrics missing ({', '.join(df.columns) or 'none'}).")
            continue
        px_ = df["PriceUSD"].dropna()
        ic = monthly_ic(sig, px_, 30)
        if ic:
            pv[f"B {asset} IC"] = ic.get("p", np.nan)
            L.append(f"- {asset} ({sig.dropna().index[0]:%Y}→): month-end net inflow vs next 30 days: Spearman {f(ic.get('ic', np.nan))}, "
                     f"permutation p {f(ic.get('p', np.nan), 3)}, {ic.get('n', 0)} months (negative = inflow → weaker price, as expected).")
        for lab, q, ab in (("top 5 % inflow (selling pressure?)", 0.95, True), ("top 5 % outflow (accumulation?)", 0.05, False)):
            r = flow_events(sig, px_, q, ab)
            if r:
                L.append(f"  - {lab}: {r['n']} events; next 7 d {pc(r[7][0])} (all days {pc(r[7][1])}), next 30 d {pc(r[30][0])} (all days {pc(r[30][1])})")
    L.append("")
    adj = holm(pv)
    if pv:
        L.append("Primary tests, Holm-corrected: " + "; ".join(f"{k}: p {f(v, 3)}, Holm {f(adj.get(k, np.nan), 3)}" for k, v in pv.items()))
    L.append("")
    L.append("Caveats: Robintrack covers one broker and 2018–2020 only; delisted tickers lack Yahoo prices; "
             "CoinMetrics exchange attribution is incomplete (unlabelled wallets).")
    return "\n".join(L)
