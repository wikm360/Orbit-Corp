import shutil
import subprocess
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.features.volume_report.extraction.income_parser import (
    extract_site_name,
    find_layout,
    guess_site_kind,
    parse_income_sheet,
)
from app.features.volume_report.extraction.normalize import Lexicon, group_key, normalize_text, parse_quantity, role_hint
from app.features.volume_report.extraction.runner import extract_file
from app.features.volume_report.extraction.units import normalize_unit
from tests.features.volume_report.extraction.builders import add_income_sheet, save

LEX = Lexicon.from_seed()


def _parse(rows, **kw):
    wb = Workbook()
    ws = add_income_sheet(wb, "درآمد", rows, **kw)
    data = [list(r) for r in ws.iter_rows(values_only=True)]
    return parse_income_sheet("درآمد", data, LEX, kw.get("period_label"))


# ---- normalization ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("متر مکعب", "m3"), ("3 m", "m3"), ("2 m", "m2"), ("مترمکعب", "m3"), ("m3", "m3"), ("m³", "m3"), ("M3", "m3"),
    ("متر مربع", "m2"), ("m²", "m2"),
    ("مترمربع سانتی متر", "m2cm"), ("متر مربع\nسانتی‌متر", "m2cm"), ("مترمربع-سانتیمتر", "m2cm"),
    ("متر مکعب-کیلومتر", "m3km"),
    ("متر طول", "m"), ("متر", "m"), ("کیلوگرم", "kg"), ("تن", "t"), ("ساعت", "hr"),
    ("مقطوع", "lump"), ("سری", "series"), ("%", "pct"), ("درصد", "pct"), ("شاخه", "ea"), ("چیز عجیب", "other"),
])
def test_unit_normalization(raw, expected):
    assert normalize_unit(raw).unit_norm == expected


def test_empty_unit_is_other_and_flagged():
    info = normalize_unit(None)
    assert (info.unit_norm, info.unit_dim, info.empty) == ("other", "nonphysical", True)


def test_subbase_is_not_also_base():
    assert LEX.tokenize(normalize_text("اجرای زیر اساس")) == ["EXEC", "SUBBASE"]
    assert LEX.tokenize(normalize_text("زیراساس")) == ["SUBBASE"]
    assert LEX.tokenize(normalize_text("تهیه و حمل مصالح اساس")) == ["SUPPLY", "HAUL", "BASE"]


def test_multiword_haul_beats_single():
    assert LEX.tokenize(normalize_text("حمل و بارگیری پله ۶")) == ["HAUL"]


def test_role_hint():
    assert role_hint(["SUPPLY"]) == "supply"
    assert role_hint(["EXEC"]) == "execute"
    assert role_hint(["SUPPLY", "EXEC"]) == "combined"
    assert role_hint(["BASE"]) == "na"


def test_hard_exclusion_reason():
    tokens = LEX.tokenize(normalize_text("اضافه بهای بتن ریزی"))
    assert "SURCHARGE" in tokens and "CONCRETE" in tokens
    assert LEX.hard_exclusion_reason(tokens) == "surcharge"
    assert LEX.hard_exclusion_reason(LEX.tokenize("بتن ریزی")) is None


@pytest.mark.parametrize("raw,expected", [
    (12, "12.0000"), (1949.36, "1949.3600"), ("۲۹٫۴۸", "29.4800"), ("1,234.5", "1234.5000"), ("-72283", "-72283.0000"),
    ("(15)", "-15.0000"), ("abc", None), (None, None), (True, None), ("", None),
])
def test_parse_quantity(raw, expected):
    got = parse_quantity(raw)
    assert (str(got) if got is not None else None) == expected


def test_group_key_depends_on_site_kind():
    assert group_key("a", "m3", "road") != group_key("a", "m3", "mining")
    assert group_key("a", "m3", "road") == group_key("a", "m3", "road")


# ---- layout / parser traps --------------------------------------------------------------------------------------

@pytest.mark.parametrize("header_row,desc_col", [(4, 1), (5, 0), (4, 2)])
def test_header_row_and_activity_column_vary(header_row, desc_col):
    parsed = _parse([(None, "اجرای اساس", "متر مکعب", 563)], header_row=header_row, desc_col=desc_col)
    assert parsed.status == "ok" and parsed.header_row == header_row
    assert [(l.description_raw, l.quantity) for l in parsed.lines] == [("اجرای اساس", Decimal("563"))]


def test_percent_over_volume_header():
    parsed = _parse([(None, "حفاری", "متر", 10)], qty_label="درصد/حجم")
    assert len(parsed.lines) == 1


def test_layout_unknown_when_no_header():
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "چیزی"
    parsed = parse_income_sheet("درآمد", [list(r) for r in ws.iter_rows(values_only=True)], LEX)
    assert parsed.status == "layout_unknown" and find_layout([[None]]) is None


