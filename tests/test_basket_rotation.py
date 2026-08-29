"""
Tests for the small-basket rotation edge test (e.g. BTC/Gold/Dollar).
"""
import numpy as np
import pandas as pd

from src.backtest.basket_rotation import rotation_returns, run_rotation_report


def _df(closes):
    n = len(closes)
    idx = pd.date_range("2018-01-01", periods=n, freq="1D", tz="UTC")
    c = np.asarray(closes, float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=idx)


def _panel(cols):
    return pd.concat({k: v["close"] for k, v in cols.items()}, axis=1).dropna()


def test_top1_follows_strongest():
    """Asset A trends up, B and C flat → top1 rotation should ride A and end up."""
    n = 600
    a = _df(100 * (1.003) ** np.arange(n))
    b = _df(np.full(n, 100.0) + np.sin(np.arange(n) / 20))
    c = _df(np.full(n, 100.0))
    panel = pd.concat({"A": a["close"], "B": b["close"], "C": c["close"]}, axis=1).dropna()
    r = rotation_returns(panel, mode="top1", cash_col="C", lookback=63, hold=21)
    assert (1 + r).prod() > 1.0


def test_dual_goes_to_cash_when_risk_weak():
    """Both risk assets decline, cash flat → dual should sit in cash and avoid loss."""
    n = 600
    down1 = _df(200 - np.arange(n) * 0.2)
    down2 = _df(200 - np.arange(n) * 0.15)
    cash = _df(np.full(n, 100.0))
    panel = pd.concat({"R1": down1["close"], "R2": down2["close"], "USD": cash["close"]},
                      axis=1).dropna()
    r = rotation_returns(panel, mode="dual", cash_col="USD", lookback=63, hold=21)
    # sitting mostly in flat cash → tiny final drift, not a big loss
    assert (1 + r).prod() > 0.9


def test_report_wellformed():
    n = 700
    rng = np.random.default_rng(5)
    data = {
        "BTC/USD": _df(np.abs(100 + np.cumsum(rng.normal(0.1, 2.0, n))) + 20),
        "GLD": _df(np.abs(100 + np.cumsum(rng.normal(0.02, 0.5, n))) + 20),
        "UUP": _df(np.abs(100 + np.cumsum(rng.normal(0.0, 0.2, n))) + 20),
    }
    report = run_rotation_report(
        get_ohlcv=lambda sym, tf, limit: data[sym],
        baskets={"BTC_Gold_Dollar": {"symbols": list(data), "cash": "UUP"}},
        limit=n, window=252, step=126,
    )
    assert "Basket Rotation Edge Test" in report
    assert "Rotation top1" in report and "Rotation dual" in report
    assert "Walk-forward" in report
    assert "Hold BTC/USD" in report
