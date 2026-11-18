"""Regressions found on the real 18-24 Aban 1405 files: summary tables under an EVM table, a column heading read as "forecast",
foreign-currency contracts, space-sensitive site names, xlsb, and which period a forecast file is for."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.features.volume_report.extraction.evm_parser import parse_evm_sheet
from app.features.volume_report.extraction.normalize import site_key
from app.features.volume_report.extraction.plan_month import is_period_title
from app.features.volume_report.extraction.probe import suggest_company
from app.features.volume_report.extraction.runner import extract_file
from app.features.volume_report.extraction.normalize import Lexicon
from app.features.volume_report.extraction.workbook import SheetData, WorkbookData
from app.features.volume_report import service

WEEK = Path("eval/volume_report/گزارش 18 تا 25")
B = 10**9
HEADER = [
    ["شرکت نمونه"],
    ["گزارش EVM"],
    ["ردیف", "نام پروژه", "مبلغ قرارداد (ریال)", "مدت", "BCWS-M", "(PV)", "(EV)", "(ev)", "(AC)", "CPI=ev/ac", "SPI=EV/PV"],
]


def test_weighted_average_row_ends_the_table_and_summary_tables_below_it_are_not_projects():
    rows = HEADER + [
        [1, "پروژه الف", 5 * B, 36, None, 20 * B, 169 * B, 130 * B, 111 * B, 1.17, 8.49],
        ["میانگین وزنی", None, None, None, None, 20 * B, 169 * B, 130 * B, 111 * B, 1.17, 8.49],
        [None, "T : مدت قرارداد"],
        [None, "خلاصه مالی"],
        [None, "کل درآمد", None, None, None, None, None, None, 169 * B],
        [None, "هزینه", None, None, None, None, None, None, 111 * B],
    ]
    parsed = parse_evm_sheet("EVM", rows)
    assert [r.project_name for r in parsed.rows] == ["پروژه الف", None]
    assert parsed.rows[1].is_total and parsed.rows[0].ac == Decimal(111 * B)


def test_footnotes_end_the_table_even_without_a_total_row():
    rows = HEADER + [
        [1, "پروژه الف", 5 * B, 36, None, 20 * B, 169 * B, 130 * B, 111 * B, 1.17, 8.49],
        [None, "T : مدت قرارداد"],
        [None, "هزینه", None, None, None, None, None, None, 111 * B],
    ]
    assert [r.project_name for r in parse_evm_sheet("EVM", rows).rows] == ["پروژه الف"]


def test_a_total_row_that_only_carries_a_plan_is_not_stored():
    rows = HEADER + [
        [1, "پروژه الف", 5 * B, 36, None, None, 100 * B, 77 * B, 51 * B, 1.5, None],
        ["جمع", None, None, None, 0.0, 0.0, None, None, None, None, 0.0],
    ]
    assert [r.is_total for r in parse_evm_sheet("EVM", rows).rows] == [False]


def test_contract_in_euro_is_not_taken_as_rial():
    rows = [list(r) for r in HEADER]
    rows[2][2] = "مبلغ قرارداد (یورو)"
    rows.append([1, "پروژه الف", 2_283_145, 36, None, None, 100 * B, 77 * B, 51 * B, 1.5, None])
    assert parse_evm_sheet("EVM", rows).rows[0].contract_amount is None


def test_a_column_heading_with_barnameh_does_not_make_an_actual_sheet_a_forecast():
    actual = [
        ["گزارش هزینه 1405/08/17 الی 1405/08/24 پروژه الف"],
        ["شاخص عملکرد برنامه (SPI)", "درآمد برنامه ای از ابتدای سال"],
        *HEADER[2:],
        [1, "پروژه الف", 5 * B, 36, None, None, 100 * B, 77 * B, 51 * B, 1.5, None],
    ]
    assert parse_evm_sheet("EVM", actual, "report.xlsx").basis == "actual"
    forecast = [["برنامه پروژه الف از 1405/08/18 الی 1405/08/24"], *HEADER[1:], [1, "پروژه الف", 5 * B, 36, None, None, 100 * B, 77 * B, 51 * B, 1.5, None]]
    assert parse_evm_sheet("EVM", forecast, "report.xlsx").basis == "planned"
    assert parse_evm_sheet("EVM", actual, "پیش بینی هفتگی.xlsx").basis == "planned"  # the file name is the hint of many forecasts


def test_site_key_ignores_spaces_and_punctuation():
    assert site_key("احداث محوطه شماره 4 3و8 میدان") == site_key("احداث محوطه شماره 4 3 و 8 میدان")
    assert site_key("قطعه2 باند") == site_key("قطعه 2 باند")
    assert site_key("پروژه الف") != site_key("پروژه ب")


def test_a_part_number_range_is_not_a_date_range():
    assert not is_period_title([["گزارش پیش بینی هزینه پروژه اجرای قطعه 6-5 طرح انتقال آب"]])
    assert is_period_title([["گزارش پیش بینی از 18-24 آبان"]])


def test_company_is_read_from_a_title_cell_not_from_a_contractor_in_a_cost_table():
    def sheet(rows):
        return SheetData("درآمد", "visible", lambda: rows)

    from app.features.volume_report.extraction.probe import classify_sheet

    title = sheet([["شرکت گلومک سازه نصر"], ["پیش بینی درآمد"]])
    cost = sheet([["گزارش"], ["x"], ["y"], ["کمپرسی", "شرکت  عمران پویش سیرجان"]])
    workbook = WorkbookData([title])
    assert suggest_company(workbook, [classify_sheet(title)]) == "شرکت گلومک سازه نصر"
    workbook = WorkbookData([cost])
    assert suggest_company(workbook, [classify_sheet(cost)]) is None


# ---- which period is a forecast file for ------------------------------------------------------------------------------------------

REPORT = SimpleNamespace(period_start=date(2026, 11, 9), period_end=date(2026, 11, 15))  # 18-24 Aban 1405


def _file(name, title=None, forecast_for="auto"):
    return SimpleNamespace(filename=name, forecast_for=forecast_for, title_period_start=title[0] if title else None, title_period_end=title[1] if title else None)


THIS, NEXT, OLD = (date(2026, 11, 9), date(2026, 11, 15)), (date(2026, 11, 16), date(2026, 11, 22)), (date(2026, 11, 2), date(2026, 11, 8))


@pytest.mark.parametrize("name, title, scope, source", [
    ("پیش بینی چنگوله 18-24 آبان.xls", OLD, "this", "filename"),            # the title is last week's copy: ignored
    ("معابر پیش بینی 18-24.pdf", None, "this", "filename"),                   # no month in the name: read in this period's month
    ("پیش بینی یازدهم الی هفدهم.pdf", THIS, "this", "title"),                  # a name that says another week is ignored too
    ("پیش بینی هفته بعد.pdf", NEXT, "next", "title"),
    ("forecast.pdf", None, "next", "unknown"),                                   # nothing to go by: the plan of the next period, as before
    ("پیش بینی 18-24.pdf", NEXT, "next", "ambiguous"),
])
def test_forecast_scope_from_title_and_file_name(name, title, scope, source):
    got = service.forecast_scope(REPORT, _file(name, title))
    assert (got["scope"], got["source"]) == (scope, source)


def test_forecast_scope_user_choice_and_files_with_actuals():
    assert service.forecast_scope(REPORT, _file("forecast.pdf", None, "this_period"))["scope"] == "this"
    assert service.forecast_scope(REPORT, _file("پیش بینی 18-24.pdf", THIS, "next_period"))["scope"] == "next"
    assert service.forecast_scope(REPORT, _file("گزارش 18-24.xls", THIS), has_actual=True) == {**service.forecast_scope(REPORT, _file("گزارش 18-24.xls", THIS), has_actual=True), "scope": "next", "source": "mixed"}


# ---- the real files ----------------------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not (WEEK / "سیرجان قطروئیه 18-24 آبان.xlsb").exists(), reason="samples not present")
def test_xlsb_is_read_through_a_converted_copy_and_summary_tables_are_ignored():
    result = extract_file(str(WEEK / "سیرجان قطروئیه 18-24 آبان.xlsb"), Lexicon.from_seed(), None, evm_only=True)
    rows = result.evm_sheets[0].rows
    assert [r.is_total for r in rows] == [False, True]
    assert rows[0].ac == Decimal("111626622166.67") and rows[0].ev == Decimal("169763484997.87")


@pytest.mark.skipif(not (WEEK / "معابر سیرجان 18-24.pdf").exists(), reason="samples not present")
def test_actual_budget_template_pdf_is_an_actual_evm_page():
    path = str(WEEK / "معابر سیرجان 18-24.pdf")
    evm = extract_file(path, Lexicon.from_seed(), None, evm_only=True, file_name="uuid-name.pdf").evm_sheets[0]  # the stored name says nothing
    assert evm.basis == "actual" and evm.rows[0].ev == Decimal("9653175748")


@pytest.mark.skipif(not (WEEK / "پیش بینی هفتگی 18-24 آبان- فراگیر عمران.pdf").exists(), reason="samples not present")
def test_the_file_name_the_user_gave_decides_a_forecast_whose_pages_look_like_an_actual_one():
    path = str(WEEK / "پیش بینی هفتگی 18-24 آبان- فراگیر عمران.pdf")
    assert extract_file(path, Lexicon.from_seed(), None, evm_only=True, file_name="پیش بینی هفتگی 18-24 آبان- فراگیر عمران.pdf").evm_sheets[0].basis == "planned"


@pytest.mark.skipif(not (WEEK / "پیش بینی چنگوله 18-24 آبان.xls").exists(), reason="samples not present")
def test_site_name_of_a_forecast_loses_its_date_suffix():
    path = str(WEEK / "پیش بینی چنگوله 18-24 آبان.xls")
    sheets = extract_file(path, Lexicon.from_seed(), None).sheets
    assert sheets and not any("تاریخ" in s.site_name_norm for s in sheets)


# ---- rows the operator hid are not part of the report -----------------------------------------------------------------------------

def _book_with_hidden_row(tmp_path, suffix=".xlsx"):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "EVM"
    for row in HEADER + [
        [1, "پروژه دیده‌شده", 5 * B, 36, None, None, 100 * B, 77 * B, 51 * B, 1.5, None],
        [2, "پروژه مخفی", 6 * B, 36, None, None, 0, 0, 169 * B, 0.0, None],
    ]:
        ws.append(row)
    ws.row_dimensions[5].hidden = True  # "پروژه مخفی"
    path = tmp_path / f"book{suffix}"
    wb.save(path)
    return str(path)


def test_hidden_rows_of_an_xlsx_are_not_read(tmp_path):
    evm = extract_file(_book_with_hidden_row(tmp_path), Lexicon.from_seed(), None, evm_only=True).evm_sheets[0]
    assert [r.project_name for r in evm.rows] == ["پروژه دیده‌شده"]  # its 169 billion of cost never reaches the company total


@pytest.mark.skipif(not (WEEK / "چنگوله 18-24 آبان.xls").exists(), reason="samples not present")
def test_hidden_rows_of_an_xls_are_not_read():
    result = extract_file(str(WEEK / "چنگوله 18-24 آبان.xls"), Lexicon.from_seed(), None, evm_only=True)
    names = [r.project_name for r in result.evm_sheets[0].rows]
    assert len(names) == 1 and "CG-2" in names[0]  # the sheet lists 5 projects, 4 rows are hidden
