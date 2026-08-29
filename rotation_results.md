# Basket Rotation — FAILED

```
Traceback (most recent call last):
  File "/home/ubuntu/TradingBot/scripts/../src/bot.py", line 246, in _run_rotation
    report = run_rotation_report(get_ohlcv=self.broker.get_ohlcv, baskets=baskets)
  File "/home/ubuntu/TradingBot/scripts/../src/backtest/basket_rotation.py", line 107, in run_rotation_report
    f"{panel.index[0]:%Y-%m} → {panel.index[-1]:%Y-%m} ({len(panel)} days)")
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/indexes/base.py", line 5401, in __getitem__
    return getitem(key)
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/arrays/datetimelike.py", line 398, in __getitem__
    result = cast("Union[Self, DTScalarOrNaT]", super().__getitem__(key))
  File "/home/ubuntu/TradingBot/.venv/lib/python3.10/site-packages/pandas/core/arrays/_mixins.py", line 284, in __getitem__
    result = self._ndarray[key]
IndexError: index 0 is out of bounds for axis 0 with size 0

```
