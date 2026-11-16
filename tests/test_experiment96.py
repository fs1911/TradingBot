import io
import zipfile
import numpy as np
import pandas as pd

from src.backtest.experiments_96 import (parse_all_zip, clean_period, period_signals, evaluate, formation_month,
                                         run_experiment96_report, GROUPS)


def _zip(rows, subs):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("SUBMISSION.tsv", "ACCESSION_NUMBER\tFILING_DATE\tSUBMISSIONTYPE\tCIK\tPERIODOFREPORT\n" +
                   "".join(f"{a}\t{fd}\t{t}\t{cik}\t{pr}\n" for a, fd, t, cik, pr in subs))
        z.writestr("COVERPAGE.tsv", "ACCESSION_NUMBER\tISAMENDMENT\n" + "".join(f"{a}\tN\n" for a, *_ in subs))
        z.writestr("INFOTABLE.tsv", "ACCESSION_NUMBER\tCUSIP\tVALUE\tPUTCALL\n" +
                   "".join(f"{a}\t{c}\t{v}\t{pc}\n" for a, c, v, pc in rows))
    b.seek(0)
    return b


def test_parse_units_threshold_and_options():
    subs = [("A1", "10-FEB-2022", "13F-HR", 1, "31-DEC-2021"), ("A2", "10-FEB-2023", "13F-HR", 2, "31-DEC-2022"),
            ("A3", "10-FEB-2023", "13F-HR", 3, "31-DEC-2022"), ("A4", "10-FEB-2023", "13F-HR/A", 4, "31-DEC-2022")]
    rows = [("A1", "AAA", 2_000_000, ""), ("A1", "BBB", 1, "PUT"),     # $1000 units → 2bn
            ("A2", "AAA", 2_000_000_000, ""),                           # $ units → 2bn
            ("A3", "AAA", 5_000_000, ""),                               # too small
            ("A4", "AAA", 9e12, "")]                                    # amendment type ignored
    rows = [(a, {"AAA": "037833100", "BBB": "594918104"}[c], v, pc) for a, c, v, pc in rows]
    df = parse_all_zip(_zip(rows, subs))
    from src.backtest.experiments_96 import int_to_cusip
    assert sorted(df["cik"]) == [1, 2] and {int_to_cusip(x) for x in df["cusip"]} == {"037833100"}
    assert np.allclose(df["value"], 2e9)


def test_signals_and_clean():
    pe = pd.Timestamp("2022-03-31")
    raw = pd.DataFrame({"cik": [1, 1, 2], "period": [pe] * 3, "filed": [pe + pd.Timedelta(days=40), pe + pd.Timedelta(days=45), pe + pd.Timedelta(days=80)],
                        "cusip": ["X", "Y", "X"], "value": [1.0, 2.0, 3.0]})
    c = clean_period(raw, pe)
    assert list(c["cusip"]) == ["Y"]  # latest in-time filing of 1; late filer 2 dropped
    # 20 managers; stock S: 10 held last quarter, 15 now; N: newly bought by 4 with big weight
    prev = pd.DataFrame([(m, "S", 1.0) for m in range(10)] + [(m, f"F{m}", 50.0) for m in range(20)], columns=["cik", "cusip", "value"])
    cur = pd.DataFrame([(m, "S", 1.0) for m in range(15)] + [(m, f"F{m}", 50.0) for m in range(20)] +
                       [(m, "N", 10.0) for m in range(4)], columns=["cik", "cusip", "value"])
    sig = period_signals(cur, prev)
    a = sig[sig["group"] == GROUPS[0]].set_index("cusip")
    assert abs(a.at["S", "dbreadth"] - 5 / 20) < 1e-9 and a.at["S", "in_uni"]
    assert a.at["N", "conv_new"] == 4 and not a.at["N", "in_uni"]
    assert formation_month(pd.Timestamp("2022-03-31")) == pd.Period("2022-05", "M")


def test_evaluate_and_report():
    rng = np.random.default_rng(0)
    months = pd.period_range("2013-01", "2026-10", freq="M")
    ticks = [f"T{i}" for i in range(200)]
    closes = pd.DataFrame(np.exp(np.cumsum(rng.normal(0.005, 0.05, (len(months), 200)), axis=0)) * 20, index=months, columns=ticks)
    spy = pd.Series(np.exp(np.cumsum(rng.normal(0.008, 0.04, len(months)))) * 100, index=months)
    rows = []
    for pe in pd.date_range("2013-06-30", "2026-03-31", freq="QE"):
        for i, t in enumerate(ticks):
            rows.append({"period": pe, "cusip": f"C{i}", "group": GROUPS[0], "in_uni": True, "dbreadth": rng.normal(),
                         "hold_prev": 10, "conv_new": int(i < 5) * 3, "n_mgr": 300})
    sig = pd.DataFrame(rows)
    res = evaluate(sig, closes, spy, {f"C{i}": t for i, t in enumerate(ticks)})
    d = res[GROUPS[0]]
    assert len(d) > 40 and {"Q1", "Q5", "C", "turn_Q5"} <= set(d.columns)
    rep = run_experiment96_report(res)
    assert "Q5 − Q1 spread" in rep and "Holm" in rep
