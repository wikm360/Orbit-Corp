from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.features.volume_report.extraction.evm_parser import parse_evm_sheet
from app.features.volume_report.extraction.normalize import Lexicon
from app.features.volume_report.extraction.runner import extract_file

SAMPLES = Path("eval/volume_report/second-aban")
HEADER = [
    ["شرکت نمونه"],
    ["گزارش مدیریت ارزش کسب شده (EVM) پروژه های در دست اجرا"],
    ["ردیف", "نام پروژه", "مبلغ قرارداد (ریال)", "مدت پیمان", "M-BCWS", "PV", "EV", "ev", "AC", "CPI=ev/AC", "SPI=EV/PV", "توضیحات"],
]


def _sheet(rows, title=None):
    data = [list(r) for r in HEADER]
    if title:
        data[1] = [title]
    return data + rows


def test_excel_numeric_cells_full_row_and_total():
    rows = _sheet([
        [1, "پروژه الف", 6_130_000_000_000, 24, 70_000_000_000, 70_000_000_000, 46_359_942_383, 35_661_494_141, 34_000_123_354, 1.05, 0.66, None],
        [2, "پروژه ب", 200_000_000_000, 12, 14_000_000_000, 14_000_000_000, 0, 0, 420_000_000, 0.0, 0.0, None],
        ["جمع", None, None, None, 84_000_000_000, 84_000_000_000, 46_359_942_383, 35_661_494_141, 34_420_123_354, 1.04, 0.55, None],
    ])
    parsed = parse_evm_sheet("EVM", rows)
    assert parsed is not None and parsed.basis == "actual"
    a, b, total = parsed.rows
    assert (a.project_name, a.contract_amount, a.pv, a.ev, a.ev_net, a.ac) == (
        "پروژه الف", Decimal(6_130_000_000_000), Decimal(70_000_000_000), Decimal(46_359_942_383), Decimal(35_661_494_141), Decimal(34_000_123_354))
    assert (a.cpi, a.spi) == (Decimal("1.05"), Decimal("0.66"))
    assert b.ev == 0 and b.cpi == Decimal("0.00") and b.spi == Decimal("0.00")  # a real zero, both operands exist
    assert total.is_total and total.ac == Decimal(34_420_123_354) and total.spi == Decimal("0.55")


def test_missing_programme_gives_null_spi_and_planned_basis_from_title():
    rows = _sheet([[1, "پروژه", 4_831_009_049_701, 24, 266_028_243_112, 204_841_747_196, 161_295_922_668, 1.27, 0.0, None]],
                  title="پیش بینی گزارش مدیریت ارزش کسب شده (EVM)")
    parsed = parse_evm_sheet("EVM", rows)
    row = parsed.rows[0]
    assert parsed.basis == "planned"
    assert row.pv is None and row.bcws is None and row.spi is None  # SPI is meaningless without PV
    assert (row.ev, row.ev_net, row.ac, row.cpi) == (Decimal(266_028_243_112), Decimal(204_841_747_196), Decimal(161_295_922_668), Decimal("1.27"))


def test_not_an_evm_sheet():
    assert parse_evm_sheet("درآمد", [["شرح", "حجم", "واحد"], ["خاکبرداری", 10, "مترمکعب"]]) is None


def test_extract_file_reports_evm_without_touching_income(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "برنامه EVM"  # a "plan" sheet name: must still be read as EVM, not skipped as planned_sheet
    for row in _sheet([[1, "پروژه الف", 1_000_000_000, 12, 5_000_000_000, 5_000_000_000, 4_000_000_000, 3_000_000_000, 2_000_000_000, 1.5, 0.8, None]]):
        ws.append(row)
    path = tmp_path / "evm.xlsx"
    wb.save(path)
    result = extract_file(str(path), Lexicon([]))
    assert [len(e.rows) for e in result.evm_sheets] == [1]
    assert result.sheets == [] and result.sheet_log[0]["kind"] == "evm" and result.sheet_log[0]["used"] is True


def _evm_of(name):
    from app.features.volume_report.extraction.workbook import open_workbook

    with open_workbook(str(SAMPLES / name)) as wb:
        for sheet in wb.sheets:
            parsed = parse_evm_sheet(sheet.name, sheet.rows(), name)
            if parsed:
                return parsed
    return None


@pytest.mark.skipif(not SAMPLES.exists(), reason="eval samples not present")
def test_real_pdf_multi_project_company_with_total():
    parsed = _evm_of("EVm گلومک سازه از 11 تا 17 آبان.pdf")
    projects = [r for r in parsed.rows if not r.is_total]
    total = parsed.rows[-1]
    assert parsed.basis == "actual" and len(projects) == 7 and total.is_total
    first = projects[0]
    assert (first.pv, first.ev, first.ev_net, first.ac) == (Decimal(70_000_000_000), Decimal(46_359_942_383), Decimal(35_661_494_141), Decimal(34_000_123_354))
    assert (first.cpi, first.spi) == (Decimal("1.05"), Decimal("0.66"))
    assert (total.pv, total.ev, total.ac, total.cpi, total.spi) == (Decimal(179_316_666_667), Decimal(77_202_426_059), Decimal(58_641_190_021), Decimal("1.01"), Decimal("0.43"))
    assert next(r for r in projects if r.ac == Decimal(5_525_900_000)).cpi == Decimal("0.49")
    assert projects[5].ev is None and projects[5].cpi is None  # no data yet: not a fake zero


@pytest.mark.skipif(not SAMPLES.exists(), reason="eval samples not present")
def test_real_pdf_forecast_and_single_project_files():
    plan = _evm_of("گزارش 18تا24 آبان پیش بینی.pdf")
    assert plan.basis == "planned" and plan.rows[-1].spi == Decimal("1.00") and plan.rows[0].ev == Decimal(77_700_000_000)
    single = _evm_of("گزارش یازدهم الی هفدهم آبان ماه 1405 پروژه راور-دیهوک.pdf")
    row = single.rows[0]
    assert single.basis == "actual" and (row.ev, row.ev_net, row.ac, row.cpi, row.pv, row.spi) == (
        Decimal(83_039_367_218), Decimal(63_940_312_758), Decimal(60_492_542_028), Decimal("1.06"), None, None)
    assert _evm_of("گزارش پیش بینی هفتگی از 18 الی 24 آبان ماه پروژه میدان نفتی سهراب.pdf").basis == "planned"
