# Experiment #99 — FAILED

```
Traceback (most recent call last):
  File "/home/ubuntu/TradingBot/scripts/../src/bot.py", line 1159, in _run_exp99
    rep = run_experiment99_report(sh, eq, gdp, diag)
  File "/home/ubuntu/TradingBot/scripts/../src/backtest/experiments_99.py", line 91, in run_experiment99_report
    bi = buffett_monthly(equities, gdp)
  File "/home/ubuntu/TradingBot/scripts/../src/backtest/experiments_99.py", line 44, in buffett_monthly
    full = pd.period_range(s.index.min(), s.index.max() + 2, freq="M")
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/indexes/period.py", line 611, in period_range
    data, freq = PeriodArray._generate_range(start, end, periods, freq)
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/arrays/period.py", line 343, in _generate_range
    subarr, freq = _get_ordinal_range(start, end, periods, freq)
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/arrays/period.py", line 1238, in _get_ordinal_range
    raise ValueError("start and end must not be NaT")
ValueError: start and end must not be NaT

```
