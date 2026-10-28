"""
Experiment #65 — does the app's buy check (🟢 / 🟡 / 🔴) separate good from bad purchases?

Rules exactly as in the "Mein Depot" prompt, as far as they can be tested historically:
  🔴 if  dilution (shares ≥ +5 % in 12 months, latest 10-K/10-Q already FILED)  OR  market
        light red (index trend score ≤ 1 AND macro stress, #46/#47)
  🟡 if  market light yellow (trend ≤ 1, no stress)  OR  no share data
  🟢 otherwise (bonus flag: buyback ≤ −2 %)
(The concentration and ETF-fee rules depend on the user's own depot and are not testable.)

Every month 2010 → mid-2025, every US stock of the #50 universe (assets ≥ $1bn, price ≥ $5)
gets a colour with information available at that month-end. Outcome: the next 12 months.
  - relative: 12-month return minus the equal-weight universe of the same month
    (stock selection — dilution rule)
  - absolute: 12-month return and the share of 'disasters' (≤ −40 %)
    (market timing — market-light rule)
Overlapping monthly cohorts → t-statistics only on non-overlapping June cohorts.
Pure, injected for CI.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


def latest_change(concept: tuple, month: pd.Period, max_age_days: int = 380) -> float:
    """Share change from the newest 10-K or 10-Q FILED by the end of `month` (ln → pct)."""
    annual, quarterly = concept
    end = month.to_timestamp(how="end")
    best = None
    for fy, (ni, filed, _) in annual.items():
        if filed is not None and filed <= end and (end - filed).days <= max_age_days:
            if best is None or filed > best[0]:
                best = (filed, ni)
    for _, ni, filed, _ in quarterly:
        if filed is not None and filed <= end and (end - filed).days <= max_age_days:
            if best is None or filed > best[0]:
                best = (filed, ni)
    if best is None or not np.isfinite(best[1]) or abs(best[1]) > 1.5:
        return float("nan")
    return float(math.exp(best[1]) - 1)


def market_light(score: pd.Series, stress: pd.Series) -> pd.Series:
    """'green' if trend ≥ 2, 'yellow' if ≤ 1 without stress, 'red' if ≤ 1 with stress."""
    st = stress.reindex(score.index).fillna(True).astype(bool)   # unknown counts as stress (as in the app)
    return pd.Series(np.where(score >= 2, "green", np.where(st, "red", "yellow")), index=score.index)


def colour(change: float, light: str) -> str:
    if (np.isfinite(change) and change >= 0.05) or light == "red":
        return "red"
    if light == "yellow" or not np.isfinite(change):
        return "yellow"
    return "green"


def build_cohorts(concepts: dict, tmap: dict, px: pd.DataFrame, light: pd.Series,
                  months: pd.PeriodIndex, min_price: float = 5.0) -> pd.DataFrame:
    rows = []
    tick_of = {cik: tmap.get(int(cik)) for cik in concepts}
    for m in months:
        if m not in px.index or m + 12 not in px.index or m not in light.index:
            continue
        p0, p1 = px.loc[m], px.loc[m + 12]
        lt = light[m]
        for cik, con in concepts.items():
            t = tick_of[cik]
            if not t or t not in px.columns or not np.isfinite(p0.get(t, np.nan)) or p0[t] < min_price:
                continue
            if not np.isfinite(p1.get(t, np.nan)):
                continue
            ch = latest_change(con, m)
            rows.append((m, t, ch, lt, colour(ch, lt), p1[t] / p0[t] - 1))
    d = pd.DataFrame(rows, columns=["month", "ticker", "change", "light", "colour", "fwd"])
    if len(d):
        d["excess"] = d["fwd"] - d.groupby("month")["fwd"].transform("mean")
        d["buyback"] = d["change"] <= -0.02
    return d


def summarise(d: pd.DataFrame, by: str, value: str) -> pd.DataFrame:
    """Mean per group: over all monthly cohorts (descriptive) and June cohorts (t-stat)."""
    cm = d.groupby(["month", by])[value].mean().unstack()
    june = cm[[p.month == 6 for p in cm.index]]
    out = {}
    for g in cm.columns:
        x, j = cm[g].dropna(), june[g].dropna()
        t = j.mean() / j.std() * math.sqrt(len(j)) if len(j) > 2 and j.std() > 0 else float("nan")
        out[g] = {"mean_all": x.mean(), "n_months": len(x), "mean_june": j.mean(), "t_june": t, "n_june": len(j),
                  "disaster": float((d.loc[d[by] == g, "fwd"] <= -0.4).mean()),
                  "n_obs": int((d[by] == g).sum())}
    return pd.DataFrame(out).T


def run_experiment65_report(d: pd.DataFrame, light: pd.Series) -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #65 — does the buy check 🟢/🟡/🔴 work? ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    if d is None or d.empty:
        return "\n".join(L + ["No cohorts."])
    L.append(f"{len(d):,} stock-months, {d['month'].nunique()} monthly cohorts {d['month'].min()}–{d['month'].max()}, "
             f"{d['ticker'].nunique():,} stocks. Market light in those months: "
             + ", ".join(f"{k} {v}" for k, v in light.reindex(sorted(d['month'].unique())).value_counts().items()) + ".")
    L.append("")
    emo = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
    L.append("## Whole check: 12-month outcome by colour")
    L.append("| colour | stock-months | 12-m return (avg of cohorts) | vs universe (all cohorts) | vs universe, June cohorts (t) | disasters ≤ −40 % |")
    L.append("|---|--:|--:|--:|--:|--:|")
    a, e = summarise(d, "colour", "fwd"), summarise(d, "colour", "excess")
    for g in ("green", "yellow", "red"):
        if g in a.index:
            L.append(f"| {emo[g]} {g} | {int(a.at[g, 'n_obs']):,} | {100*a.at[g, 'mean_all']:+.1f} % | "
                     f"{100*e.at[g, 'mean_all']:+.1f} % | {100*e.at[g, 'mean_june']:+.1f} % ({e.at[g, 't_june']:+.2f}) | "
                     f"{100*a.at[g, 'disaster']:.1f} % |")
    L.append("")
    L.append("## Component 1: dilution rule (stock selection, same months)")
    d2 = d.copy()
    d2["share_group"] = np.where(d2["change"] >= 0.05, "dilution ≥ +5 %",
                                 np.where(d2["change"] <= -0.02, "buyback ≤ −2 %",
                                          np.where(d2["change"].notna(), "neutral", "no data")))
    e2 = summarise(d2, "share_group", "excess")
    L.append("| shares | stock-months | vs universe (all cohorts) | June cohorts (t) | disasters ≤ −40 % |")
    L.append("|---|--:|--:|--:|--:|")
    for g in ("buyback ≤ −2 %", "neutral", "dilution ≥ +5 %", "no data"):
        if g in e2.index:
            L.append(f"| {g} | {int(e2.at[g, 'n_obs']):,} | {100*e2.at[g, 'mean_all']:+.1f} % | "
                     f"{100*e2.at[g, 'mean_june']:+.1f} % ({e2.at[g, 't_june']:+.2f}) | {100*e2.at[g, 'disaster']:.1f} % |")
    L.append("")
    L.append("## Component 2: market light (timing — absolute returns of ALL stocks bought in that month)")
    a3 = summarise(d, "light", "fwd")
    L.append("| market light at purchase | stock-months | avg 12-m return | disasters ≤ −40 % |")
    L.append("|---|--:|--:|--:|")
    for g in ("green", "yellow", "red"):
        if g in a3.index:
            L.append(f"| {emo[g]} {g} | {int(a3.at[g, 'n_obs']):,} | {100*a3.at[g, 'mean_all']:+.1f} % | "
                     f"{100*a3.at[g, 'disaster']:.1f} % |")
    L.append("")
    L.append("Reading: the dilution rule is about WHICH stock (relative columns); the market light is about WHEN "
             "(absolute columns). Few red-light months in 2010–2025 (mainly 2020) → the timing part has little "
             "evidence here; #45–#47 tested it over 1928–2026.")
    return "\n".join(L)
