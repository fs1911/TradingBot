import io
import zipfile
import numpy as np
import pandas as pd

from src.backtest.experiments_76 import parse_sales_zip, sale_events, controls, run_experiment76_report


def _zip():
    sub = "ACCESSION_NUMBER\tFILING_DATE\tISSUERTRADINGSYMBOL\nA1\t05-MAR-2015\tXYZ\nA2\t06-MAR-2015\tXYZ\nA3\t09-MAR-2015\tXYZ\nA4\t09-MAR-2015\tXYZ\n"
    tr = ("ACCESSION_NUMBER\tTRANS_DATE\tTRANS_CODE\tTRANS_SHARES\tTRANS_PRICEPERSHARE\tTRANS_ACQUIRED_DISP_CD\n"
          "A1\t02-MAR-2015\tS\t10000\t50\tD\nA2\t03-MAR-2015\tS\t10000\t50\tD\nA3\t04-MAR-2015\tS\t20000\t50\tD\n"
          "A4\t04-MAR-2015\tP\t20000\t50\tA\n")
    own = "ACCESSION_NUMBER\tRPTOWNERCIK\nA1\t1\nA2\t2\nA3\t3\nA4\t4\n"
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("SUBMISSION.tsv", sub); z.writestr("NONDERIV_TRANS.tsv", tr); z.writestr("REPORTINGOWNER.tsv", own)
    return b.getvalue()


def test_parse_and_cluster():
    s = parse_sales_zip(_zip())
    assert len(s) == 3 and set(s["owner"]) == {"1", "2", "3"}
    ev = sale_events(s)
    assert len(ev["A cluster sale"]) == 1 and ev["A cluster sale"]["date"].iloc[0] == pd.Timestamp("2015-03-09")


def test_controls_and_report():
    d = pd.bdate_range("2012-01-01", "2020-12-31")
    rng = np.random.default_rng(0)
    prices = {"XYZ": pd.Series(50 * np.exp(np.cumsum(rng.normal(0, 0.01, len(d)))), index=d)}
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(d)))), index=d)
    ev = pd.DataFrame({"ticker": ["XYZ"], "date": [pd.Timestamp("2015-03-09")]})
    c = controls(ev, prices)
    assert len(c) == 1 and abs((c["date"].iloc[0] - ev["date"].iloc[0]).days) > 180
    rep = run_experiment76_report(parse_sales_zip(_zip()), [], prices, spy)
    assert "cluster sale" in rep and "calendar portfolio" in rep
