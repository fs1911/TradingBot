import io
import zipfile
import numpy as np
import pandas as pd

from src.backtest.experiments_63 import (read_xlsx, find_links, quarterly, recession_analysis, unemployment_analysis,
                                         stock_anxiety, run_experiment63_report, auc)

M = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def make_xlsx(sheets: dict) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        sh_xml = "".join(f'<sheet name="{n}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i, n in enumerate(sheets))
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{M}" xmlns:r="{R}"><sheets>{sh_xml}</sheets></workbook>')
        rels = "".join(f'<Relationship Id="rId{i+1}" Target="worksheets/sheet{i+1}.xml" Type="x"/>'
                       for i in range(len(sheets)))
        z.writestr("xl/_rels/workbook.xml.rels",
                   f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>')
        for i, (n, df) in enumerate(sheets.items()):
            rows = []
            allrows = [list(df.columns)] + df.values.tolist()
            for r, vals in enumerate(allrows):
                cells = []
                for c, v in enumerate(vals):
                    ref = f"{_col(c)}{r+1}"
                    if isinstance(v, str):
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{v}</t></is></c>')
                    elif v is not None and not (isinstance(v, float) and np.isnan(v)):
                        cells.append(f'<c r="{ref}"><v>{v}</v></c>')
                rows.append(f'<row r="{r+1}">{"".join(cells)}</row>')
            z.writestr(f"xl/worksheets/sheet{i+1}.xml", f'<worksheet xmlns="{M}"><sheetData>{"".join(rows)}</sheetData></worksheet>')
    return b.getvalue()


def _spf():
    q = pd.period_range("1968Q4", "2024Q4", freq="Q")
    rng = np.random.default_rng(0)
    rec = pd.DataFrame({"YEAR": q.year, "QUARTER": q.quarter, "RECESS1": 20.0,
                        "RECESS2": rng.uniform(10, 30, len(q)), "RECESS5": 15.0})
    un = 5 + np.cumsum(rng.normal(0, 0.2, len(q)))
    unemp = pd.DataFrame({"YEAR": q.year, "QUARTER": q.quarter, "UNEMP1": un, "UNEMP6": un + 0.1})
    return rec, unemp


def test_reader_roundtrip():
    rec, _ = _spf()
    wb = read_xlsx(make_xlsx({"RECESS": rec.head(5)}))
    assert list(wb["RECESS"].columns) == ["YEAR", "QUARTER", "RECESS1", "RECESS2", "RECESS5"]
    assert wb["RECESS"]["YEAR"].iloc[0] == 1968.0


def test_find_links_filters():
    html = '<a href="/-/media/x/Median_Level.xlsx">a</a><a href="/logo.png">b</a><a href="/files/other.xlsx">c</a>'
    out = find_links(html, "https://www.philadelphiafed.org/page")
    assert out == ["https://www.philadelphiafed.org/-/media/x/Median_Level.xlsx"]


def test_auc_and_analyses():
    assert auc(np.array([0.9, 0.8, 0.1, 0.2]), np.array([1, 1, 0, 0])) == 1.0
    rec, unemp = _spf()
    rq = quarterly(rec)
    L = recession_analysis(rq)
    assert any("2008Q1" in l for l in L) and any("AUC" in l for l in L)
    assert "RMSE" in unemployment_analysis(quarterly(unemp))[0]
    m = pd.period_range("1968-01", "2025-12", freq="M")
    g = pd.Series(100 * np.exp(np.cumsum(np.full(len(m), 0.005))), index=m)
    assert any("quintile" in l for l in stock_anxiety(rq, g))


def test_report_end_to_end():
    rec, unemp = _spf()
    books = {"https://x/Mean_RECESS.xlsx": read_xlsx(make_xlsx({"RECESS": rec})),
             "https://x/Median_Level.xlsx": read_xlsx(make_xlsx({"UNEMP": unemp}))}
    d = pd.bdate_range("1965-01-01", "2025-12-31")
    g = pd.Series(np.linspace(100, 5000, len(d)), index=d)
    rep = run_experiment63_report(books, ["page → 2 links"], g)
    assert "Did the professionals see recessions" in rep and "RMSE" in rep and "Data discovery" in rep
    assert "AAII data not reachable" in rep and "No stock-price series" in rep


def test_stock10_vs_reality():
    from src.backtest.experiments_63 import stock10_analysis
    q = pd.period_range("1992Q1", "2026Q1", freq="Q")
    q1 = [p for p in q if p.quarter == 1]
    df = pd.DataFrame({"YEAR": [p.year for p in q1], "QUARTER": 1, "STOCK10": 7.0})
    books = {"https://x/medianLevel.xlsx": {"STOCK10": df}}
    m = pd.period_range("1990-01", "2026-09", freq="M")
    tr = pd.Series(100 * 1.08 ** (np.arange(len(m)) / 12), index=m)
    L = stock10_analysis(books, tr)
    assert any("expected avg 7.0 %" in l and "actual avg 8.0 %" in l for l in L)
