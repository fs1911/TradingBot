# Experiment #59 — how many years to tell skill from luck? (2026-10-28 05:31 UTC)

t after n years = α·√n / TE  ⇒  years needed n = (t·TE/α)². α = true yearly edge over the benchmark, TE = tracking error (yearly volatility of the difference to the benchmark).

## A Years needed for t = 2 (the usual '95 %')
| true edge α | TE 2 % | TE 4 % | TE 6 % | TE 8 % | TE 12 % | TE 20 % |
|---|--:|--:|--:|--:|--:|--:|
| 0.5 %/yr | 64 | 256 | 576 | 1,024 | 2,304 | 6,400 |
| 1.0 %/yr | 16 | 64 | 144 | 256 | 576 | 1,600 |
| 2.0 %/yr | 4.0 | 16 | 36 | 64 | 144 | 400 |
| 3.0 %/yr | 1.8 | 7.1 | 16 | 28 | 64 | 178 |
| 5.0 %/yr | 0.6 | 2.6 | 5.8 | 10 | 23 | 64 |

## A Years needed for t = 3 (Harvey–Liu–Zhu threshold)
| true edge α | TE 2 % | TE 4 % | TE 6 % | TE 8 % | TE 12 % | TE 20 % |
|---|--:|--:|--:|--:|--:|--:|
| 0.5 %/yr | 144 | 576 | 1,296 | 2,304 | 5,184 | 14,400 |
| 1.0 %/yr | 36 | 144 | 324 | 576 | 1,296 | 3,600 |
| 2.0 %/yr | 9.0 | 36 | 81 | 144 | 324 | 900 |
| 3.0 %/yr | 4.0 | 16 | 36 | 64 | 144 | 400 |
| 5.0 %/yr | 1.4 | 5.8 | 13 | 23 | 52 | 144 |

## A Years needed for t = 3.7 (Bonferroni over this project's ~270 trials)
| true edge α | TE 2 % | TE 4 % | TE 6 % | TE 8 % | TE 12 % | TE 20 % |
|---|--:|--:|--:|--:|--:|--:|
| 0.5 %/yr | 219 | 876 | 1,971 | 3,505 | 7,885 | 21,904 |
| 1.0 %/yr | 55 | 219 | 493 | 876 | 1,971 | 5,476 |
| 2.0 %/yr | 14 | 55 | 123 | 219 | 493 | 1,369 |
| 3.0 %/yr | 6.1 | 24 | 55 | 97 | 219 | 608 |
| 5.0 %/yr | 2.2 | 8.8 | 20 | 35 | 79 | 219 |

Typical tracking errors: index-near fund 2–4 %, active stock fund 4–8 %, concentrated stock picker / single factor 8–12 %, few stocks or one sector 15–25 %.

## B Tracking errors measured in this project
| strategy | edge p.a. | t | years | implied TE | years for t = 2 at that edge | for t = 3 |
|---|--:|--:|--:|--:|--:|--:|
| #50 buyback quintile vs universe | +2.6 % | +3.01 | 17 | 3.6 % | 7.5 | 17 |
| #50b app rule (shares −2 %) | +2.1 % | +2.80 | 17 | 3.1 % | 8.7 | 20 |
| #51 Berkshire clone vs SPY | -2.1 % | -0.99 | 13.2 | 7.7 % | — (negative) | — |
| #56 momentum big, developed 2011→ | +0.2 % | +0.18 | 15.7 | 4.4 % | 1,938 | 4,361 |
| #56 quality big, developed 2011→ | +1.2 % | +1.32 | 15.7 | 3.6 % | 36 | 81 |
| #56 small value, developed 2011→ | -2.0 % | -1.00 | 15.7 | 7.9 % | — (negative) | — |

## C A truly skilled manager (α = 2 %, TE = 6 %) vs a skill-less one
| after | P(skilled shows t > 2) | P(skill-less shows t > 2) |
|---|--:|--:|
| 5 years | 10 % | 2.3 % |
| 10 years | 17 % | 2.3 % |
| 20 years | 31 % | 2.3 % |
| 30 years | 43 % | 2.3 % |
| 50 years | 64 % | 2.3 % |

## D Bayes: of the managers with t > 2 after 10 years, how many really have skill?
| share of truly skilled managers (α 2 %, TE 6 %) | share of 't > 2 after 10 y' that are skilled |
|---|--:|
| 1 % | 7 % |
| 5 % | 28 % |
| 10 % | 46 % |
| 25 % | 72 % |

## E Even real skill (α = 2 %, TE = 6 %) often looks like failure
| period | P(skilled manager is BEHIND the index) |
|---|--:|
| 1 year | 37 % |
| 3 years | 28 % |
| 5 years | 23 % |
| 10 years | 15 % |
| 20 years | 7 % |

**Reading:** with a realistic edge of 1–2 % and a tracking error of 6–8 %, it takes 36–256 years to reach t = 2 — longer than a career. A 10-year track record therefore cannot separate a skilled manager from a lucky one, and a genuinely skilled one lags the index in about a quarter of all 5-year periods. That is why star track records say little, and why every claim of a proven edge should be met with: over how many years, against which benchmark, after how many trials?

**Counterpoint (honest):** broad, rule-based tilts over hundreds of stocks have LOW tracking error (#50 buybacks ≈ 3.6 %), so a 2–3 % edge becomes testable in 7–9 years — that is why #50 could reach t ≈ 3 in 17 years. Concentrated stock picking (TE 15–25 %) can essentially never be proven.