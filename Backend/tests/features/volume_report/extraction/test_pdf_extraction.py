from pathlib import Path
from decimal import Decimal

import pytest

from app.features.volume_report.extraction.normalize import Lexicon
from app.features.volume_report.extraction.runner import extract_file
from app.features.volume_report.extraction.workbook import open_workbook
from app.features.volume_report.extraction.probe import probe_workbook


PDF_SAMPLE = Path("eval/هفتگی معابر سیرجان یکم تا دهم.pdf")


@pytest.mark.skipif(not PDF_SAMPLE.exists(), reason="Sample PDF not present in eval/")
def test_pdf_open_workbook_and_probe():
    with open_workbook(str(PDF_SAMPLE)) as wb:
        assert len(wb.sheets) == 3
        probes = probe_workbook(wb)
        assert len(probes) == 3
        # Page 1: income sheet
        assert probes[0].kind == "income"
        assert probes[0].used is True
        # Page 2: expense sheet
        assert probes[1].kind == "expense"
        assert probes[1].used is False
        assert probes[1].reason == "expense_sheet"
        # Page 3: planned / EVM sheet
        assert probes[2].kind == "planned"
        assert probes[2].used is False
        assert probes[2].reason == "planned_sheet"


@pytest.mark.skipif(not PDF_SAMPLE.exists(), reason="Sample PDF not present in eval/")
def test_pdf_extract_file():
    lex = Lexicon.from_seed()
    result = extract_file(str(PDF_SAMPLE), lex)

    assert len(result.sheet_log) == 3
    assert len(result.sheets) == 1

    sheet = result.sheets[0]
    assert sheet.status == "ok"
    assert sheet.site_name == "معابر سیرجان"
    assert len(sheet.lines) == 6

    # Verify extracted items and quantities
    quantities_by_desc = {line.description_raw: (line.unit_norm, line.quantity) for line in sheet.lines}

    assert "تخریب جداول و بتن ماهیچه" in quantities_by_desc
    assert quantities_by_desc["تخریب جداول و بتن ماهیچه"] == ("m", Decimal("120.0000"))

    assert "تخریب بتن غیر مسلح" in quantities_by_desc
    assert quantities_by_desc["تخریب بتن غیر مسلح"] == ("m3", Decimal("22.0000"))

    assert "کانال کنی ، خاکبرداری و حمل" in quantities_by_desc
    assert quantities_by_desc["کانال کنی ، خاکبرداری و حمل"] == ("m3", Decimal("67.0000"))

    assert "بارگیری و حمل مصالح تخریب شده" in quantities_by_desc
    assert quantities_by_desc["بارگیری و حمل مصالح تخریب شده"] == ("m3", Decimal("67.0000"))

    assert "پریمکت" in quantities_by_desc
    assert quantities_by_desc["پریمکت"] == ("kg", Decimal("4514.0000"))

    assert "آسفالت" in quantities_by_desc
    assert quantities_by_desc["آسفالت"] == ("t", Decimal("1783.0000"))



def test_wrapped_description_lines_are_glued_to_their_code_row():
    from app.features.volume_report.extraction.pdf_extractor import _attach_wrapped_descriptions

    headers = ["ردیف فصل", "موضوع", "ضریب شکست", "حجم", "واحد", "قیمت واحد"]
    body = [
        ["20 35101", None, "خاکبرداری از قرضه", "5684", "مترمکعب", "100 ریال"],       # y=100: description on the same line
        [None, "تسطیح و کوبیدن بستر", "با تراکم 95 تا 100", None, None, None],        # y=94: head of the next row
        ["22 35202", None, None, "1,000", "مترمربع", "50 ریال"],                      # y=88: no text of its own
        [None, "سانتی متر .", None, None, None, None],                                 # y=82: tail
        ["81 140801 اضافه بها", "عمق 2", "متر", "متر 0", "مترمکعب", None],            # y=76: code cell + qty cell carry words
        ["جمع کل", None, None, None, None, None],
    ]
    out = _attach_wrapped_descriptions(body, [100.0, 94.0, 88.0, 82.0, 76.0, 70.0], headers)
    assert [r[1] for r in out[:3]] == ["خاکبرداری از قرضه", "تسطیح و کوبیدن بستر با تراکم 95 تا 100 سانتی متر .", "اضافه بها عمق 2 متر متر"]
    assert [r[3] for r in out[:3]] == ["5684", "1,000", "0"]
    assert out[2][0] == "81 140801" and out[2][2] is None
    assert out[3][0] == "جمع کل"  # rows from the totals row on are untouched
    assert len(out) == 4


def test_wide_sheet_header_labels_are_not_merged():
    """Sheets shrunk to fit one page have a tiny font; a fixed 18pt distance used to merge "ضریب شکست" and "حجم"."""
    sample = Path("eval/سیستان و بلوچستان.pdf")
    if not sample.exists():
        pytest.skip("Sample PDF not present in eval/")
    with open_workbook(str(sample)) as wb:
        sheet = next(s for s in wb.sheets if "میرجاوه" in s.name and s.name.startswith("درآمد"))
        header = sheet.rows()[2]
        assert "حجم" in header and "واحد" in header
        lexicon = Lexicon([])
        from app.features.volume_report.extraction.income_parser import parse_income_sheet
        parsed = parse_income_sheet(sheet.name, sheet.rows(), lexicon)
        assert parsed.status == "ok" and len(parsed.lines) == 6


def test_site_name_drops_report_date_and_month():
    from app.features.volume_report.extraction.income_parser import strip_period_from_name

    assert strip_period_from_name("احداث باند دوم زاهدان خاش 1405/08/11") == "احداث باند دوم زاهدان خاش"
    assert strip_period_from_name("احداث باند دوم زاهدان میرجاوه قطعه 2 آبان ماه 1405 تاریخ : 1405/08/11") == "احداث باند دوم زاهدان میرجاوه قطعه 2"
    assert strip_period_from_name("بهسازی محور کرمان-دیهوک از 1405/08/01 الی 1405/08/10") == "بهسازی محور کرمان-دیهوک"
    assert strip_period_from_name("راه 2") == "راه 2"


# ---- weekly report with a forecast page (presentation-form glyphs, flipped page) -------------------------------------

_CHANGULEH = Path(__file__).resolve().parents[4] / "eval" / "10-17 آبان چنگوله.pdf"


@pytest.mark.skipif(not _CHANGULEH.exists(), reason="eval PDF not available")
def test_weekly_pdf_reads_actual_page_and_forecast_page_separately():
    result = extract_file(str(_CHANGULEH), Lexicon.from_seed())
    assert [(s.basis, s.status) for s in result.sheets] == [("actual", "ok"), ("planned", "ok")]
    assert result.sheets[0].site_name == result.sheets[1].site_name and "چنگوله" in result.sheets[0].site_name

    def qty(sheet):
        return {line.description_raw: (line.quantity, line.unit_norm) for line in sheet.lines}

    assert qty(result.sheets[0]) == {
        "عملیات خاکبرداری": (Decimal("4100"), "m3"), "عملیات خاکریزی": (Decimal("799"), "m3"), "عملیات ساب بیس": (Decimal("350"), "m3"),
        "قالب بندی": (Decimal("205"), "m2"), "بتن ریزی": (Decimal("137"), "m3"),
    }
    assert qty(result.sheets[1])["عملیات خاکبرداری"] == (Decimal("3500"), "m3") and qty(result.sheets[1])["بتن ریزی"] == (Decimal("150"), "m3")
