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


def test_to_logical_rtl_preserves_mixed_ltr_codes_and_brackets():
    from app.features.volume_report.extraction.pdf_extractor import _to_logical_rtl

    assert _to_logical_rtl("(لﺎﯾر)") == "(ریال)"
    assert _to_logical_rtl("ﺮﺘﻣ 10 ﺎﺗ C16 5 ﻦﺘﺑ") == "بتن C16 5 تا 10 متر"
    assert _to_logical_rtl("ﯽﻠﺻا ﯽﺳﺮﺘﺳد هدﺎﺟ- 1 عﻮﻧ ﻦﯿﻣز") == "زمین نوع 1 -جاده دسترسی اصلی"


def test_wrapped_units_and_equipment_count_header_parse():
    from app.features.volume_report.extraction.income_parser import parse_income_sheet
    from app.features.volume_report.extraction.pdf_extractor import _attach_wrapped_units

    body = [
        [None, "مترمکعب-", None, None],
        ["حمل خاک به دپو", None, "4,092", None],
        [None, "کیلومتر", None, None],
    ]
    ys = [227.5, 222.7, 218.4]
    rows_out, ys_out = _attach_wrapped_units(body, ys, qty_idx=2, unit_idx=1, desc_idx=0)
    assert len(rows_out) == 1 and len(ys_out) == 1
    assert rows_out[0] == ["حمل خاک به دپو", "مترمکعب- کیلومتر", "4,092", None]

    rental_rows = [
        ["شرکت نمونه"],
        ["اجاره دستگاه در معدن 1"],
        ["فعالیت", "تعداد دستگاه", "واحد"],
        ["اجاره دستگاه بیل", "3", "عدد"],
    ]
    parsed = parse_income_sheet("درآمد اجاره دستگاه", rental_rows, Lexicon([]))
    assert parsed.status == "ok"
    assert len(parsed.lines) == 1
    assert parsed.lines[0].quantity == Decimal("3")
    assert parsed.lines[0].unit_norm == "ea" and parsed.lines[0].unit_dim == "nonphysical"


_GOLOMAK_SECOND_ABAN = (
    Path(__file__).resolve().parents[4] / "eval" / "volume_report" / "second-aban" / "EVm گلومک سازه از 11 تا 17 آبان.pdf"
)


@pytest.mark.skipif(not _GOLOMAK_SECOND_ABAN.exists(), reason="eval PDF not available")
def test_foxit_golomak_pdf_extracts_evm_and_all_income_pages():
    result = extract_file(str(_GOLOMAK_SECOND_ABAN), Lexicon.from_seed())
    assert result.warnings == []
    assert [s for s in result.sheet_log if s.get("layout_unknown")] == []
    assert len(result.evm_sheets) == 1 and len(result.evm_sheets[0].rows) == 8
    assert len(result.sheets) == 6

    by_page = {s.sheet_name: s for s in result.sheets}
    p2 = by_page["درآمد احداث قطعه (صفحه 2)"]
    assert p2.status == "ok" and len(p2.lines) == 18
    assert [(ln.quantity, ln.unit_norm) for ln in p2.lines[-3:]] == [
        (Decimal("108"), "m3km"),
        (Decimal("4092"), "m3km"),
        (Decimal("432"), "m3km"),
    ]
    assert by_page["درآمد بارگیری دستگاه بیل HEC (صفحه 4)"].lines[0].quantity == Decimal("42000")
    assert by_page["درآمد بارگیری و حمل کلوخه سنگ آهن معدن سنگان (صفحه 6)"].status == "ok"
    assert by_page["درآمد بارگیری و حمل کلوخه سنگ آهن معدن سنگان (صفحه 6)"].lines == []
    assert by_page["درآمد عملیات اجرایی احداث سد مخزنی آخران (صفحه 8)"].lines[0].quantity == Decimal("1000")
    p10 = by_page["درآمد اجاره دستگاه  معدن (صفحه 10)"]
    assert [(ln.quantity, ln.unit_norm) for ln in p10.lines] == [
        (Decimal("3"), "ea"),
        (Decimal("1"), "ea"),
        (Decimal("2"), "ea"),
    ]
    p12 = by_page["درآمد معدن دولومیت (صفحه 12)"]
    assert [(ln.description_raw, ln.quantity, ln.unit_norm) for ln in p12.lines] == [
        ("شاتکریت لایه اول با بتن 300 کیلو سیمان به ازای هر سانت ضخامت", Decimal("270"), "m2"),
        ("بوته کنی در زمین های پوشیده شده از بوته", Decimal("10000"), "m2"),
        ("کانال کنی", Decimal("600"), "m3"),
        ("بارگیری و تخلیه", Decimal("2000"), "m3"),
    ]


