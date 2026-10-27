# Experiment #60 — FAILED

```
Traceback (most recent call last):
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/arrays/datetimes.py", line 2663, in _infer_tz_from_endpoints
    inferred_tz = timezones.infer_tzinfo(start, end)
  File "pandas/_libs/tslibs/timezones.pyx", line 369, in pandas._libs.tslibs.timezones.infer_tzinfo
AssertionError: Inputs must both have the same timezone, None != UTC

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/ubuntu/TradingBot/scripts/../src/bot.py", line 363, in _run_experiment60
    df = fetch_bars(self.broker._data, self.broker._crypto_data, sym, start, end, 1,
  File "/home/ubuntu/TradingBot/scripts/../src/backtest/experiments_60.py", line 41, in fetch_bars
    edges = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="MS", tz="UTC")
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/indexes/datetimes.py", line 1008, in date_range
    dtarr = DatetimeArray._generate_range(
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/arrays/datetimes.py", line 447, in _generate_range
    tz = _infer_tz_from_endpoints(start, end, tz)
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/arrays/datetimes.py", line 2666, in _infer_tz_from_endpoints
    raise TypeError(
TypeError: Start and end cannot both be tz-aware with different timezones

```