def test_blank_row_inside_table_is_skipped_not_a_stop():
    rows = [(None, "بارگیری پله ۵", "متر مکعب", 29560), (None, None, None, None), (None, "بارگیری پله ۶", "متر مکعب", 22693)]
    assert [l.quantity for l in _parse(rows).lines] == [Decimal("29560"), Decimal("22693")]


def test_rows_after_total_are_not_read():
    rows = [(None, "اجرای اساس", "متر مکعب", 5), ("جمع صورت وضعیت",), (None, "یادداشت", "متر مکعب", 999)]
    assert [l.description_raw for l in _parse(rows).lines] == ["اجرای اساس"]


def test_zero_and_non_numeric_counted_but_not_stored():
    parsed = _parse([(None, "الف", "متر", 0), (None, "ب", "متر", "توضیح"), (None, "ج", "متر", 3)])
    assert (parsed.rows_total, parsed.rows_nonzero, len(parsed.lines)) == (3, 1, 1)


def test_negative_quantity_kept_with_flag():
    line = _parse([(None, "کسورات", "متر مکعب", -72283)]).lines[0]
    assert line.quantity == Decimal("-72283") and line.flags["negative_qty"]


def test_nonphysical_units_stored_with_flag():
    parsed = _parse([(None, "اجاره ماشین آلات", "مقطوع", 1), (None, "گریدر", "ساعت", 40), (None, "اجرای اساس", "متر مکعب", 7)])
    flags = {l.description_raw: l.flags.get("nonphysical_unit", False) for l in parsed.lines}
    assert flags == {"اجاره ماشین آلات": True, "گریدر": False, "اجرای اساس": False}
    assert parsed.rows_nonphysical == 1  # hours are a physical (time) dimension, lump is not
    assert next(l for l in parsed.lines if l.unit_norm == "hr").unit_dim == "time"


def test_surcharge_word_flag_even_with_concrete():
    line = _parse([(None, "اضافه بهای بتن ریزی", "متر مکعب", 5.88)]).lines[0]
    assert line.flags["has_surcharge_word"] and "CONCRETE" in line.tokens


def test_section_heading_carried_forward():
    rows = [("عملیات آسفالت", "بیندر", "تن", 693), (None, "توپکا", "تن", 10), ("عملیات خاکی", "خاکبرداری", "متر مکعب", 4)]
    parsed = _parse(rows, section_col=0, desc_col=1)
    assert [l.section_heading for l in parsed.lines] == ["عملیات آسفالت", "عملیات آسفالت", "عملیات خاکی"]


def test_twin_rows_hint():
    rows = [(None, "بتن‌ریزی شمع", "متر مکعب", 29.48), (None, "حمل مصالح بتن‌ریزی شمع", "متر مکعب", 29.48),
            (None, "بتن پی", "متر مکعب", 25)]
    lines = _parse(rows).lines
    assert lines[0].flags["twin_rows"] == [lines[1].row_no] and lines[1].flags["twin_rows"] == [lines[0].row_no]
    assert "twin_rows" not in lines[2].flags


def test_unit_missing_warning():
    parsed = _parse([(None, "اجرای اساس", None, 5)])
    assert parsed.lines[0].unit_norm == "other" and parsed.warnings[0]["code"] == "unit_missing"


def test_period_label_mismatch_is_a_warning_only():
    parsed = _parse([(None, "اجرای اساس", "متر مکعب", 5)], title="گزارش درآمد پروژه الف در ماه اردیبهشت 1405")
    wb = Workbook()
    ws = add_income_sheet(wb, "درآمد", [(None, "اجرای اساس", "متر مکعب", 5)], title="گزارش درآمد پروژه الف در ماه اردیبهشت 1405")
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    p = parse_income_sheet("درآمد", rows, LEX, "شهریور 1405")
    assert [w["code"] for w in p.warnings] == ["period_label_mismatch"] and len(p.lines) == 1
    assert not parse_income_sheet("درآمد", rows, LEX, "اردیبهشت 1405").warnings
    assert parsed.status == "ok"


# ---- site name / kind -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("title,expected", [
    ("گزارش درآمد پروژه احداث باند دوم محور زرند سیریز در ماه شهریور 1405", "احداث باند دوم محور زرند سیریز"),
    ('درآمد پروژه "راهسازی باند دوم محور زرند-بافق" در ماه شهریور 1405', "راهسازی باند دوم محور زرند-بافق"),
    ("گزارش درامد شهریور ماه پروژه بهسازی و روکش «معبر الف»", "بهسازی و روکش معبر الف"),
])
def test_site_name_extraction(title, expected):
    assert extract_site_name([[None], [title]], "x") == expected


