from app.features.documents.ingestion.parser import parse_document


def _write(tmp_path, name: str, data: bytes):
    path = tmp_path / name
    path.write_bytes(data)
    return path


async def test_plain_utf8_txt_parses_unchanged(tmp_path):
    text = "(.venv) E:\\wikm\\STT>python transcribe.py\nخروجی: تست فارسی\n"
    path = _write(tmp_path, "note.txt", text.encode("utf-8"))

    result = parse_document(str(path))

    assert result == text
    assert "\x00" not in result


async def test_utf16_le_with_bom_is_decoded_correctly(tmp_path):
    """Reproduces the bug report: a Windows-originated transcript (e.g. from
    PowerShell's Start-Transcript) saved as UTF-16LE. A naive
    `read_text(encoding="utf-8")` doesn't raise on this - every ASCII byte
    followed by a NUL byte is individually valid UTF-8 - so it silently
    corrupts the text with a literal NUL after every character, which
    Postgres then rejects outright on insert."""
    text = "(.venv) E:\\wikm\\STT\\STT>python transcribe.py\nمتن فارسی تستی\n"
    path = _write(tmp_path, "transcript.txt", text.encode("utf-16"))  # adds a BOM

    result = parse_document(str(path))

    assert result == text
    assert "\x00" not in result


async def test_utf16_le_without_bom_is_still_detected_by_heuristic(tmp_path):
    text = "plain ascii transcript content with no special characters at all"
    path = _write(tmp_path, "no-bom.txt", text.encode("utf-16-le"))

    result = parse_document(str(path))

    assert result == text
    assert "\x00" not in result


async def test_utf8_with_bom_strips_the_bom(tmp_path):
    text = "hello world"
    path = _write(tmp_path, "bom.txt", b"\xef\xbb\xbf" + text.encode("utf-8"))

    result = parse_document(str(path))

    assert result == text


# --- office formats -------------------------------------------------------------------------------------------------

import shutil
import subprocess

import pytest

from app.features.documents.ingestion.parser import SUPPORTED_EXTENSIONS, parse_document_pages

needs_soffice = pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice not installed")


def _xlsx(tmp_path, rows_by_sheet: dict[str, list[list]]):
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, rows in rows_by_sheet.items():
        sheet = workbook.create_sheet(title)
        for row in rows:
            sheet.append(row)
    path = tmp_path / "book.xlsx"
    workbook.save(path)
    return path


def _soffice_convert(src, fmt: str, out_dir):
    subprocess.run(
        ["soffice", f"-env:UserInstallation=file://{out_dir}/profile", "--headless", "--convert-to", fmt, "--outdir", str(out_dir), str(src)],
        check=True, capture_output=True, timeout=120,
    )


def test_xlsx_keeps_columns_aligned_and_formats_values(tmp_path):
    import datetime

    path = _xlsx(tmp_path, {"قیمت": [["ردیف", "شرح", "مبلغ"], [1, None, 2500.0], [2, "بتن", 1.5], [None, None, None]],
                            "خالی": [[None]]})

    pages = parse_document_pages(str(path))

    assert len(pages) == 1  # the empty sheet yields nothing
    lines = pages[0].text.splitlines()
    assert lines[1] == "ردیف | شرح | مبلغ"
    assert lines[2] == "1 |  | 2500"  # empty cell kept, 2500.0 -> 2500
    assert lines[3] == "2 | بتن | 1.5"
    assert pages[0].metadata["sheet_name"] == "قیمت"
    assert datetime  # (date formatting covered below)


def test_xlsx_large_sheet_is_paged_with_header_repeated(tmp_path):
    rows = [["id", "name"]] + [[i, f"item{i}"] for i in range(1, 151)]
    path = _xlsx(tmp_path, {"S": rows})

    pages = parse_document_pages(str(path))

    assert len(pages) == 3  # 151 rows / 60
    assert [p.page_number for p in pages] == [1, 2, 3]
    assert pages[1].text.splitlines()[1] == "id | name"  # header repeated
    assert "item150" in pages[2].text
    assert pages[2].metadata["sheet_name"] == "S"


def test_xlsx_dates_render_without_midnight_time(tmp_path):
    import datetime

    path = _xlsx(tmp_path, {"S": [["d"], [datetime.datetime(2024, 3, 5)], [datetime.datetime(2024, 3, 5, 14, 30)]]})

    text = parse_document_pages(str(path))[0].text

    assert "2024-03-05\n" in text + "\n" and "2024-03-05 14:30:00" in text and "T00:00:00" not in text


def test_csv_is_supported_and_detects_delimiter(tmp_path):
    path = _write(tmp_path, "t.csv", "نام;مقدار\nالف;10\nب;20\n".encode("utf-8"))

    pages = parse_document_pages(str(path))

    assert pages[0].text.splitlines()[1:] == ["نام | مقدار", "الف | 10", "ب | 20"]


def test_docx_keeps_body_order_headings_and_dedupes_merged_cells(tmp_path):
    import docx

    document = docx.Document()
    document.add_heading("فصل اول", level=1)
    document.add_paragraph("قبل از جدول")
    table = document.add_table(rows=2, cols=3)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "عنوان ادغام"
    table.cell(0, 2).text = "C"
    for i in range(3):
        table.cell(1, i).text = f"v{i}"
    document.add_paragraph("بعد از جدول")
    path = tmp_path / "d.docx"
    document.save(path)

    text = parse_document_pages(str(path))[0].text

    assert text.index("# فصل اول") < text.index("قبل از جدول") < text.index("عنوان ادغام | C") < text.index("v0 | v1 | v2") < text.index("بعد از جدول")


def test_all_legacy_office_extensions_are_supported():
    assert {".xls", ".doc", ".ppt", ".rtf", ".odt", ".ods", ".odp", ".csv"} <= SUPPORTED_EXTENSIONS


@needs_soffice
def test_xls_is_converted_and_parsed(tmp_path):
    src = _xlsx(tmp_path, {"برآورد": [["شرح", "مقدار"], ["خاکبرداری", 120]]})
    out = tmp_path / "out"
    out.mkdir()
    _soffice_convert(src, "xls", out)

    pages = parse_document_pages(str(out / "book.xls"))

    assert "خاکبرداری | 120" in pages[0].text
    assert pages[0].metadata["sheet_name"] == "برآورد"


@needs_soffice
def test_doc_is_converted_and_parsed(tmp_path):
    import docx

    document = docx.Document()
    document.add_paragraph("متن قرارداد پیمان")
    src = tmp_path / "c.docx"
    document.save(src)
    out = tmp_path / "out"
    out.mkdir()
    _soffice_convert(src, "doc:MS Word 97", out)

    pages = parse_document_pages(str(out / "c.doc"))

    assert "متن قرارداد پیمان" in pages[0].text


@needs_soffice
def test_corrupt_legacy_file_raises_a_clear_error(tmp_path):
    from app.core.exceptions import BadRequestError

    path = _write(tmp_path, "broken.xls", b"this is not a spreadsheet")

    with pytest.raises(BadRequestError):
        parse_document_pages(str(path))
