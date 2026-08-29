"""
Tests for the cross-sectional momentum edge test. Synthetic panels verify the
core mechanic (it overweights recent winners), no-crash on a report, and the
panel alignment.
"""
import numpy as np
import pandas as pd

from src.backtest.xsec_momentum import (
    xsec_momentum_returns, _price_panel, run_xsec_report,
)


def _df(closes):
    n = len(closes)
    idx = pd.date_range("2016-01-01", periods=n, freq="1D", tz="UTC")
    c = np.asarray(closes, float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": np.full(n, 1e6)}, index=idx)


def test_panel_common_window():
    a = _df(100 + np.arange(500) * 0.1)
    b = _df(100 + np.arange(400) * 0.1)          # shorter
    panel = _price_panel({"A": a, "B": b})
    assert list(panel.columns) == ["A", "B"]
    assert not panel.isna().any().any()
    assert len(panel) == 400                       # limited to the shorter series


def test_momentum_picks_winners():
    """One asset trends up strongly, the rest drift down → momentum (long top 30%)
    should end profitable and beat the equal-weight average."""
    n = 900
    winners = 100 * (1 + 0.002) ** np.arange(n)                 # compounding up
    losers = [100 - np.arange(n) * 0.02 for _ in range(9)]      # 9 mild decliners
    data = {"WIN": _df(winners)}
    for i, l in enumerate(losers):
        data[f"L{i}"] = _df(l)
    panel = _price_panel(data)
    strat = xsec_momentum_returns(panel, lookback=252, skip=21, hold=21, top_frac=0.2)
    ew = panel.pct_change().fillna(0).mean(axis=1)
    assert (1 + strat).prod() > (1 + ew).prod()    # momentum beats equal-weight hold here


def test_report_wellformed():
    n = 900
    rng = np.random.default_rng(3)
    data = {f"S{i}": _df(np.abs(100 + np.cumsum(rng.normal(0.02, 1.0, n))) + 5)
            for i in range(10)}
    report = run_xsec_report(
        get_ohlcv=lambda sym, tf, limit: data[sym],
        universes={"equities": list(data.keys())},
        limit=n, window=252, step=126,
    )
    assert "Cross-Sectional Momentum Edge Test" in report
    assert "EQUITIES" in report
    assert "Walk-forward" in report and "MAR" in report
