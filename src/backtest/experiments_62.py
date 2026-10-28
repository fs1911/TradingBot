"""
Experiment #62 — machine learning on company data: does a model find more than our
simple rules (buybacks, quality)?

Data: the #49/#50 SEC universe (US firms, assets ≥ $1bn, 10-K filed by end of June),
Yahoo prices. One row per firm and formation year (end of June), 9 features, all
point-in-time and ranked to [0, 1] within each year (Gu, Kelly & Xiu 2020 practice):
  gross profitability, ROE, low accruals, low leverage, size (log assets),
  net share issuance (buybacks), 12-1 month momentum, last-month return, 12-month volatility.
Target: the stock's return over the next 12 months, ranked within the year.

Models, strictly walk-forward (trained only on years whose 12-month outcome was already
known at the formation date, expanding window, ≥ 5 training years):
  H1 buybacks alone (#50)             H2 quality score alone (#49)
  H3 'human rule': mean rank of buybacks, quality and momentum (pre-specified, no fitting)
  M1 ridge regression on the 9 ranked features
  M2 gradient-boosted trees (150 trees, depth 3, learning rate 0.05, subsample 0.7),
     implemented in numpy (no ML packages on the server)
  P  placebo: M2 trained on shuffled targets (must be ≈ 0)
Per model: average rank information coefficient (Spearman correlation prediction vs
outcome, per year) with t across years; top-quintile minus universe (equal-weight,
monthly) p.a. and t. Survivorship: only currently listed tickers have Yahoo prices.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

FEATURES = ["gross_profitability", "roe", "low_accruals", "low_leverage", "size", "buyback",
            "mom12_1", "rev1", "vol12"]


# ── panel ────────────────────────────────────────────────────────────────────

def build_panel(comp_by_year: dict, buyback_by_year: dict, px: pd.DataFrame, rets: pd.DataFrame,
                min_price: float = 5.0) -> pd.DataFrame:
    """comp_by_year: {fy: DataFrame ticker → components (#49)}; buyback_by_year: {fy: Series
    ticker → −net issuance}; px/rets monthly (Period index). Formation end of June fy+1."""
    rows = []
    for y, comp in sorted(comp_by_year.items()):
        form = pd.Period(f"{y + 1}-06", "M")
        if form not in px.index or form - 12 not in px.index:
            continue
        p0 = px.loc[form]
        tick = [t for t in comp.index if t in px.columns and np.isfinite(p0.get(t, np.nan)) and p0[t] >= min_price]
        if len(tick) < 50:
            continue
        c = comp.loc[tick]
        mom = px.loc[form - 1, tick] / px.loc[form - 12, tick] - 1
        rev = rets.loc[form, tick] if form in rets.index else pd.Series(np.nan, index=tick)
        hist = rets.loc[(rets.index > form - 12) & (rets.index <= form), tick]
        vol = hist.std()
        fwd_m = [m for m in pd.period_range(form + 1, form + 12, freq="M") if m in rets.index]
        fwd = (1 + rets.loc[fwd_m, tick].fillna(0)).prod() - 1 if len(fwd_m) == 12 else pd.Series(np.nan, index=tick)
        bb = buyback_by_year.get(y, pd.Series(dtype=float)).reindex(tick)
        df = pd.DataFrame({"year": y, "ticker": tick,
                           "gross_profitability": c["gross_profitability"].to_numpy(), "roe": c["roe"].to_numpy(),
                           "low_accruals": c["low_accruals"].to_numpy(), "low_leverage": c["low_leverage"].to_numpy(),
                           "size": np.log(c["assets"].to_numpy()), "buyback": bb.to_numpy(),
                           "mom12_1": mom.to_numpy(), "rev1": rev.to_numpy(), "vol12": vol.to_numpy(),
                           "fwd": fwd.to_numpy()})
        rows.append(df)
    if not rows:
        return pd.DataFrame()
    p = pd.concat(rows, ignore_index=True)
    for f in FEATURES + ["fwd"]:
        p[f + "_r"] = p.groupby("year")[f].rank(pct=True)
    for f in FEATURES:
        p[f + "_r"] = p[f + "_r"].fillna(0.5)            # missing → neutral
    return p


# ── models ───────────────────────────────────────────────────────────────────

def ridge_fit(X: np.ndarray, y: np.ndarray, lam: float = 1.0):
    Xc = np.column_stack([np.ones(len(X)), X])
    I = np.eye(Xc.shape[1]); I[0, 0] = 0
    return np.linalg.solve(Xc.T @ Xc + lam * I, Xc.T @ y)


def ridge_predict(w, X):
    return w[0] + X @ w[1:]


class _Tree:
    """Regression tree on [0,1] features, histogram splits: features are pre-binned into
    `bins` integer bins; each node scans all bin edges at once via bincount/cumsum."""

    def __init__(self, depth=3, min_leaf=50, bins=16):
        self.depth, self.min_leaf, self.bins = depth, min_leaf, bins

    def fit(self, B, g):
        """B: integer-binned features (n × p, values 0..bins-1); g: residuals."""
        self.nodes = []                       # (feature, bin_threshold, left, right) or (None, value)
        self._grow(B, g, np.arange(len(g)), 0)
        return self

    def _grow(self, B, g, idx, d):
        node_id = len(self.nodes)
        self.nodes.append(None)
        gi = g[idx]
        if d == self.depth or len(idx) < 2 * self.min_leaf:
            self.nodes[node_id] = (None, float(gi.mean()))
            return node_id
        n, tot = len(idx), gi.sum()
        best = None
        for j in range(B.shape[1]):
            bj = B[idx, j]
            cnt = np.cumsum(np.bincount(bj, minlength=self.bins))[:-1]
            sm = np.cumsum(np.bincount(bj, weights=gi, minlength=self.bins))[:-1]
            ok = (cnt >= self.min_leaf) & (n - cnt >= self.min_leaf)
            if not ok.any():
                continue
            gain = np.where(ok, sm ** 2 / np.maximum(cnt, 1) + (tot - sm) ** 2 / np.maximum(n - cnt, 1), -np.inf)
            k = int(np.argmax(gain))
            if best is None or gain[k] > best[0]:
                best = (gain[k], j, k)
        if best is None:
            self.nodes[node_id] = (None, float(gi.mean()))
            return node_id
        _, j, k = best
        m = B[idx, j] <= k
        left = self._grow(B, g, idx[m], d + 1)
        right = self._grow(B, g, idx[~m], d + 1)
        self.nodes[node_id] = (j, k, left, right)
        return node_id

    def predict(self, B):
        out = np.empty(len(B))
        stack = [(0, np.arange(len(B)))]
        while stack:
            nid, idx = stack.pop()
            node = self.nodes[nid]
            if node[0] is None:
                out[idx] = node[1]
                continue
            j, k, l, r = node
            m = B[idx, j] <= k
            stack.append((l, idx[m]))
            stack.append((r, idx[~m]))
        return out


def _bin(X, bins=16):
    return np.clip((np.asarray(X) * bins).astype(int), 0, bins - 1)


def gbm_fit(X, y, n_trees=150, lr=0.05, depth=3, subsample=0.7, seed=62):
    rng = np.random.default_rng(seed)
    B = _bin(X)
    base = float(y.mean())
    pred = np.full(len(y), base)
    trees = []
    for _ in range(n_trees):
        idx = np.flatnonzero(rng.random(len(y)) < subsample)
        t = _Tree(depth=depth).fit(B[idx], (y - pred)[idx])
        pred += lr * t.predict(B)
        trees.append(t)
    return base, lr, trees


def gbm_predict(model, X):
    base, lr, trees = model
    B = _bin(X)
    return base + lr * sum(t.predict(B) for t in trees)


# ── evaluation ───────────────────────────────────────────────────────────────

def walk_forward(panel: pd.DataFrame, min_train_years: int = 5, seed: int = 62) -> dict:
    """{model: DataFrame[year, ticker, score]} — predictions only for out-of-sample years."""
    Xcols = [f + "_r" for f in FEATURES]
    years = sorted(panel["year"].unique())
    out = {k: [] for k in ("H1 buybacks", "H2 quality", "H3 human rule", "M1 ridge", "M2 boosted trees",
                           "P placebo (shuffled)")}
    rng = np.random.default_rng(seed)
    for y in years:
        train = panel[(panel["year"] <= y - 1) & panel["fwd_r"].notna()]   # outcome known by June y+1
        if train["year"].nunique() < min_train_years:
            continue
        test = panel[panel["year"] == y]
        Xt, X = train[Xcols].to_numpy(), test[Xcols].to_numpy()
        yt = train["fwd_r"].to_numpy() - 0.5
        qual = test[["gross_profitability_r", "roe_r", "low_accruals_r", "low_leverage_r"]].mean(axis=1)
        scores = {
            "H1 buybacks": test["buyback_r"].to_numpy(),
            "H2 quality": qual.to_numpy(),
            "H3 human rule": ((test["buyback_r"] + qual + test["mom12_1_r"]) / 3).to_numpy(),
            "M1 ridge": ridge_predict(ridge_fit(Xt, yt), X),
            "M2 boosted trees": gbm_predict(gbm_fit(Xt, yt), X),
            "P placebo (shuffled)": gbm_predict(gbm_fit(Xt, rng.permutation(yt), n_trees=60), X),
        }
        for k, sc in scores.items():
            out[k].append(pd.DataFrame({"year": y, "ticker": test["ticker"].to_numpy(), "score": sc}))
    return {k: pd.concat(v, ignore_index=True) for k, v in out.items() if v}


def rank_ic(pred: pd.DataFrame, panel: pd.DataFrame) -> pd.Series:
    m = pred.merge(panel[["year", "ticker", "fwd"]], on=["year", "ticker"]).dropna()
    return m.groupby("year").apply(lambda g: g["score"].rank().corr(g["fwd"].rank()) if len(g) > 20 else np.nan).dropna()


def run_experiment62_report(panel: pd.DataFrame, px: pd.DataFrame, rets: pd.DataFrame, n_trials: int = 300) -> str:
    from datetime import datetime, timezone
    from .experiments_49 import form_portfolios, mstat
    L = [f"# Experiment #62 — machine learning on company data ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if panel is None or panel.empty:
        return "\n".join(L + ["No panel."])
    L.append(f"Panel: {len(panel):,} firm-years, {panel['year'].min()}–{panel['year'].max()} (formation June of the "
             f"following year), {panel.groupby('year').size().median():.0f} firms per year. Features ranked per year; "
             f"walk-forward, expanding window ≥ 5 years. Bonferroni α/{n_trials} → |t| ≳ 3.7.")
    L.append("")
    preds = walk_forward(panel)
    L.append("| model | test years | rank IC (mean) | IC t | years IC > 0 | top quintile − universe p.a. | t | years top beats universe |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|")
    for k, pr in preds.items():
        ic = rank_ic(pr, panel)
        sc = {int(y): g.set_index("ticker")["score"] for y, g in pr.groupby("year")}
        port = form_portfolios(sc, px, rets)
        if port.empty or ic.empty:
            L.append(f"| {k} | — | — | — | — | — | — | — |")
            continue
        ex = port["Q5"] - port["universe"]
        st = mstat(ex)
        yr = ex.groupby(ex.index.year).sum()
        ict = ic.mean() / ic.std() * math.sqrt(len(ic)) if ic.std() > 0 else float("nan")
        L.append(f"| {k} | {len(ic)} | {ic.mean():+.3f} | {ict:+.2f} | {int((ic > 0).sum())}/{len(ic)} | "
                 f"{100*st['ann']:+.1f} % | {st['t']:+.2f} | {int((yr > 0).sum())}/{len(yr)} |")
    L.append("")
    if "M2 boosted trees" in preds and "H3 human rule" in preds:
        a = rank_ic(preds["M2 boosted trees"], panel)
        b = rank_ic(preds["H3 human rule"], panel)
        d = (a - b).dropna()
        if len(d) > 2 and d.std() > 0:
            L.append(f"Boosted trees − human rule, rank IC difference: {d.mean():+.3f} (t {d.mean()/d.std()*math.sqrt(len(d)):+.2f}, "
                     f"{int((d > 0).sum())}/{len(d)} years better).")
    L.append("")
    L.append("Rank IC = correlation between a model's ranking and the realised 12-month return ranking (0 = no "
             "information; +0.05 is already considered useful in practice). The placebo shows what fitting noise "
             "looks like out-of-sample.")
    return "\n".join(L)
