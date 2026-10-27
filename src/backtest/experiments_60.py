"""
Experiment #60 — the "live data" hypothesis: is there short-term predictability in
minute data, and does anything survive spreads and fees?

User thesis: without live data you cannot make big gains. Here we use the finest data
we can get for free (Alpaca minute bars: IEX feed for stocks, Alpaca crypto) and ask:

  A How predictable are minute returns at all? Autocorrelation (lags 1–5) and variance
    ratios (q = 2, 4, 8, 16) per symbol and bar size (1, 5, 15, 60 minutes).
  B Six pre-registered short-term rules, positions decided on the COMPLETED bar and held
    for the next bar(s); stocks strictly within the session (flat overnight):
      R1 momentum   sign of the last bar           R2 reversal   minus that sign
      R3 z-reversal price vs 20-bar mean, |z| > 2  R4 breakout   new 60-bar high/low, 5 bars
      R5 opening-range breakout (stocks)           R6 last-30-minutes drift (stocks)
    Gross return per position change and the BREAK-EVEN COST per side; net results at
    realistic costs (stocks 1 and 3 bp per side; crypto 25 bp = measured Alpaca fee,
    and 5 bp = cheapest large exchange).
  C Selection honesty: the best rule/bar size in the first half → its second half.
  D Placebo: random positions with the same exposure and turnover.
Caveat in the report: bar data ≠ the sub-millisecond speed of HFT firms; their edge is
infrastructure (co-location, order flow, rebates), which no retail data feed can test.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

STOCKS = ["SPY", "QQQ", "IWM", "AAPL", "NVDA", "TSLA"]
CRYPTO = ["BTC/USD", "ETH/USD"]
COSTS_BP = {"stock": (1.0, 3.0), "crypto": (5.0, 25.0)}
BARS = (1, 5, 15, 60)


def _utc(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tz is None else t.tz_convert("UTC")


def month_edges(start, end) -> pd.DatetimeIndex:
    """[start, first of each month …, end], all tz-aware UTC (inputs may be naive or aware)."""
    a, b = _utc(start), _utc(end)
    mid = pd.date_range(a, b, freq="MS")
    return pd.DatetimeIndex([a]).append(mid[mid > a]).append(pd.DatetimeIndex([b]))


def fetch_bars(data_client, crypto_client, symbol: str, start, end, minutes: int, log=None) -> pd.DataFrame:
    """Minute bars in monthly chunks (alpaca-py paginates within a request)."""
    from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    tf = TimeFrame(minutes, TimeFrameUnit.Minute) if minutes < 60 else TimeFrame(1, TimeFrameUnit.Hour)
    parts = []
    edges = month_edges(start, end)
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            continue
        try:
            if "/" in symbol:
                df = crypto_client.get_crypto_bars(CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=tf,
                                                                     start=a, end=b)).df
            else:
                df = data_client.get_stock_bars(StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf,
                                                                 start=a, end=b, feed="iex")).df
        except Exception as e:
            if log:
                log(f"#60 {symbol} {a:%Y-%m}: {repr(e)[:80]}")
            continue
        if df is not None and len(df):
            df = df.reset_index()
            df = df.rename(columns={"timestamp": "t"}).set_index("t")[["open", "high", "low", "close", "volume"]]
            parts.append(df)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index = pd.to_datetime(out.index, utc=True)
    return out


def session_mask(idx: pd.DatetimeIndex, is_stock: bool) -> pd.Series:
    """Day key; stocks: regular session only (09:30–16:00 New York)."""
    ny = idx.tz_convert("America/New_York")
    day = pd.Series(ny.normalize(), index=idx)
    if not is_stock:
        return day, pd.Series(True, index=idx)
    mins = ny.hour * 60 + ny.minute
    return day, pd.Series((mins >= 570) & (mins < 960), index=idx)


def resample(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if minutes == 1 or df.empty:
        return df
    o = df.resample(f"{minutes}min", label="left", closed="left")
    out = pd.DataFrame({"open": o["open"].first(), "high": o["high"].max(), "low": o["low"].min(),
                        "close": o["close"].last(), "volume": o["volume"].sum()}).dropna(subset=["close"])
    return out


def bar_returns(df: pd.DataFrame, is_stock: bool) -> pd.DataFrame:
    """Close-to-close returns within the same day/session; columns r, day, last (last bar of day)."""
    day, ok = session_mask(df.index, is_stock)
    d = pd.DataFrame({"c": df["close"].to_numpy(), "day": day.to_numpy(), "ok": ok.to_numpy()}, index=df.index)
    d = d[d["ok"]]
    d["r"] = d.groupby("day")["c"].pct_change()
    d["last"] = d["day"] != d["day"].shift(-1)
    d["first"] = d["day"] != d["day"].shift(1)
    return d


def autocorr(r: pd.Series, lags=(1, 2, 3, 4, 5)) -> dict:
    r = r.dropna()
    n = len(r)
    out = {}
    for k in lags:
        rho = r.autocorr(k) if n > k + 10 else float("nan")
        out[k] = (float(rho), float(rho * math.sqrt(n)) if np.isfinite(rho) else float("nan"))
    return out


def variance_ratio(r: pd.Series, q: int) -> tuple:
    """Lo–MacKinlay VR(q) with homoskedastic z (overlapping sums)."""
    r = r.dropna().to_numpy()
    n = len(r)
    if n < q * 20:
        return float("nan"), float("nan")
    mu = r.mean()
    v1 = ((r - mu) ** 2).sum() / (n - 1)
    rq = np.convolve(r, np.ones(q), "valid")
    vq = ((rq - q * mu) ** 2).sum() / (q * (n - q + 1) * (1 - q / n))
    vr = vq / v1
    z = (vr - 1) / math.sqrt(2 * (2 * q - 1) * (q - 1) / (3 * q * n))
    return float(vr), float(z)


def positions(d: pd.DataFrame, rule: str, is_stock: bool, minutes: int) -> pd.Series:
    """Position held during the NEXT bar (decided on the completed bar). Flat on the last
    bar of each day (stocks)."""
    r, c = d["r"].fillna(0.0), d["c"]
    if rule == "R1 momentum":
        p = np.sign(r)
    elif rule == "R2 reversal":
        p = -np.sign(r)
    elif rule == "R3 z-reversal":
        m, s = c.rolling(20).mean(), c.rolling(20).std()
        z = (c - m) / s
        p = pd.Series(np.where(z < -2, 1.0, np.where(z > 2, -1.0, 0.0)), index=d.index)
    elif rule == "R4 breakout":
        hi, lo = c.rolling(60).max().shift(1), c.rolling(60).min().shift(1)
        sig = pd.Series(np.where(c > hi, 1.0, np.where(c < lo, -1.0, np.nan)), index=d.index)
        p = sig.ffill(limit=4).fillna(0.0)
    elif rule == "R5 opening range" and is_stock:
        ny = d.index.tz_convert("America/New_York")
        mins = pd.Series(ny.hour * 60 + ny.minute, index=d.index)
        in_or = mins < 600
        orh = c.where(in_or).groupby(d["day"]).transform("max")
        orl = c.where(in_or).groupby(d["day"]).transform("min")
        raw = pd.Series(np.where(~in_or & (c > orh), 1.0, np.where(~in_or & (c < orl), -1.0, np.nan)), index=d.index)
        first = raw.groupby(d["day"]).transform(lambda x: x.dropna().iloc[0] if x.notna().any() else 0.0)
        started = raw.notna().groupby(d["day"]).cummax()
        p = (first * started).astype(float)
    elif rule == "R6 last 30 min" and is_stock:
        ny = d.index.tz_convert("America/New_York")
        mins = pd.Series(ny.hour * 60 + ny.minute, index=d.index)
        p = pd.Series(np.where(mins + minutes > 930, 1.0, 0.0), index=d.index)
    else:
        return pd.Series(dtype=float)
    p = pd.Series(p, index=d.index).astype(float)
    if is_stock:
        p[d["last"]] = 0.0
    return p


def evaluate(d: pd.DataFrame, pos: pd.Series) -> dict:
    """Gross P&L of holding `pos` (set at bar t) over bar t+1."""
    nxt = d["r"].shift(-1).fillna(0.0)
    same_day = d["day"] == d["day"].shift(-1)
    pnl = (pos * nxt).where(same_day, 0.0)
    turn = pos.diff().abs().fillna(pos.abs())
    n_turn = float(turn.sum())
    gross = float(pnl.sum())
    daily = pnl.groupby(d["day"]).sum()
    t = float(daily.mean() / daily.std() * math.sqrt(len(daily))) if daily.std() > 0 else float("nan")
    return {"gross_total": gross, "turnover": n_turn, "days": len(daily),
            "exposure": float((pos != 0).mean()),
            "bp_per_side": (gross / n_turn * 1e4) if n_turn > 0 else float("nan"),
            "t_gross": t, "daily": daily, "turn_daily": turn.groupby(d["day"]).sum()}


def net_ann(ev: dict, cost_bp: float) -> float:
    daily = ev["daily"] - ev["turn_daily"] * cost_bp / 1e4
    return float(daily.mean() * 252) if len(daily) else float("nan")


def placebo_p(d: pd.DataFrame, pos: pd.Series, ev: dict, n: int = 200, seed: int = 60) -> float:
    """Circularly shifted position series (same exposure/turnover, timing destroyed)."""
    rng = np.random.default_rng(seed)
    vals = pos.to_numpy()
    if len(vals) < 1000:
        return float("nan")
    hits = 0
    for _ in range(n):
        k = int(rng.integers(len(vals) // 10, len(vals) - len(vals) // 10))
        e = evaluate(d, pd.Series(np.roll(vals, k), index=pos.index))
        hits += e["gross_total"] >= ev["gross_total"]
    return (hits + 1) / (n + 1)


RULES = ("R1 momentum", "R2 reversal", "R3 z-reversal", "R4 breakout", "R5 opening range", "R6 last 30 min")


def analyse_symbol(df1: pd.DataFrame, symbol: str) -> dict:
    is_stock = "/" not in symbol
    res = {"symbol": symbol, "is_stock": is_stock, "bars": {}, "first": None, "last": None}
    if df1 is None or df1.empty:
        return res
    res["first"], res["last"] = df1.index[0], df1.index[-1]
    for m in BARS:
        df = resample(df1, m)
        d = bar_returns(df, is_stock)
        if len(d) < 2000:
            continue
        cell = {"n": len(d), "ac": autocorr(d["r"]), "vr": {q: variance_ratio(d["r"], q) for q in (2, 4, 8, 16)},
                "rules": {}}
        half = d["day"].unique()
        cut = half[len(half) // 2] if len(half) > 20 else None
        for rule in RULES:
            pos = positions(d, rule, is_stock, m)
            if pos.empty or pos.abs().sum() == 0:
                continue
            ev = evaluate(d, pos)
            split = {}
            if cut is not None:
                for nm, mask in (("first", d["day"] < cut), ("second", d["day"] >= cut)):
                    split[nm] = evaluate(d[mask], pos[mask])
            cell["rules"][rule] = {"ev": ev, "split": split, "pos": pos}
        # placebo only for this bar size's best first-half rule (keeps memory/time bounded)
        firsts = [(rr["split"]["first"]["t_gross"], k) for k, rr in cell["rules"].items()
                  if rr["split"].get("first") and np.isfinite(rr["split"]["first"]["t_gross"])]
        if firsts:
            k = max(firsts)[1]
            rr = cell["rules"][k]
            rr["placebo_p"] = placebo_p(d, rr["pos"], rr["ev"], n=100)
        for rr in cell["rules"].values():
            rr.pop("pos", None)
        res["bars"][m] = cell
    res["n1"] = len(df1)
    return res


def run_experiment60_report(results: dict, n_trials: int = 300) -> str:
    """results: {symbol: analyse_symbol(1-minute bars)} (analysed one by one to bound memory)."""
    from datetime import datetime, timezone
    L = [f"# Experiment #60 — minute data: is there a short-term edge after costs? "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("Data: Alpaca 1-minute bars (stocks: free IEX feed, regular session only; crypto: Alpaca), "
             "resampled to 5/15/60 minutes. Positions decided on the completed bar, held for the next; stocks flat "
             "overnight. 'Break-even' = gross gain per position change ÷ 2 sides — what a trader may pay per side "
             f"(spread + fees + slippage) before the rule loses. Bonferroni α/{n_trials} → |t| ≳ 3.7.")
    L.append("")
    L.append("## Coverage")
    L.append("| symbol | from | to | 1-min bars |")
    L.append("|---|---|---|--:|")
    for sym, res in results.items():
        if res.get("first") is None:
            L.append(f"| {sym} | — | — | no data |")
            continue
        L.append(f"| {sym} | {res['first']:%Y-%m-%d} | {res['last']:%Y-%m-%d} | {res['n1']:,} |")
    L.append("")

    L.append("## A How predictable are minute returns? (autocorrelation lag 1 / variance ratio q=16)")
    L.append("| symbol | bar | n | ρ(1) (t) | ρ(2) (t) | VR(2) (z) | VR(16) (z) |")
    L.append("|---|--:|--:|--:|--:|--:|--:|")
    for sym, res in results.items():
        for m, cell in res["bars"].items():
            a1, a2 = cell["ac"][1], cell["ac"][2]
            v2, v16 = cell["vr"][2], cell["vr"][16]
            L.append(f"| {sym} | {m}m | {cell['n']:,} | {a1[0]:+.3f} ({a1[1]:+.1f}) | {a2[0]:+.3f} ({a2[1]:+.1f}) | "
                     f"{v2[0]:.3f} ({v2[1]:+.1f}) | {v16[0]:.3f} ({v16[1]:+.1f}) |")
    L.append("")
    L.append("ρ = correlation of a bar's return with the previous bar's; ±0.01 means 1 % of the next move is "
             "'explained'. VR < 1 = mean reversion, > 1 = trending.")
    L.append("")

    L.append("## B Six rules — gross edge and break-even cost per side")
    L.append("| symbol | bar | rule | position changes | in market | gross p.a. | t (gross) | break-even bp/side | "
             "net p.a. @ low cost | net p.a. @ realistic cost |")
    L.append("|---|--:|---|--:|--:|--:|--:|--:|--:|--:|")
    cand = []
    for sym, res in results.items():
        lo, hi = COSTS_BP["stock" if res["is_stock"] else "crypto"]
        for m, cell in res["bars"].items():
            for rule, rr in cell["rules"].items():
                ev = rr["ev"]
                yrs = ev["days"] / (252 if res["is_stock"] else 365)
                gross_pa = ev["gross_total"] / yrs if yrs > 0 else float("nan")
                be = ev["bp_per_side"] / 2 if np.isfinite(ev["bp_per_side"]) else float("nan")
                L.append(f"| {sym} | {m}m | {rule} | {ev['turnover']:,.0f} | {100*ev['exposure']:.0f}% | "
                         f"{100*gross_pa:+.1f}% | {ev['t_gross']:+.2f} | {be:+.2f} | "
                         f"{100*net_ann(ev, lo):+.0f}% ({lo:g} bp) | {100*net_ann(ev, hi):+.0f}% ({hi:g} bp) |")
                cand.append((sym, m, rule, rr, res, cell))
    L.append("")
    L.append("Realistic costs per side: liquid US stocks/ETFs ~1–3 bp (spread + slippage, no commission); "
             "crypto 25 bp at Alpaca (measured in this project), ~5 bp at the cheapest large exchanges.")
    L.append("")

    L.append("## C Selection honesty: best rule in the first half → second half")
    best = None
    for sym, m, rule, rr, res, cell in cand:
        f = rr["split"].get("first")
        if f and np.isfinite(f["t_gross"]) and (best is None or f["t_gross"] > best[0]):
            best = (f["t_gross"], sym, m, rule, rr, res, cell)
    if best:
        t1, sym, m, rule, rr, res, cell = best
        s = rr["split"]["second"]
        lo, hi = COSTS_BP["stock" if res["is_stock"] else "crypto"]
        L.append(f"Best in the first half (of {len(cand)} rule × bar × symbol combinations): **{sym} {m}m {rule}** "
                 f"(t {t1:+.2f}). Second half: gross t **{s['t_gross']:+.2f}**, break-even "
                 f"{s['bp_per_side']/2:+.2f} bp/side, net p.a. {100*net_ann(s, lo):+.0f}% @ {lo:g} bp, "
                 f"{100*net_ann(s, hi):+.0f}% @ {hi:g} bp.")
        p = rr.get("placebo_p", float("nan"))
        L.append(f"Placebo (same exposure and turnover, timing shifted; full sample, 100 shifts): p = {p:.3f}.")
    else:
        L.append("Not enough data for a split.")
    L.append("")
    n_sig = sum(1 for *_, rr, _r, _c in cand if abs(rr["ev"]["t_gross"]) > 3.7 and rr["ev"]["t_gross"] > 0)
    n_net = 0
    for sym, m, rule, rr, res, cell in cand:
        lo, hi = COSTS_BP["stock" if res["is_stock"] else "crypto"]
        if net_ann(rr["ev"], hi) > 0 and all(net_ann(v, hi) > 0 for v in rr["split"].values()):
            n_net += 1
    L.append(f"**Summary:** {n_sig} of {len(cand)} combinations have a gross edge with t > 3.7; {n_net} are net "
             f"positive at realistic costs in BOTH halves.")
    L.append("")
    L.append("What this test cannot see: the edge of high-frequency firms comes from microseconds, co-location, "
             "order-flow payments and exchange rebates — infrastructure, not data a retail trader can buy.")
    return "\n".join(L)
