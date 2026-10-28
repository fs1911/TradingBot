"""
Experiment #59 — power analysis: how many years does it take to tell skill from luck?

With yearly excess return α over a benchmark and tracking error TE (volatility of the
excess return), the t-statistic after n years is t = α·√n / TE. So the years needed to
reach a target t are

        n = (t · TE / α)².

  A Years needed for t = 2 (classic 5 %), t = 3 (Harvey–Liu–Zhu) and t = 3.7
    (Bonferroni over this project's ~270 trials), for α 0.5–5 % and TE 2–20 %.
  B Tracking errors measured in THIS project (#50 buybacks, #51 Berkshire clone,
    #56 factor portfolios, a typical active fund) → years needed for each.
  C Power and false positives after 10 / 20 / 30 years for a truly skilled manager
    (α = 2 %, TE = 6 %) and a skill-less one (α = 0): P(t > 2).
  D Bayes: if 10 % of managers truly have α = 2 % (rest 0, fee-free), what share of
    managers with t > 2 after 10 years actually have skill?
  E Even with real skill, how often does the skilled manager LAG the index over
    1, 3, 5, 10 years? (what makes investors give up)
Pure, no data.
"""
from __future__ import annotations
import math

ALPHAS = (0.005, 0.01, 0.02, 0.03, 0.05)
TES = (0.02, 0.04, 0.06, 0.08, 0.12, 0.20)

# (label, excess p.a., t, years) as measured in this project → implied TE = α·√n / t
MEASURED = [
    ("#50 buyback quintile vs universe", 0.026, 3.01, 17),
    ("#50b app rule (shares −2 %)", 0.021, 2.80, 17),
    ("#51 Berkshire clone vs SPY", -0.021, -0.99, 13.2),
    ("#56 momentum big, developed 2011→", 0.002, 0.18, 15.7),
    ("#56 quality big, developed 2011→", 0.012, 1.32, 15.7),
    ("#56 small value, developed 2011→", -0.020, -1.00, 15.7),
]


def _phi(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def years_needed(alpha: float, te: float, t: float = 2.0) -> float:
    return (t * te / alpha) ** 2 if alpha > 0 else float("inf")


def implied_te(alpha: float, t: float, years: float) -> float:
    return abs(alpha) * math.sqrt(years) / abs(t) if t else float("nan")


def power(alpha: float, te: float, years: float, t_crit: float = 2.0) -> float:
    """P(t > t_crit) when the true excess is alpha (t ~ Normal(alpha·√n/TE, 1))."""
    return 1 - _phi(t_crit - alpha * math.sqrt(years) / te)


def skilled_share(prior: float, alpha: float, te: float, years: float, t_crit: float = 2.0) -> float:
    tp = prior * power(alpha, te, years, t_crit)
    fp = (1 - prior) * power(0.0, te, years, t_crit)
    return tp / (tp + fp) if tp + fp > 0 else float("nan")


def p_lag(alpha: float, te: float, years: float) -> float:
    """P(cumulative excess < 0 over `years`) for a manager with true alpha."""
    return _phi(-alpha * math.sqrt(years) / te)


def _y(n: float) -> str:
    if not math.isfinite(n):
        return "∞"
    return f"{n:,.0f}" if n >= 10 else f"{n:.1f}"


def run_experiment59_report() -> str:
    from datetime import datetime, timezone
    L = [f"# Experiment #59 — how many years to tell skill from luck? ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", ""]
    L.append("t after n years = α·√n / TE  ⇒  years needed n = (t·TE/α)². α = true yearly edge over the benchmark, "
             "TE = tracking error (yearly volatility of the difference to the benchmark).")
    L.append("")
    for t, label in ((2.0, "t = 2 (the usual '95 %')"), (3.0, "t = 3 (Harvey–Liu–Zhu threshold)"),
                     (3.7, "t = 3.7 (Bonferroni over this project's ~270 trials)")):
        L.append(f"## A Years needed for {label}")
        L.append("| true edge α | " + " | ".join(f"TE {int(te*100)} %" for te in TES) + " |")
        L.append("|---|" + "--:|" * len(TES))
        for a in ALPHAS:
            L.append(f"| {100*a:.1f} %/yr | " + " | ".join(_y(years_needed(a, te, t)) for te in TES) + " |")
        L.append("")
    L.append("Typical tracking errors: index-near fund 2–4 %, active stock fund 4–8 %, concentrated stock picker / "
             "single factor 8–12 %, few stocks or one sector 15–25 %.")
    L.append("")
    L.append("## B Tracking errors measured in this project")
    L.append("| strategy | edge p.a. | t | years | implied TE | years for t = 2 at that edge | for t = 3 |")
    L.append("|---|--:|--:|--:|--:|--:|--:|")
    for name, a, t, n in MEASURED:
        te = implied_te(a, t, n)
        L.append(f"| {name} | {100*a:+.1f} % | {t:+.2f} | {n:g} | {100*te:.1f} % | "
                 f"{_y(years_needed(a, te, 2.0)) if a > 0 else '— (negative)'} | "
                 f"{_y(years_needed(a, te, 3.0)) if a > 0 else '—'} |")
    L.append("")
    a, te = 0.02, 0.06
    L.append(f"## C A truly skilled manager (α = {100*a:.0f} %, TE = {100*te:.0f} %) vs a skill-less one")
    L.append("| after | P(skilled shows t > 2) | P(skill-less shows t > 2) |")
    L.append("|---|--:|--:|")
    for n in (5, 10, 20, 30, 50):
        L.append(f"| {n} years | {100*power(a, te, n):.0f} % | {100*power(0.0, te, n):.1f} % |")
    L.append("")
    L.append("## D Bayes: of the managers with t > 2 after 10 years, how many really have skill?")
    L.append("| share of truly skilled managers (α 2 %, TE 6 %) | share of 't > 2 after 10 y' that are skilled |")
    L.append("|---|--:|")
    for prior in (0.01, 0.05, 0.10, 0.25):
        L.append(f"| {100*prior:.0f} % | {100*skilled_share(prior, a, te, 10):.0f} % |")
    L.append("")
    L.append(f"## E Even real skill (α = {100*a:.0f} %, TE = {100*te:.0f} %) often looks like failure")
    L.append("| period | P(skilled manager is BEHIND the index) |")
    L.append("|---|--:|")
    for n in (1, 3, 5, 10, 20):
        L.append(f"| {n} year{'s' if n > 1 else ''} | {100*p_lag(a, te, n):.0f} % |")
    L.append("")
    L.append("**Reading:** with a realistic edge of 1–2 % and a tracking error of 6–8 %, it takes 36–256 years to "
             "reach t = 2 — longer than a career. A 10-year track record therefore cannot separate a skilled "
             "manager from a lucky one, and a genuinely skilled one lags the index in about a quarter of all "
             "5-year periods. That is why star track records say little, and why every claim of a proven edge "
             "should be met with: over how many years, against which benchmark, after how many trials?")
    L.append("")
    L.append("**Counterpoint (honest):** broad, rule-based tilts over hundreds of stocks have LOW tracking error "
             "(#50 buybacks ≈ 3.6 %), so a 2–3 % edge becomes testable in 7–9 years — that is why #50 could reach "
             "t ≈ 3 in 17 years. Concentrated stock picking (TE 15–25 %) can essentially never be proven.")
    return "\n".join(L)
