"""
Experiment #15 — a genuinely new CATEGORY: machine-learning / feature-based
prediction, instead of fixed rules. A logistic-regression classifier is trained
by walk-forward (only past data) to predict the next day's direction from a set of
features (lagged returns, RSI, volatility, distances from moving averages). It
trades long/flat on the model's signal and is judged by the full rigor battery.

ML on public price features is the most overfitting-prone approach in quant, so
the walk-forward is strict: the model is retrained on an expanding past window and
only ever predicts the unseen next block; features are standardized with training-
window statistics only. Pure numpy (no scikit-learn).
"""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd
from loguru import logger

from .rigor import full_rigor


def _norm(s: pd.Series) -> pd.Series:
    s = s.sort_index(); s.index = s.index.normalize(); return s


def _rsi(closes: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(closes), 50.0)
    if len(closes) < period + 1:
        return out
    d = np.diff(closes)
    g = np.where(d > 0, d, 0.0); l = np.where(d < 0, -d, 0.0)
    ag = g[:period].mean(); al = l[:period].mean()
    out[period] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(period + 1, len(closes)):
        ag = (ag * (period - 1) + g[i - 1]) / period
        al = (al * (period - 1) + l[i - 1]) / period
        out[i] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


FEATURES = ["r1", "r2", "r3", "r5", "r10", "rsi2", "rsi14", "d_sma20", "d_sma50", "vol10", "vol20"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    c = _norm(df["close"])
    r = c.pct_change()
    out = pd.DataFrame(index=c.index)
    out["r1"] = r
    out["r2"] = c.pct_change(2)
    out["r3"] = c.pct_change(3)
    out["r5"] = c.pct_change(5)
    out["r10"] = c.pct_change(10)
    arr = c.to_numpy()
    out["rsi2"] = (_rsi(arr, 2) - 50) / 50
    out["rsi14"] = (_rsi(arr, 14) - 50) / 50
    out["d_sma20"] = c / c.rolling(20).mean() - 1
    out["d_sma50"] = c / c.rolling(50).mean() - 1
    out["vol10"] = r.rolling(10).std()
    out["vol20"] = r.rolling(20).std()
    out["fwd"] = r.shift(-1)                       # next-day return (target basis)
    return out


def _fit_logreg(X, y, lr=0.3, epochs=400, l2=1e-3):
    n, k = X.shape
    w = np.zeros(k)
    for _ in range(epochs):
        z = X @ w
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        grad = X.T @ (p - y) / n + l2 * w
        w -= lr * grad
    return w


def ml_returns(df: pd.DataFrame, retrain: int = 63, train_min: int = 400,
               threshold: float = 0.5, commission_pct: float = 0.05,
               slippage_pct: float = 0.03):
    """Walk-forward logistic regression; long when P(up)>threshold, else flat.
    Returns (daily net returns, mean feature weights across retrains)."""
    feat = build_features(df).dropna()
    if len(feat) < train_min + retrain + 20:
        return pd.Series(dtype=float), {}
    X_all = feat[FEATURES].to_numpy()
    fwd = feat["fwd"].to_numpy()
    y_all = (fwd > 0).astype(float)
    idx = feat.index
    n = len(feat)

    pos = np.zeros(n)
    weight_snapshots = []
    t = train_min
    while t < n:
        tr = slice(0, t)
        mu = X_all[tr].mean(axis=0)
        sd = X_all[tr].std(axis=0) + 1e-9
        Xtr = (X_all[tr] - mu) / sd
        w = _fit_logreg(np.column_stack([np.ones(t), Xtr]), y_all[tr])
        weight_snapshots.append(w[1:])
        end = min(t + retrain, n)
        Xte = (X_all[t:end] - mu) / sd
        p = 1.0 / (1.0 + np.exp(-np.clip(np.column_stack([np.ones(end - t), Xte]) @ w, -30, 30)))
        pos[t:end] = (p > threshold).astype(float)
        t = end

    pos_s = pd.Series(pos, index=idx)          # pos[t] applies to fwd[t] = return t->t+1
    cost = (commission_pct + slippage_pct) / 100
    turn = pos_s.diff().abs().fillna(pos_s.abs())
    ret = (pos_s * pd.Series(fwd, index=idx) - turn * cost).rename("ret")
    mean_w = dict(zip(FEATURES, np.mean(weight_snapshots, axis=0))) if weight_snapshots else {}
    return ret.dropna(), mean_w


def run_experiment15_report(
    get_ohlcv: Callable[[str, str, int], pd.DataFrame],
    symbols: list[str],
    n_trials: int = 35,
    limit: int = 2500,
) -> str:
    from datetime import datetime, timezone

    lines = [f"# Experiment #15 — machine learning (walk-forward logistic regression) "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    lines.append(f"A logistic-regression classifier trained walk-forward on past data only, "
                 f"predicting next-day direction from {len(FEATURES)} features, trading long/flat. "
                 f"Judged by the full rigor battery (multiple-testing haircut α/{n_trials}).")
    lines.append("")
    lines.append("| Symbol | OOS ret% | Sharpe | t-stat | p-value | sig(haircut) | Walk-fwd | regimes+ | Verdict |")
    lines.append("|---|--:|--:|--:|--:|:--:|:--:|:--:|---|")

    survivors = 0
    weight_acc: dict[str, list] = {f: [] for f in FEATURES}
    for sym in symbols:
        df = get_ohlcv(sym, "1Day", limit)
        if df is None or len(df) < 700:
            lines.append(f"| {sym} | insufficient data |||||||")
            continue
        ret, weights = ml_returns(df)
        if ret.empty:
            lines.append(f"| {sym} | insufficient data |||||||")
            continue
        res = full_rigor(f"ML {sym}", ret, n_trials)
        if res["verdict"].startswith("✅"):
            survivors += 1
        lines.append(f"| {sym} | {res['oos_ret']:+.0f} | {res['sharpe']} | {res['t_stat']} | "
                     f"{res['p_value']} | {'yes' if res['sig_after_haircut'] else 'no'} | "
                     f"{res['wf_pct']}% | {res['regime_positive']} | {res['verdict']} |")
        for f, wv in weights.items():
            weight_acc[f].append(wv)

    lines.append("")
    # which features the model leaned on (research output)
    avg_w = {f: float(np.mean(v)) for f, v in weight_acc.items() if v}
    if avg_w:
        ranked = sorted(avg_w.items(), key=lambda kv: -abs(kv[1]))
        lines.append("**Average feature weights (what the model used):** "
                     + ", ".join(f"{f} {w:+.2f}" for f, w in ranked))
        lines.append("")
    lines.append(f"**Summary:** {survivors}/{len(symbols)} symbols survive the full battery. "
                 + ("A trained model found a robust signal — investigate." if survivors else
                    "None — the learned models do not generalise out-of-sample (as expected for "
                    "price-only ML)."))
    return "\n".join(lines)
