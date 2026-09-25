"""
Experiment #42 — classic chart-technical rules (Fibonacci & co.) under a placebo test.

Retail and newsletter trading leans on Fibonacci retracements, support/resistance,
breakouts, RSI, MACD, Bollinger bands and moving-average crosses. The project so far
tested RSI(2), SMA filters and mean reversion on a few indices; the rest was never
tested cleanly. Here every rule is written as an OBJECTIVE, lookahead-free long/flat
rule (signal at close t, position from t+1) and applied to ~40 markets across asset
classes (indices back to 1927, single stocks, commodity futures, FX, bonds, crypto).

The key test is a PLACEBO: the rule's own position series is circularly shifted
against the market's returns (shift ≥ 1 year). That keeps exposure, number of trades
and holding lengths identical but destroys any timing. Timing edge = real
Σ pos·(r − cash) minus the placebo average. Pooled p-value = share of pooled placebo
draws (independent random shift per market) ≥ real, Bonferroni over the rules.

Also reported: trade win rates (what promoters quote), net Sharpe vs buy & hold after
5 bps per switch, per-asset-class edge, and the edge before 1992 (Brock, Lakonishok &
LeBaron's publication), 1992–2007 and 2008+.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .experiments_33 import cash_daily_returns
from .experiments_38 import _naive

MIN_SHIFT = 252
ERAS = (("≤1991", None, "1991-12-31"), ("1992–2007", "1992-01-01", "2007-12-31"),
        ("2008+", "2008-01-01", None))


# ── indicators ──────────────────────────────────────────────────────────────

def rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _run_state(entry: np.ndarray, exit_: np.ndarray) -> np.ndarray:
    """Generic long/flat state machine from boolean entry/exit arrays."""
    pos = np.zeros(len(entry))
    inpos = False
    for t in range(len(entry)):
        if inpos and exit_[t]:
            inpos = False
        elif not inpos and entry[t]:
            inpos = True
        pos[t] = 1.0 if inpos else 0.0
    return pos


# ── rules: each returns a 0/1 position decided at close t (apply from t+1) ──

def rule_fib(c: pd.Series, n: int = 120, level: float = 0.618, stop: float = 0.786,
             max_hold: int = 60, min_range: float = 0.05) -> pd.Series:
    """Buy the Fibonacci retracement of the latest up-swing.
    Swing high H = highest close of the last n days (not today); swing low L = lowest
    close of the n days before H. Enter when price has pulled back to H − level·(H−L)
    but not below the stop H − stop·(H−L). Exit at H (target), at the stop, or after
    max_hold days."""
    x = c.to_numpy(float)
    N = len(x)
    pos = np.zeros(N)
    inpos, eH, eStop, held = False, 0.0, 0.0, 0
    for t in range(2 * n, N):
        if inpos:
            held += 1
            if x[t] >= eH or x[t] <= eStop or held >= max_hold:
                inpos = False
            else:
                pos[t] = 1.0
                continue
        w = x[t - n + 1: t + 1]
        h = t - n + 1 + int(np.argmax(w))
        if h == t:
            continue
        H = x[h]
        L = float(np.min(x[h - n: h]))
        if L <= 0 or (H - L) / L < min_range:
            continue
        rng = H - L
        if H - stop * rng < x[t] <= H - level * rng:
            inpos, eH, eStop, held = True, H, H - stop * rng, 0
            pos[t] = 1.0
    return pd.Series(pos, index=c.index)


def rule_support(c: pd.Series, n: int = 60, band: float = 0.02, stop: float = 0.03,
                 max_hold: int = 40) -> pd.Series:
    """Buy at support: close within `band` above the prior n-day low. Exit at the
    prior n-day high (resistance), a close `stop` below support, or after max_hold."""
    x = c.to_numpy(float)
    lo = c.shift(1).rolling(n).min().to_numpy()
    hi = c.shift(1).rolling(n).max().to_numpy()
    pos = np.zeros(len(x))
    inpos, tgt, stp, held = False, 0.0, 0.0, 0
    for t in range(n + 1, len(x)):
        if inpos:
            held += 1
            if x[t] >= tgt or x[t] <= stp or held >= max_hold:
                inpos = False
            else:
                pos[t] = 1.0
                continue
        if np.isfinite(lo[t]) and lo[t] <= x[t] <= lo[t] * (1 + band) and hi[t] > lo[t] * (1 + 2 * band):
            inpos, tgt, stp, held = True, hi[t], lo[t] * (1 - stop), 0
            pos[t] = 1.0
    return pd.Series(pos, index=c.index)


def rule_breakout(c: pd.Series, n: int = 20, m: int = 10) -> pd.Series:
    """Donchian / resistance breakout: enter on a close above the prior n-day high,
    exit on a close below the prior m-day low (Turtle style)."""
    hi = c.shift(1).rolling(n).max()
    lo = c.shift(1).rolling(m).min()
    return pd.Series(_run_state((c > hi).to_numpy(), (c < lo).to_numpy()), index=c.index)


def rule_rsi(c: pd.Series, n: int = 14, lo: float = 30, out: float = 50) -> pd.Series:
    r = rsi(c, n)
    return pd.Series(_run_state((r < lo).to_numpy(), (r > out).to_numpy()), index=c.index)


def rule_macd(c: pd.Series, f: int = 12, s: int = 26, g: int = 9) -> pd.Series:
    m = c.ewm(span=f, adjust=False).mean() - c.ewm(span=s, adjust=False).mean()
    sig = m.ewm(span=g, adjust=False).mean()
    p = (m > sig).astype(float)
    p.iloc[: s + g] = 0.0
    return p


def rule_bollinger(c: pd.Series, n: int = 20, k: float = 2.0) -> pd.Series:
    mid = c.rolling(n).mean()
    sd = c.rolling(n).std()
    return pd.Series(_run_state((c < mid - k * sd).to_numpy(), (c > mid).to_numpy()), index=c.index)


def rule_cross(c: pd.Series, f: int = 50, s: int = 200) -> pd.Series:
    p = (c.rolling(f).mean() > c.rolling(s).mean()).astype(float)
    p.iloc[:s] = 0.0
    return p


RULES = {
    "Fibonacci 38.2% (120d swing)": lambda c: rule_fib(c, 120, 0.382, 0.786),
    "Fibonacci 50% (120d swing)": lambda c: rule_fib(c, 120, 0.5, 0.786),
    "Fibonacci 61.8% (120d swing)": lambda c: rule_fib(c, 120, 0.618, 0.786),
    "Fibonacci 61.8% (60d swing)": lambda c: rule_fib(c, 60, 0.618, 0.786),
    "Support bounce (60d low)": lambda c: rule_support(c, 60),
    "Support bounce (250d low)": lambda c: rule_support(c, 250),
    "Breakout 20/10 (Donchian)": lambda c: rule_breakout(c, 20, 10),
    "Breakout 55/20 (Turtle)": lambda c: rule_breakout(c, 55, 20),
    "Breakout 52-week high": lambda c: rule_breakout(c, 250, 50),
    "RSI(14) <30 → >50": lambda c: rule_rsi(c, 14, 30, 50),
    "MACD 12/26/9 cross": lambda c: rule_macd(c),
    "Bollinger 20/2 lower band → mid": lambda c: rule_bollinger(c),
    "Golden cross 50/200": lambda c: rule_cross(c, 50, 200),
}


# ── evaluation ─────────────────────────────────────────────────────────────

def shift_distribution(pos: np.ndarray, x: np.ndarray, min_shift: int = MIN_SHIFT) -> tuple:
    """Real Σ pos[t]·x[t] and the placebo values Σ pos[t−k]·x[t] for all circular
    shifts min_shift ≤ k ≤ n − min_shift (via FFT). Both annualised per day."""
    n = len(x)
    cc = np.real(np.fft.ifft(np.fft.fft(x) * np.conj(np.fft.fft(pos))))
    real = float(np.dot(pos, x))
    ks = np.arange(min_shift, n - min_shift + 1)
    return real * 252 / n, cc[ks] * 252 / n


def trades(pos: np.ndarray, c: np.ndarray) -> list:
    """Round-trip returns: entry at close of the first in-position day's signal,
    exit at the close of the signal day that ends the position."""
    out = []
    entry = None
    for t in range(1, len(pos)):
        if pos[t] == 1 and pos[t - 1] == 0:
            entry = c[t]
        elif pos[t] == 0 and pos[t - 1] == 1 and entry is not None:
            out.append(c[t] / entry - 1)
            entry = None
    return out


def evaluate_market(close: pd.Series, cash: pd.Series, rule, cost_bps: float = 5.0) -> dict | None:
    c = _naive(close)
    if len(c) < 3 * MIN_SHIFT + 300:
        return None
    r = c.pct_change().fillna(0.0)
    cs = cash.reindex(c.index).fillna(0.0) if cash is not None else pd.Series(0.0, index=c.index)
    sig = rule(c).reindex(c.index).fillna(0.0)
    p = sig.shift(1).fillna(0.0)
    x = (r - cs).to_numpy()
    real, plc = shift_distribution(p.to_numpy(), x)
    turns = p.diff().abs().fillna(0.0)
    strat = p * r + (1 - p) * cs - turns * cost_bps / 1e4
    sx = strat - cs
    bx = r - cs
    sh = lambda z: float(z.mean() / z.std() * math.sqrt(252)) if z.std() > 0 else 0.0
    tr = trades(sig.to_numpy(), c.to_numpy())
    eras = {}
    for lbl, a, b in ERAS:
        pp, xx = p.loc[a:b], (r - cs).loc[a:b]
        if len(xx) > 750 and pp.sum() > 20:
            eras[lbl] = (float((pp * xx).sum()), float(pp.sum()), float(xx.mean()), len(xx))
    return {"real": real, "placebo": plc, "exposure": float(p.mean()),
            "trades_py": float(turns.sum() / 2 / (len(c) / 252)),
            "win": float(np.mean([t > 0 for t in tr])) if tr else float("nan"),
            "avg_trade": float(np.mean(tr)) if tr else float("nan"), "n_trades": len(tr),
            "sh_strat": sh(sx), "sh_bh": sh(bx), "eras": eras,
            "beat95": real > float(np.percentile(plc, 95)), "start": c.index[0]}


def pooled_p(results: list, n_draw: int = 5000, seed: int = 42) -> tuple:
    """Average over markets of real edge vs the same average under independent random
    shifts. Returns (edge = real − placebo mean, p)."""
    if not results:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    real = np.mean([m["real"] for m in results])
    base = np.mean([m["placebo"].mean() for m in results])
    draws = np.zeros(n_draw)
    for m in results:
        draws += m["placebo"][rng.integers(0, len(m["placebo"]), n_draw)]
    draws /= len(results)
    return float(real - base), float((draws >= real).mean())


def era_edge(results: list, lbl: str) -> float:
    """Timing edge in an era: Σ pos·x − exposure·mean(x), annualised, averaged."""
    vals = []
    for m in results:
        e = m["eras"].get(lbl)
        if e:
            s, days_in, mu, n = e
            vals.append((s - days_in * mu) * 252 / n)
    return float(np.mean(vals)) if len(vals) >= 3 else float("nan")


def run_experiment42_report(markets: dict, irx: pd.Series, rules: dict | None = None,
                            prior_trials: int = 165) -> str:
    """markets: {name: (asset_class, close Series)}."""
    from datetime import datetime, timezone
    rules = rules or RULES
    n_rules = len(rules)
    crit = 0.05 / n_rules
    L = [f"# Experiment #42 — chart-technical rules under a placebo test "
         f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    idx = pd.DatetimeIndex([])
    for _, (_, s) in markets.items():
        if s is not None and len(s):
            idx = idx.union(_naive(s).index)
    cash = cash_daily_returns(_naive(irx) if irx is not None and len(irx) else pd.Series(dtype=float), idx)
    usable = {k: v for k, v in markets.items() if v[1] is not None and len(v[1]) >= 3 * MIN_SHIFT + 300}
    L.append(f"Markets usable: {len(usable)}/{len(markets)}. Cash = ^IRX "
             f"{'ok' if irx is not None and len(irx) > 1000 else 'MISSING → 0%'}. "
             f"Rules: {n_rules}; Bonferroni α/{n_rules} = {crit:.4f} on the pooled placebo p "
             f"(project total trials now ≈{prior_trials + n_rules}).")
    classes = sorted({v[0] for v in usable.values()})
    L.append("Markets: " + "; ".join(f"{cl}: " + ", ".join(k for k, v in usable.items() if v[0] == cl)
                                     for cl in classes))
    L.append("")
    L.append("Timing edge = real Σ pos·(r − cash) minus the average over circular shifts of the SAME "
             "position series (same exposure, trades, holding times; timing destroyed). "
             "Units: % per year of excess return, averaged over markets.")
    L.append("")
    L.append("| Rule | exposure | trades/yr | win rate | avg trade | timing edge | placebo p | sig | "
             "markets > own 95% | Sharpe net vs B&H (median Δ) | markets net Sharpe > B&H |")
    L.append("|---|--:|--:|--:|--:|--:|--:|:--:|--:|--:|--:|")
    by_rule = {}
    n_sig = 0
    for name, fn in rules.items():
        res = []
        per_class = {}
        for mk, (cl, s) in usable.items():
            m = evaluate_market(s, cash, fn)
            if m is None:
                continue
            m["class"] = cl
            res.append(m)
        by_rule[name] = res
        if not res:
            L.append(f"| {name} | — | | | | | | | | | |")
            continue
        edge, p = pooled_p(res)
        sig = p < crit and edge > 0
        n_sig += int(sig)
        wins = [m["win"] for m in res if np.isfinite(m["win"])]
        avgt = [m["avg_trade"] for m in res if np.isfinite(m["avg_trade"])]
        dsh = [m["sh_strat"] - m["sh_bh"] for m in res]
        L.append(f"| {name} | {100*np.mean([m['exposure'] for m in res]):.0f}% | "
                 f"{np.mean([m['trades_py'] for m in res]):.1f} | "
                 f"{100*np.mean(wins):.0f}% | {100*np.mean(avgt):+.2f}% | {100*edge:+.2f}% | {p:.3f} | "
                 f"{'✅' if sig else '❌'} | {sum(m['beat95'] for m in res)}/{len(res)} | "
                 f"{np.median(dsh):+.2f} | {sum(d > 0 for d in dsh)}/{len(res)} |")
    L.append("")
    L.append(f"By chance about 5% of markets beat their own 95th placebo percentile "
             f"(≈{0.05*len(usable):.1f} of {len(usable)}).")
    L.append("")

    L.append("### Timing edge by asset class (% p.a.; * = class-pooled placebo p < 0.05, "
             "** = < α/rules)")
    L.append("| Rule | " + " | ".join(classes) + " |")
    L.append("|---|" + "--:|" * len(classes))
    for name, res in by_rule.items():
        cells = []
        for cl in classes:
            sub = [m for m in res if m["class"] == cl]
            if len(sub) < 2:
                cells.append("—")
                continue
            e, pc = pooled_p(sub, 3000)
            star = "**" if pc < crit and e > 0 else ("*" if pc < 0.05 and e > 0 else "")
            cells.append(f"{100*e:+.2f}{star}")
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    L.append("")

    L.append("### Timing edge by era (% p.a.; Brock/Lakonishok/LeBaron published 1992)")
    L.append("| Rule | " + " | ".join(e[0] for e in ERAS) + " |")
    L.append("|---|" + "--:|" * len(ERAS))
    for name, res in by_rule.items():
        vals = [era_edge(res, e[0]) for e in ERAS]
        L.append(f"| {name} | " + " | ".join("—" if not np.isfinite(v) else f"{100*v:+.2f}" for v in vals) + " |")
    L.append("")
    L.append(f"**Summary:** {n_sig}/{n_rules} rules show a timing edge beyond the placebo after the "
             f"Bonferroni haircut. A high win rate alone says nothing: the placebo has the same "
             f"exposure and trade structure. Survivorship: single stocks are today's large caps.")
    return "\n".join(L)