def test_site_name_falls_back_to_sheet_name():
    assert extract_site_name([[None]], "درآمد معدن فراگیر") == "معدن فراگیر"


def test_site_kind_guess():
    assert guess_site_kind(normalize_text("معدن فراگیر")) == "mining"
    assert guess_site_kind(normalize_text("باطله برداری گل گهر")) == "mining"
    assert guess_site_kind(normalize_text("باند دوم محور زرند")) == "road"


# ---- whole-workbook probing -------------------------------------------------------------------------------------

def test_probe_skips_hidden_planned_expense_other_and_logs_reasons(tmp_path):
    wb = Workbook()
    add_income_sheet(wb, "درآمد پروژه یک", [(None, "اجرای اساس", "متر مکعب", 563)])
    add_income_sheet(wb, "درآمد پنهان", [(None, "اجرای اساس", "متر مکعب", 1)], state="hidden")
    add_income_sheet(wb, "درآمد برنامه ای", [(None, "اجرای اساس", "متر مکعب", 2)])
    add_income_sheet(wb, "هزینه", [(None, "اجرای اساس", "متر مکعب", 3)])
    summary = wb.create_sheet("EVM M")
    summary["B2"] = "شرکت محورگستر توسعه"
    wb.create_sheet("Chart")
    wb.create_sheet("پیش بینی")  # EVM-style summary named like a forecast but not an income table: skipped
    result = extract_file(save(wb, tmp_path), LEX)
    log = {e["sheet"]: e for e in result.sheet_log}
    # the income-layout plan sheet is read, as the forecast of the next period
    assert [(s.sheet_name, s.basis) for s in result.sheets] == [("درآمد پروژه یک", "actual"), ("درآمد برنامه ای", "planned")]
    assert log["درآمد برنامه ای"]["kind"] == "planned" and log["درآمد برنامه ای"]["used"] and log["درآمد برنامه ای"]["basis"] == "planned"
    assert log["پیش بینی"]["reason"] == "planned_sheet" and not log["پیش بینی"]["used"]
    assert log["درآمد پنهان"]["reason"] == "hidden" and log["درآمد پنهان"]["kind"] == "hidden" and not log["درآمد پنهان"]["used"]
    assert log["هزینه"]["kind"] == "expense" and log["Chart"]["kind"] == "other"
    assert log["درآمد پروژه یک"]["used"] and log["درآمد پروژه یک"]["rows_nonzero"] == 1
    assert result.suggested_company.startswith("شرکت محورگستر")


def test_unreadable_extension_rejected(tmp_path):
    from app.core.exceptions import BadRequestError

    path = tmp_path / "a.csv"
    path.write_text("x")
    with pytest.raises(BadRequestError):
        extract_file(str(path), LEX)


# ---- reference scenario (mining file, doc 13.3) -----------------------------------------------------------------

def test_mining_reference_rows():
    rows = [
        (None, "حمل و بارگیری پله ۱", "متر مکعب", 29560),
        (None, "حمل و بارگیری پله ۲", "متر مکعب", 22693),
        (None, None, None, None),
        (None, "حمل و بارگیری پله ۶", "متر مکعب", 47584),
        (None, "حمل و بارگیری ابرفت", "متر مکعب", 37754),
        (None, "گریدر", "ساعت", 120),
        (None, "کسورات", "متر مکعب", -72283),
        ("جمع صورت وضعیت",),
        (None, "یادداشت", "متر مکعب", 5),
    ]
    parsed = _parse(rows, title="گزارش درآمد پروژه معدن آزمایشی در ماه شهریور 1405")
    assert parsed.site_kind_guess == "mining"
    haul = sum(l.quantity for l in parsed.lines if "HAUL" in l.tokens and l.unit_norm == "m3" and l.quantity > 0)
    assert haul == Decimal("137591")


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice needed to produce a real .xls")
def test_legacy_xls_is_read_with_xlrd(tmp_path):
    wb = Workbook()
    add_income_sheet(wb, "درآمد پروژه یک", [(None, "اجرای اساس", "متر مکعب", 563)])
    add_income_sheet(wb, "درآمد پنهان", [(None, "اجرای اساس", "متر مکعب", 1)], state="hidden")
    src = save(wb, tmp_path, "src.xlsx")
    out = tmp_path / "out"
    subprocess.run(["soffice", f"-env:UserInstallation=file://{tmp_path / 'profile'}", "--headless", "--convert-to", "xls",
                    "--outdir", str(out), src], check=True, capture_output=True, timeout=120)
    result = extract_file(str(out / "src.xls"), LEX)
    assert [(l.description_raw, l.quantity) for s in result.sheets for l in s.lines] == [("اجرای اساس", Decimal("563"))]
    assert {e["sheet"]: e["reason"] for e in result.sheet_log}["درآمد پنهان"] == "hidden"
