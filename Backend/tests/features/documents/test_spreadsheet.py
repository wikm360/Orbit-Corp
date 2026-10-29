import pytest
from openpyxl import Workbook

from app.core.exceptions import BadRequestError
from app.features.documents import spreadsheet


def _workbook(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["نام", "شماره بیمه", "دستمزد", 29, None, "محل"])
    ws.append(["علیرضا پاریاب", 65913003, "15,979,160", 1, None, "معدن"])
    ws.append(["سید رسول موسوی", 65085092, "۱۶۷۲۱۰۹۶", 2, None, "عسلویه"])  # Persian digits as text
    ws.append(["حسن شهبا", None, 0, 3, None, "معدن"])
    ws.append([None, None, None, None, None, None])
    ws.append(["مصطفى كريمي", 1, 5, 4, None, "معدن"])  # Arabic ى / ك
    wb.create_sheet("Sheet2").append(["a", "b"])
    wb["Sheet2"].append([1, 2])
    wb.save(path)
    return str(path)


def _query(tables, sql, **kwargs):
    return spreadsheet.run_query(tables, sql, max_rows=kwargs.pop("max_rows", 50), timeout_seconds=5)


def test_columns_named_typed_and_row_numbers_kept(tmp_path):
    tables = spreadsheet.load_tables(_workbook(tmp_path / "a.xlsx"))
    sheet = tables[0]
    assert [c.name for c in sheet.columns] == ["نام", "شماره بیمه", "دستمزد", "ستون_D (29)", "ستون_E", "محل"]
    assert [c.synthetic for c in sheet.columns] == [False, False, False, True, True, False]
    assert sheet.columns[2].type == "INTEGER"  # '15,979,160' and '۱۶۷۲۱۰۹۶' are numbers
    assert sheet.row_numbers == [2, 3, 4, 6]  # the blank row 5 is skipped, numbering is the file's own


def test_lookup_aggregate_and_row_reference(tmp_path):
    tables = spreadsheet.load_tables(_workbook(tmp_path / "a.xlsx"))
    result = _query(tables, "SELECT _row, دستمزد FROM Sheet1 WHERE نام LIKE '%پاریاب%'")
    assert result.rows == [[2, 15979160]]
    total = _query(tables, 'SELECT SUM("دستمزد"), COUNT(*) FROM "Sheet1" WHERE "محل" = \'معدن\'')
    assert total.rows == [[15979165, 3]]
    assert _query(tables, "SELECT a + b FROM Sheet2").rows == [[3]]


def test_literals_are_normalized_like_stored_text(tmp_path):
    tables = spreadsheet.load_tables(_workbook(tmp_path / "a.xlsx"))
    arabic = _query(tables, "SELECT _row FROM Sheet1 WHERE نام LIKE '%مصطفي كريمي%'")  # Arabic ي/ك typed by the user
    assert arabic.rows == [[6]]


def test_no_match_suggests_similar_names(tmp_path):
    tables = spreadsheet.load_tables(_workbook(tmp_path / "a.xlsx"))
    result = _query(tables, "SELECT * FROM Sheet1 WHERE نام LIKE '%حسین شهبا%'")
    assert result.rows == []
    assert any("حسن شهبا" in s for s in result.suggestions)


def test_truncation_flag(tmp_path):
    tables = spreadsheet.load_tables(_workbook(tmp_path / "a.xlsx"))
    result = _query(tables, "SELECT _row FROM Sheet1", max_rows=2)
    assert len(result.rows) == 2 and result.truncated


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE Sheet1",
        "DELETE FROM Sheet1",
        "SELECT 1; SELECT 2",
        "ATTACH DATABASE 'x.db' AS x",
        "PRAGMA table_info(Sheet1)",
        "SELECT load_extension('x')",
        "SELECT readfile('/etc/passwd')",
        "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT count(*) FROM c",
        "",
        "SELECT FROM WHERE",
    ],
)
def test_unsafe_or_invalid_sql_is_rejected(tmp_path, sql):
    tables = spreadsheet.load_tables(_workbook(tmp_path / "a.xlsx"))
    with pytest.raises(BadRequestError):
        _query(tables, sql)


def test_error_lists_real_columns(tmp_path):
    tables = spreadsheet.load_tables(_workbook(tmp_path / "a.xlsx"))
    with pytest.raises(BadRequestError, match="دستمزد"):
        _query(tables, "SELECT nope FROM Sheet1")


def test_cache_is_written_reused_and_cleaned(tmp_path):
    path = _workbook(tmp_path / "a.xlsx")
    first = spreadsheet.load_tables(path)
    cache = spreadsheet.tables_cache_path(path)
    assert cache.exists()
    assert spreadsheet.load_tables(path)[0].rows == first[0].rows
    spreadsheet.cleanup_tables_cache(path)
    assert not cache.exists()


def test_csv_and_non_spreadsheet(tmp_path):
    csv_path = tmp_path / "p.csv"
    csv_path.write_text("نام,مبلغ\nعلی,1000\nرضا,2500\n", encoding="utf-8")
    tables = spreadsheet.load_tables(str(csv_path))
    assert _query(tables, "SELECT SUM(مبلغ) FROM p").rows == [[3500]]
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    with pytest.raises(BadRequestError):
        spreadsheet.load_tables(str(pdf))
    assert not spreadsheet.is_spreadsheet(str(pdf))


def test_describe_marks_synthetic_columns_and_unknown_sheet(tmp_path):
    tables = spreadsheet.load_tables(_workbook(tmp_path / "a.xlsx"))
    text = spreadsheet.describe_tables(tables)
    assert "ستون_D (29) *" in text and "Sheet2" in text
    with pytest.raises(BadRequestError, match="Available sheets"):
        spreadsheet.describe_tables(tables, "nope")


def test_ingestion_text_is_one_named_record_per_row(tmp_path):
    from app.features.documents.ingestion.parser import parse_document_pages

    pages = parse_document_pages(_workbook(tmp_path / "a.xlsx"))
    first = pages[0].text
    assert "query_spreadsheet" in first
    assert "ردیف 2: نام: علیرضا پاریاب | شماره بیمه: 65913003 | دستمزد: 15979160 | ستون_D (29): 1 | محل: معدن" in first
    assert pages[0].metadata["sheet_name"] == "Sheet1"
    assert "ردیف 5" not in first  # the blank row is not a record