def _make_minimal_symbol_ttf(code_to_gid: dict[int, int], *, upm: int = 2048, ng: int = 221) -> bytes:
    """Build a minimal SFNT binary (head + maxp + cmap format-4 subtable for pid=3, eid=0)."""
    import struct

    head = bytearray(54)
    struct.pack_into(">H", head, 18, upm)
    maxp = struct.pack(">IH", 0x00010000, ng)

    sorted_items = sorted(code_to_gid.items())
    # Encode each entry as its own 1-char delta segment + 0xFFFF sentinel
    segs = [(c, c, (gid - c) & 0xFFFF) for c, gid in sorted_items] + [(0xFFFF, 0xFFFF, 1)]
    seg_count = len(segs)
    sub = bytearray()
    sub += struct.pack(">HHHHHHH", 4, 16 + 8 * seg_count, 0, seg_count * 2, 2, 0, 0)
    sub += b"".join(struct.pack(">H", ec) for _, ec, _ in segs)
    sub += struct.pack(">H", 0)
    sub += b"".join(struct.pack(">H", sc) for sc, _, _ in segs)
    sub += b"".join(struct.pack(">h", dl if dl < 0x8000 else dl - 0x10000) for _, _, dl in segs)
    sub += b"\x00\x00" * seg_count
    cmap = struct.pack(">HH", 0, 1) + struct.pack(">HHI", 3, 0, 12) + bytes(sub)

    tables = [("cmap", bytes(cmap)), ("head", bytes(head)), ("maxp", maxp)]
    offset = 12 + 16 * len(tables)
    directory = bytearray()
    payload = bytearray()
    for tag, content in tables:
        directory += tag.encode("latin1") + struct.pack(">III", 0, offset, len(content))
        pad = (-len(content)) % 4
        payload += content + (b"\x00" * pad)
        offset += len(content) + pad
    return struct.pack(">IHHHH", 0x00010000, len(tables), 16, 0, 0) + bytes(directory) + bytes(payload)


def test_ttf_cmap_repairs_broken_bfont_tounicode_with_anchor_check():
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    from app.features.volume_report.extraction.pdf_extractor import _build_tounicode_stream, _synthesize_ttf_tounicode

    ttf_bytes = _make_minimal_symbol_ttf({
        0xF001: 3,    # ' '
        0xF002: 15,   # '1'
        0xF003: 139,  # 'ش'
        0xF004: 127,  # 'ر'
        0xF005: 115,  # 'ح'
        0xF006: 211,  # 'لا' (\uFEFB)
    })
    ff2 = DecodedStreamObject()
    ff2.set_data(ttf_bytes)
    font = DictionaryObject({
        NameObject("/Subtype"): NameObject("/TrueType"),
        NameObject("/BaseFont"): NameObject("/IFRQAJ+BZar,Bold"),
        NameObject("/FontDescriptor"): DictionaryObject({NameObject("/FontFile2"): ff2}),
        NameObject("/ToUnicode"): _build_tounicode_stream({0x01: " ", 0x02: "1"}),
    })

    repaired = _synthesize_ttf_tounicode(font, "/IFRQAJ+BZar,Bold")
    assert repaired == {0x01: " ", 0x02: "1", 0x03: "ش", 0x04: "ر", 0x05: "ح", 0x06: "\uFEFB"}

    # Mismatched anchor (code 0x02 maps to '2' instead of Bornayekta '1' at GID 15) -> must refuse to guess
    bad_anchor = DictionaryObject({
        NameObject("/Subtype"): NameObject("/TrueType"),
        NameObject("/BaseFont"): NameObject("/CustomNonBFont"),
        NameObject("/FontDescriptor"): DictionaryObject({NameObject("/FontFile2"): ff2}),
        NameObject("/ToUnicode"): _build_tounicode_stream({0x01: " ", 0x02: "2"}),
    })
    assert _synthesize_ttf_tounicode(bad_anchor, "/CustomNonBFont") is None

    # Unused /WinAnsiEncoding Excel helper font without /ToUnicode is never touched
    winansi = DictionaryObject({
        NameObject("/Subtype"): NameObject("/TrueType"),
        NameObject("/BaseFont"): NameObject("/BCDGEE+BNazaninBold"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        NameObject("/FontDescriptor"): DictionaryObject({NameObject("/FontFile2"): ff2}),
    })
    assert _synthesize_ttf_tounicode(winansi, "/BCDGEE+BNazaninBold") is None


def test_page_xy_transforms_rotated_pages():
    from app.features.volume_report.extraction.pdf_extractor import _page_xy

    cm_up = [1, 0, 0, 1, 0, 0]
    cm_flip = [1, 0, 0, -1, 0, 800]
    tm = [0, 1, -1, 0, 120.0, 540.0]
    assert _page_xy(cm_up, tm, 0) == (120.0, 540.0)
    assert _page_xy(cm_flip, tm, 0) == (120.0, -540.0)
    assert _page_xy(cm_up, tm, 90) == (540.0, -120.0)
    assert _page_xy(cm_up, tm, 180) == (-120.0, -540.0)
    assert _page_xy(cm_up, tm, 270) == (-540.0, 120.0)
