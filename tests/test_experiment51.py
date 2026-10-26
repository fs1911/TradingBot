import io
import zipfile
import numpy as np
import pandas as pd

from src.backtest.experiments_51 import (list_13f_zips, parse_13f_zip, build_portfolios, run_portfolio,
                                         run_experiment51_report)


def _zip():
    sub = ("ACCESSION_NUMBER\tFILING_DATE\tSUBMISSIONTYPE\tPERIODOFREPORT\n"
           "A1\t14-FEB-2020\t13F-HR\t31-DEC-2019\n"
           "A2\t14-FEB-2020\t13F-HR/A\t31-DEC-2019\n"
           "A3\t13-FEB-2020\t13F-HR\t31-DEC-2019\n")
    cov = ("ACCESSION_NUMBER\tFILINGMANAGER_NAME\tISAMENDMENT\n"
           "A1\tBerkshire Hathaway Inc\tN\n"
           "A2\tBerkshire Hathaway Inc\tY\n"
           "A3\tSome Random Capital LLC\tN\n")
    info = ("ACCESSION_NUMBER\tNAMEOFISSUER\tCUSIP\tVALUE\tPUTCALL\n"
            "A1\tAPPLE INC\t037833100\t100\t\n"
            "A1\tAPPLE INC\t037833100\t50\t\n"
            "A1\tAPPLE INC\t037833100\t999\tPut\n"
            "A1\tCOCA COLA\t191216100\t30\t\n"
            "A2\tAPPLE INC\t037833100\t5\t\n"
            "A3\tAPPLE INC\t037833100\t7\t\n")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("2020q1_form13f/SUBMISSION.tsv", sub)
        z.writestr("2020q1_form13f/COVERPAGE.tsv", cov)
        z.writestr("2020q1_form13f/INFOTABLE.tsv", info)
    b.seek(0)
    return b


def test_list_zips():
    html = '<a href="/files/structureddata/data/form-13f-data-sets/01dec2023-29feb2024_form13f.zip">x</a>' \
           '<a href="/other.pdf">y</a>'
    out = list_13f_zips(html)
    assert out == ["https://www.sec.gov/files/structureddata/data/form-13f-data-sets/01dec2023-29feb2024_form13f.zip"]


def test_parse_selects_manager_skips_amendments_and_options():
    h = parse_13f_zip(_zip())
    assert set(h["manager"]) == {"Berkshire Hathaway"}
    assert set(h["ACCESSION_NUMBER"]) == {"A1"}
    aapl = h[h["cusip"] == "037833100"]["value"].iloc[0]
    assert aapl == 150          # the PUT row and the amendment are excluded
    assert h["filed"].iloc[0] == pd.Timestamp("2020-02-14")


def _holdings():
    rows = []
    for mgr, acc, filed, pos in [
        ("Berkshire Hathaway", "B1", "2020-02-14", {"AAA": 300, "BBB": 100}),
        ("Appaloosa", "P1", "2020-02-10", {"CCC": 50, "DDD": 40, "EEE": 30, "FFF": 1}),
        ("Baupost", "U1", "2020-02-10", {"CCC": 10, "DDD": 10, "GGG": 5}),
        ("Third Point", "T1", "2020-02-10", {"CCC": 10, "DDD": 2}),
    ]:
        for t, v in pos.items():
            rows.append({"manager": mgr, "ACCESSION_NUMBER": acc, "filed": pd.Timestamp(filed), "ticker": t,
                         "value": v, "cusip": t, "period": pd.Timestamp("2019-12-31"), "issuer": t})
    return pd.DataFrame(rows)


def test_build_portfolios_point_in_time_and_rules():
    months = pd.period_range("2020-01", "2020-10", freq="M")
    p = build_portfolios(_holdings(), months, max_age_months=6)
    a = p["A Berkshire clone"]
    assert pd.Period("2020-02", "M") not in a          # filed in Feb → usable from March
    assert abs(a[pd.Period("2020-03", "M")]["AAA"] - 0.75) < 1e-12
    assert pd.Period("2020-09", "M") not in a          # older than 6 months
    c = p["C Consensus (≥3 funds)"][pd.Period("2020-03", "M")]
    assert set(c.index) == {"CCC", "DDD"}
    b = p["B Best ideas (top 3 each)"][pd.Period("2020-03", "M")]
    assert "FFF" not in b.index and "CCC" in b.index
    d = p["D All holdings (EW)"][pd.Period("2020-03", "M")]
    assert set(d.index) == {"CCC", "DDD", "EEE", "FFF", "GGG"}


def test_run_portfolio_weights_returns():
    rets = pd.DataFrame({"X": [0.1, 0.2], "Y": [0.0, np.nan]}, index=pd.period_range("2020-01", periods=2, freq="M"))
    sel = {pd.Period("2020-01", "M"): pd.Series({"X": 0.5, "Y": 0.5}),
           pd.Period("2020-02", "M"): pd.Series({"X": 0.5, "Y": 0.5})}
    r = run_portfolio(sel, rets)
    assert abs(r.iloc[0] - 0.05) < 1e-12 and abs(r.iloc[1] - 0.2) < 1e-12


def test_report_runs_on_synthetic():
    idx = pd.bdate_range("2013-01-01", "2024-12-31")
    rng = np.random.default_rng(0)
    prices = {t: pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(idx)))), index=idx)
              for t in "AAA BBB CCC DDD EEE FFF GGG".split()}
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(idx)))), index=idx)
    base = _holdings()
    h = pd.concat([base.assign(filed=base["filed"] + pd.DateOffset(months=3 * q),
                               ACCESSION_NUMBER=base["ACCESSION_NUMBER"] + str(q)) for q in range(-25, 20)])
    rep = run_experiment51_report(h, 10, [], prices, spy)
    assert "A Berkshire clone" in rep and "SPY" in rep and "Best ideas − all holdings" in rep
