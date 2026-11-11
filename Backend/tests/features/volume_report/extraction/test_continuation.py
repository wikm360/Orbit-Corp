from decimal import Decimal
from pathlib import Path

import pytest

from app.features.volume_report.extraction.continuation import continuation_grid
from app.features.volume_report.extraction.evm_parser import parse_evm_sheet
from app.features.volume_report.extraction.income_parser import find_layout, parse_income_sheet
from app.features.volume_report.extraction.normalize import Lexicon
from app.features.volume_report.extraction.runner import extract_file

SAMPLES = Path("eval/volume_report/second-aban")

PAGE = [
    ["3"],
    ["خاکبرداری از قرضه جهت مصرف در خاکریزی"],
    ["035101 4,000 مترمکعب 412,500 ریال 1,650,000,000 ریال 1.3 1.28 1.57 4,304,277,120 ریال"],
    ["معمولی"],
    ["تسطیح و آب پاشی و کوبیدن بستر خاکریزها با"],
    ["035201 0 مترمربع 9,710 ریال - ریال 1.3 1.28 1.57 - ریال"],
    ["تراکم کمتر از 95 درصد"],
    ["110502 0 کیلوگرم 422,500 ریال - ریال 1.3 1.28 1.37 - ریال"],
    ["200508 حمل آب برای عملیات خاکریزی 4320 مترمکعب / کیلومتر 39,600 ریال 171,072,000 ریال 1.3"],
    ["جمع صورت وضعیت بدون اعمال ضرایب ( ریال ) 11,973,038,000"],
    ["900101 5 عدد 1,000 ریال"],  # after the totals: never read
]


def test_continuation_page_becomes_a_standard_grid():
    grid = continuation_grid(PAGE)
    assert grid[0] == ["شرح", "فعالیت", "حجم", "واحد"] and len(grid) == 5
    assert grid[1][1:] == ["خاکبرداری از قرضه جهت مصرف در خاکریزی معمولی", "4000", "مترمکعب"]
    assert grid[4][1:] == ["حمل آب برای عملیات خاکریزی", "4320", "مترمکعب / کیلومتر"]
    parsed = parse_income_sheet("صفحه (صفحه 7)", grid, Lexicon([]))
    assert parsed.status == "ok" and parsed.rows_total == 4 and parsed.rows_nonzero == 2
    assert [(l.quantity, l.unit_norm) for l in parsed.lines] == [(Decimal(4000), "m3"), (Decimal(4320), "m3km")]


def test_not_a_continuation_page():
    assert continuation_grid([["نام دستگاه", "کد", "70"], ["کمپرسی 742 70 70 ساعت 16,000,000"]]) is None


def test_split_activity_header_is_still_found():
    header = ["مبلغ", "x", "x", "x", "x", "x", "x", "x", "x", "x", "x", "x", "واحد", "تعداد دستگاه", "ت", "فعالی", "شرح"]
    assert find_layout([header])[1]["desc"] == 15


def test_budget_template_reads_ev_ev_ac_and_cpi_only():
    rows = [["گزارش هزینه 1405/08/09 الی 1405/08/16 پروژه معابر سیرجان"],
            ["Y - BC WS M - BC WS PV EV ev AC AC EV = C PI AC / ev = C PI PV EV = S PI"],
            ["1,183,719 225,184 10 4,025,574,774 3,096,595,980 4,402,000,000 0.91 0.70 402557477.37"]]
    parsed = parse_evm_sheet("برنامه", rows, "x.pdf")
    row = parsed.rows[0]
    assert row.project_name == "معابر سیرجان" and (row.ev, row.ev_net, row.ac, row.cpi) == (
        Decimal(4_025_574_774), Decimal(3_096_595_980), Decimal(4_402_000_000), Decimal("0.70"))
    assert row.pv is None and row.spi is None


@pytest.mark.skipif(not (SAMPLES / "سیستان.pdf").exists(), reason="sample not present")
def test_real_pdf_continuation_pages_are_read_and_marked():
    result = extract_file(str(SAMPLES / "سیستان.pdf"), Lexicon([]))
    cont = [e for e in result.sheet_log if e.get("continuation")]
    assert len(cont) == 4 and all(e["kind"] == "income" and e["used"] for e in cont)
    khash = [s for s in result.sheets if "خاش" in s.site_name]
    quantities = sorted(l.quantity for s in khash for l in s.lines)
    assert Decimal(4000) in quantities and Decimal(59250) in quantities and Decimal(12000) in quantities
    assert len({s.site_name for s in result.sheets}) == 2  # the pages carry on the same two projects


@pytest.mark.skipif(not (SAMPLES / "Sirjan Daily EVM ABAN.pdf").exists(), reason="sample not present")
def test_unreadable_font_is_reported_not_silently_empty():
    result = extract_file(str(SAMPLES / "Sirjan Daily EVM ABAN.pdf"), Lexicon([]))
    assert {w["code"] for w in result.warnings} == {"unreadable_pdf_font"}
    assert all(e["reason"] == "unreadable_font" for e in result.sheet_log)


@pytest.mark.skipif(not (SAMPLES / "سیستان پیش بینی.xlsx").exists(), reason="sample not present")
def test_forecast_file_with_plain_income_sheet_names_is_planned():
    result = extract_file(str(SAMPLES / "سیستان پیش بینی.xlsx"), Lexicon([]))
    assert result.sheets and all(s.basis == "planned" for s in result.sheets)  # never leaks into the actual totals
