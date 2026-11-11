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

    if not (SAMPLES / name).exists():
        pytest.skip(f"sample {name} not present")

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
    plan = _evm_of("سیستان پیش بینی.xlsx")
    assert plan.basis == "planned" and plan.rows[-1].spi == Decimal("1.00") and plan.rows[0].ev == Decimal(77_700_000_000)
    single = _evm_of("گزارش یازدهم الی هفدهم آبان ماه 1405 پروژه راور-دیهوک.pdf")
    row = single.rows[0]
    assert single.basis == "actual" and (row.ev, row.ev_net, row.ac, row.cpi, row.pv, row.spi) == (
        Decimal(83_039_367_218), Decimal(63_940_312_758), Decimal(60_492_542_028), Decimal("1.06"), None, None)
    assert _evm_of("گزارش پیش بینی هفتگی از 18 الی 24 آبان ماه پروژه میدان نفتی سهراب.pdf").basis == "planned"


def test_income_totals_chain_from_flattened_rows():
    from app.features.volume_report.extraction.income_totals import detect_basis, parse_income_totals

    rows = [
        ["درآمد از هفته دوم آبان"],
        ["جمع صورت وضعیت بدون اعمال ضرایب )ریال( 6 ، 935 ، 892 ، 440", "( جمع تعدیل )ریال 31 ، 137 ، 259 ، 574"],
        ["جمع صورت وضعیت با اعمال ضرایب )ریال( 17 ، 662 ، 679 ، 776", "( جمع کل درآمد )ریال 48 ، 799 ، 939 ، 351"],
        ["مابه التفاوت مصالح )ریال( 0 ( جمع صورت وضعیت تجمعی با اعمال ضرایب )ریال 1,819,912,090,783", "( جمع کل درآمد با کسر سهم جهاد نصر )ریال 46 ، 359 ، 942 ، 383"],
        ["مقایسه درآمد و هزینه"],
        ["35,661,494,14134,000,123,354", "1,661,370,787"],
    ]
    totals = parse_income_totals(rows)
    assert (totals.statement_base, totals.statement_coef, totals.adjustment, totals.income_total, totals.cumulative) == (
        Decimal(6_935_892_440), Decimal(17_662_679_776), Decimal(31_137_259_574), Decimal(48_799_939_351), Decimal(1_819_912_090_783))
    assert parse_income_totals([["شرح", "حجم"]]) is None
    assert detect_basis("برنامه درآمد پروژه", rows, None) == "planned" and detect_basis("درآمد پروژه", rows, "x.xlsx") == "actual"
    assert detect_basis("درآمد", rows, "سیستان پیش بینی.xlsx") == "planned"


@pytest.mark.skipif(not SAMPLES.exists(), reason="eval samples not present")
def test_real_excel_with_extra_average_column_and_income_totals():
    parsed = _evm_of("سیستان پیش بینی.xlsx")
    first = parsed.rows[0]
    assert parsed.basis == "planned" and first.project_name == "باند دوم محور زاهدان - میرجاوه قطعه2"
    assert (first.contract_amount, first.pv, first.ev_net, first.ac, first.cpi, first.spi) == (
        Decimal(7_120_698_396_196), Decimal(77_700_000_000), Decimal(59_769_230_769), Decimal(39_621_903_492), Decimal("1.51"), Decimal("1"))
    from app.features.volume_report.extraction.income_totals import parse_income_totals
    from app.features.volume_report.extraction.workbook import open_workbook

    with open_workbook(str(SAMPLES / "سیستان پیش بینی.xlsx")) as wb:
        totals = parse_income_totals(next(s for s in wb.sheets if "میرجاوه" in s.name and "درآمد" in s.name).rows())
    assert totals.income_total == Decimal(77_700_000_000) and totals.adjustment == Decimal(28_934_824_632)


def test_income_totals_reads_visual_order_arabic_digits():
    from app.features.volume_report.extraction.income_totals import parse_income_totals

    rows = [["جمع صورت وضعیت بدون اعمال ضرایب ) ریال (", "٣٣٤،٠٧٠،٠٦٩،٤٢", "جمع تعدیل ) ریال (", "٠٠٨،١٤٢،٥٢٠،١٢"],
            ["جمع کل درآمد ) ریال (", "٣٣٢،٢١٣،٥٨٩،٥٤"]]
    totals = parse_income_totals(rows)
    assert (totals.statement_base, totals.adjustment, totals.income_total) == (Decimal(24_960_070_433), Decimal(21_025_241_800), Decimal(45_985_312_233))
    assert totals.statement_base + totals.adjustment == totals.income_total


def test_income_totals_value_before_label_and_split_letters():
    from app.features.volume_report.extraction.income_totals import parse_income_totals

    before = [["31،137،259،574", "جمع تعدیل (ریال)", "6،935،892،440", "جمع صورت وضعیت بدون اعمال ضرایب (ریال)"],
              ["48،799،939،351", "جمع کل درآمد (ریال)", "17،662،679،776", "جمع صورت وضعیت با اعمال ضرایب (ریال)"],
              ["46،359،942،383", "جمع کل درآمد با کسر سهم جهاد نصر (ریال)", "0", "مابه التفاوت مصالح (ریال)"],
              ["1,819,912,090,783", "جمع صورت وضعیت تجمعی با اعمال ضرایب (ریال)"]]
    totals = parse_income_totals(before)
    assert (totals.statement_base, totals.statement_coef, totals.adjustment, totals.income_total, totals.cumulative) == (
        Decimal(6_935_892_440), Decimal(17_662_679_776), Decimal(31_137_259_574), Decimal(48_799_939_351), Decimal(1_819_912_090_783))
    split = [["0", "جمع تعدی ل )ریال(", "6,183,333,333", "ب )ریا ل("], ["6,183,333,333", "جمع ک ل درآمد )ریال(", "6,183,333,333"]]
    letters = parse_income_totals(split)
    assert letters.adjustment == 0 and letters.income_total == Decimal(6_183_333_333) and letters.statement_base is None
