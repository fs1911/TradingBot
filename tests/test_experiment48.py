"""
Tests for experiment #48: insider purchases as a buy signal.
"""
import io
import zipfile

import numpy as np
import pandas as pd

from src.backtest.experiments_48 import (
    parse_quarter_zip, signals, event_returns, calendar_portfolio, run_experiment48_report,
)


def _zip(rows):
    sub = "ACCESSION_NUMBER\tFILING_DATE\tPERIOD_OF_REPORT\tDOCUMENT_TYPE\tISSUERCIK\tISSUERNAME\tISSUERTRADINGSYMBOL\n"
    tr = ("ACCESSION_NUMBER\tNONDERIV_TRANS_SK\tSECURITY_TITLE\tTRANS_DATE\tTRANS_CODE\tTRANS_SHARES\t"
          "TRANS_PRICEPERSHARE\tTRANS_ACQUIRED_DISP_CD\n")
    own = "ACCESSION_NUMBER\tRPTOWNERCIK\tRPTOWNERNAME\tRPTOWNER_RELATIONSHIP\n"
    for i, (tic, fdate, tdate, code, sh, px, owner) in enumerate(rows):
        acc = f"A{i}"
        sub += f"{acc}\t{fdate}\t{tdate}\t4\t1\tX\t{tic}\n"
        tr += f"{acc}\t{i}\tCommon\t{tdate}\t{code}\t{sh}\t{px}\tA\n"
        own += f"{acc}\t{owner}\tN\tDirector\n"
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("SUBMISSION.tsv", sub)
        z.writestr("NONDERIV_TRANS.tsv", tr)
        z.writestr("REPORTINGOWNER.tsv", own)
    return b.getvalue()


def test_parse_and_signals():
    rows = [("abc", "05-JAN-2015", "02-JAN-2015", "P", 1000, 50, "o1"),
            ("ABC", "10-JAN-2015", "08-JAN-2015", "P", 1000, 50, "o2"),
            ("ABC", "20-JAN-2015", "18-JAN-2015", "P", 1000, 50, "o3"),
            ("ABC", "21-JAN-2015", "18-JAN-2015", "S", 9000, 50, "o4"),     # sale ignored
            ("XYZ", "03-MAR-2015", "01-MAR-2015", "P", 20000, 30, "o9")]    # $600k single buy
    p = parse_quarter_zip(_zip(rows))
    assert len(p) == 4 and set(p["ticker"]) == {"ABC", "XYZ"}
    s = signals(p)
    assert list(s["A cluster"]["ticker"]) == ["ABC"]
    assert s["A cluster"]["date"].iloc[0] == pd.Timestamp("2015-01-20")   # 3rd insider's filing
    assert list(s["B large"]["ticker"]) == ["XYZ"]


def test_event_returns_and_calendar():
    idx = pd.bdate_range("2014-01-01", periods=800)
    spy = pd.Series(np.linspace(100, 120, 800), index=idx)
    px = pd.Series(np.linspace(50, 80, 800), index=idx)
    r = event_returns(px, spy, pd.Timestamp("2015-01-20"))
    assert r and r["3M"] > 0
    ev = pd.DataFrame({"ticker": ["ABC"], "date": [pd.Timestamp("2015-01-20")]})
    cp = calendar_portfolio(ev, {"ABC": px}, spy)
    assert len(cp) >= 6


def test_report_smoke():
    rows = [("ABC", "05-JAN-2015", "02-JAN-2015", "P", 1000, 50, "o1"),
            ("ABC", "10-JAN-2015", "08-JAN-2015", "P", 1000, 50, "o2"),
            ("ABC", "20-JAN-2015", "18-JAN-2015", "P", 1000, 50, "o3")]
    p = parse_quarter_zip(_zip(rows))
    idx = pd.bdate_range("2012-01-01", periods=1500)
    rng = np.random.default_rng(0)
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 1500))), index=idx)
    px = pd.Series(50 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, 1500))), index=idx)
    rep = run_experiment48_report(p, [], {"ABC": px}, spy)
    assert "Experiment #48" in rep and "Signal A cluster" in rep
    assert "No data" in run_experiment48_report(pd.DataFrame(), ["2006q1: x"], {}, spy)
