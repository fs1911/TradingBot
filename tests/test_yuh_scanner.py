import numpy as np
import pandas as pd

from src.scanner.yuh_scanner import (Asset, judge, scan, diff_states, format_changes, format_monthly, load_universe,
                                     GREEN, YELLOW, RED, summary_markdown)

D = pd.bdate_range("2023-01-02", periods=600)
UP = pd.Series(np.linspace(50, 100, 600), index=D)
DOWN = pd.Series(np.linspace(100, 50, 600), index=D)
TODAY = D[-1]


def test_judge_rules():
    s = Asset("A", "A", "stock")
    assert judge(s, UP, True, 0.9, -0.03, pd.Timestamp("2000-01-01"), TODAY).colour == GREEN
    assert judge(s, UP, True, 0.9, 0.06, pd.Timestamp("2000-01-01"), TODAY).colour == RED      # dilution
    assert judge(s, DOWN, True, 0.9, -0.03, None, TODAY).colour == RED                          # trend broken
    assert judge(s, UP, False, 0.9, -0.03, None, TODAY).colour == YELLOW                        # market weak
    assert judge(s, UP, True, 0.5, -0.03, None, TODAY).colour == YELLOW                         # weak momentum
    young = judge(s, UP, True, 0.9, -0.03, TODAY - pd.Timedelta(days=400), TODAY)
    assert young.colour == YELLOW and any("Börsengang" in r for r in young.reasons)
    assert judge(Asset("E", "E", "etf"), UP, True, float("nan"), float("nan"), None, TODAY).colour == GREEN
    assert judge(Asset("C", "C-USD", "crypto"), DOWN, True, float("nan"), float("nan"), None, TODAY).colour == RED
    assert judge(s, UP.iloc[:100], True, 0.9, 0, None, TODAY).colour == YELLOW


def test_scan_diff_and_messages(tmp_path):
    p = tmp_path / "u.csv"
    p.write_text("name,yahoo,type\nAlpha,AAA,stock\nBeta,BBB.SW,stock\nWorld,WRLD,etf\nXRP,XRP-USD,crypto\nbad,,stock\n")
    uni = load_universe(str(p))
    assert [a.yahoo for a in uni] == ["AAA", "BBB.SW", "WRLD", "XRP-USD"]
    prices = {"AAA": UP, "BBB.SW": DOWN, "WRLD": UP, "XRP-USD": UP}
    idx = {"SPY": UP, "^SSMI": UP, "^GDAXI": UP}
    v = scan(uni, prices, {}, {}, idx, TODAY)
    assert v["BBB.SW"].colour == RED and v["WRLD"].colour == GREEN and v["XRP-USD"].colour == GREEN
    new = {k: x.colour for k, x in v.items()}
    assert diff_states({}, new) == []
    prev = dict(new); prev["BBB.SW"] = GREEN
    ch = diff_states(prev, new)
    assert ch == [("BBB.SW", GREEN, RED)]
    names = {a.yahoo: a.name for a in uni}
    msg = format_changes(ch, v, names, TODAY)
    assert "Beta" in msg and "🟢→🔴" in msg
    kinds = {a.yahoo: a.kind for a in uni}
    assert "Monatsliste" in format_monthly(v, names, kinds, TODAY)
    assert "| 🔴 | Beta |" in summary_markdown(v, names, kinds, TODAY)


def test_universe_from_public_lists(tmp_path):
    from src.scanner.yuh_scanner import build_universe, write_universe, load_universe
    stocks = ("<table><tr><th></th><th>Company Name</th><th>Stock Market</th><th>Symbol</th><th>Currency</th></tr>"
              "<tr><td></td><td>3M</td><td>NYSE</td><td>MMM</td><td>USD</td></tr>"
              "<tr><td></td><td>ABB</td><td>SIX</td><td>ABBN</td><td>CHF</td></tr>"
              "<tr><td></td><td>Accor</td><td>EURONEXT</td><td>AC</td><td>EUR</td></tr>"
              "<tr><td></td><td>Berkshire</td><td>NYSE</td><td>BRK.B</td><td>USD</td></tr>"
              "<tr><td></td><td>Ghost</td><td>SIX</td><td>XXX</td><td>CHF</td></tr></table>")
    etfs = ("<table><tr><th></th><th>Yuh Designation</th><th>ETF Name</th><th>Ticker</th><th>ISIN</th><th>TER</th></tr>"
            "<tr><td></td><td>Benchmark: Nasdaq-100</td><td>Invesco EQQQ Nasdaq-100</td><td>EQQQ.USD</td><td>IE0032077012</td><td>0.30%</td></tr></table>")
    ok = {"MMM", "ABBN.SW", "AC.PA", "BRK-B", "EQQQ.SW", "BTC-USD", "XRP-USD"}
    rows, skipped = build_universe(stocks, etfs, lambda s: s in ok)
    ys = [r[1] for r in rows]
    assert ys[:5] == ["MMM", "ABBN.SW", "AC.PA", "BRK-B", "EQQQ.SW"] and "XRP-USD" in ys
    assert skipped == ["Ghost (SIX:XXX)"]
    p = tmp_path / "u.csv"
    write_universe(str(p), rows)
    assert len(load_universe(str(p))) == len(rows)
