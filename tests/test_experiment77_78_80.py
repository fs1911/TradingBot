import numpy as np
import pandas as pd

from src.backtest.experiments_77_78_80 import (parse_submissions, ipo_events, parse_sp500_changes, index_effect,
                                               run_experiments77_78_80_report)


def test_parse_submissions_ipo():
    js = {"sic": "7372", "filings": {"recent": {"form": ["10-K", "424B4", "S-1/A", "S-1"],
                                                "filingDate": ["2021-03-01", "2020-06-10", "2020-06-01", "2020-04-01"]}}}
    r = parse_submissions(js)
    assert r["sic2"] == "73" and r["ipo_prospectus"] == pd.Timestamp("2020-06-10")
    assert parse_submissions({"filings": {"recent": {"form": ["10-K"], "filingDate": ["2020-01-01"]}}})["ipo_prospectus"] is None


def test_ipo_events_and_changes():
    d = pd.bdate_range("2020-06-12", "2024-12-31")
    prices = {"NEW": pd.Series(np.linspace(10, 5, len(d)), index=d),
              "OLD": pd.Series(10.0, index=pd.bdate_range("2010-01-01", "2024-12-31"))}
    subs = pd.DataFrame({"sic2": ["73", "10"], "ipo_prospectus": [pd.Timestamp("2020-06-10"), pd.Timestamp("2020-06-10")]},
                        index=[1, 2])
    ev = ipo_events(subs, {1: "NEW", 2: "OLD"}, prices)
    assert list(ev["ticker"]) == ["NEW"]
    page = ('<table id="changes"><tr><th>Date</th></tr><tr><td>June 22, 2020</td><td>NEW</td><td>New Co</td>'
            '<td>OLD</td><td>Old Co</td><td>x</td></tr></table>')
    ch = parse_sp500_changes(page)
    assert ch.iloc[0]["added"] == "NEW" and ch.iloc[0]["removed"] == "OLD"
    spy = pd.Series(100.0, index=pd.bdate_range("2010-01-01", "2024-12-31"))
    eff = index_effect(ch, prices, spy)
    assert eff["added"]["n"] == 0 or np.isfinite(eff["added"]["post250"])


def test_report():
    d = pd.bdate_range("2005-01-03", "2024-12-31")
    rng = np.random.default_rng(1)
    prices = {f"T{i}": pd.Series(20 * np.exp(np.cumsum(rng.normal(0, 0.02, len(d)))), index=d) for i in range(10)}
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(d)))), index=d)
    rep = run_experiments77_78_80_report(pd.DataFrame(), {}, prices, spy, pd.DataFrame(), "FINRA: not reachable")
    assert "#78" in rep and "#80" in rep and "FINRA" in rep


def test_changes_rowspan_and_attrs():
    page = ('<table class="wikitable" id="changes"><tbody><tr><th>Date</th><th>Added</th></tr>'
            '<tr style="x"><td rowspan="2">March 24, 2025</td><td>AAA</td><td>A Co</td><td>BBB</td><td>B Co</td><td>r</td></tr>'
            '<tr><td>CCC</td><td>C Co</td><td>DDD</td><td>D Co</td><td>r</td></tr></tbody></table>')
    ch = parse_sp500_changes(page)
    assert list(ch["added"]) == ["AAA", "CCC"] and list(ch["removed"]) == ["BBB", "DDD"]
    assert (ch["date"] == pd.Timestamp("2025-03-24")).all()


def test_changes_found_by_header():
    page = ('<table class="wikitable"><tr><th>Symbol</th></tr></table>'
            '<table class="wikitable sortable"><tr><th>Effective Date</th><th colspan="2">Added</th><th colspan="2">Removed</th></tr>'
            '<tr><td>June 22, 2020</td><td>NEW</td><td>New Co</td><td>OLD</td><td>Old Co</td><td>r</td></tr></table>')
    ch = parse_sp500_changes(page)
    assert list(ch["added"]) == ["NEW"]


def test_wikitext_changes():
    from src.backtest.experiments_77_78_80 import parse_sp500_wikitext
    wt = ("== Selected changes ==\n{| class=\"wikitable\"\n! Date\n|-\n|{{dts|2025|07|09}}\n|[[Block, Inc.|XYZ]]\n|Block\n"
          "|[[Hess Corporation|HES]]\n|Hess\n|Acquired.<ref>x</ref>\n|-\n|July 23, 2025\n"
          "|{{NasdaqSymbol|DDOG}} || Datadog || {{NyseSymbol|JNPR}} || Juniper || r\n|}\n")
    ch = parse_sp500_wikitext(wt)
    assert list(ch["added"]) == ["XYZ", "DDOG"] and list(ch["removed"]) == ["HES", "JNPR"]
