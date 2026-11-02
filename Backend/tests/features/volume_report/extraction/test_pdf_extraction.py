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

