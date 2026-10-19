import asyncio
import uuid
from unittest.mock import AsyncMock, patch

from app.features.documents.ingestion.parser import DocumentPage, ExtractedImage
from app.features.documents.ingestion.pipeline import IngestionContext, OCRStep
from app.features.documents.ingestion.text_layer import (
    TEXT_GARBLED,
    TEXT_OK,
    TEXT_VISUAL_PERSIAN,
    assess_text_layer,
    fix_visual_persian,
)

# Lines copied (short, non-sensitive headings) from a real "Machine Translated by Google" PDF text layer:
# Arabic presentation forms, letters reversed inside each word.
_VISUAL_HEADING = "ﺶﺨﺑ- 2  ﻂﯾاﺮﺷ و ﻂﺑاﻮﺿدادراﺮﻗ"
_VISUAL_BODY = "ﺖ ﺳا ﻪﮐ ﯽﻨﯿﻣز ﺖﺳا ﻪﺑ ﯽﻨﻌﻣ ﻪﻨﯾﺰﻫ"
# Symbol noise like the leftover OCR layer of a scanned page.
_GARBAGE = '~ m -· . "" .;.,..- .,.~ •• --..:..\'.:...? Y AP2 ;.:.1\\ Si ... \')l.t \\O ,T•V ,AO, ,llf \'f"f\' .AT 1 . T.bf•'


def test_plain_persian_and_english_text_are_ok():
    assert assess_text_layer("این یک متن عادی فارسی است که ترتیب منطقی دارد و باید دست نخورده بماند") == TEXT_OK
    assert assess_text_layer("Section 6 - HSE requirements for contractors working on site") == TEXT_OK
    assert assess_text_layer("") == TEXT_OK


def test_numeric_tables_are_not_flagged_as_garbage():
    table = "پیمانکار 58.63% 124,082,022,612 7.28% 15,404,904,102 65.90% 139,486,926,714 کارفرما 43.04% 1,822,032,198"
    assert assess_text_layer(table) == TEXT_OK


def test_visual_order_presentation_forms_are_detected():
    assert assess_text_layer(_VISUAL_HEADING + "\n" + _VISUAL_BODY) == TEXT_VISUAL_PERSIAN


def test_symbol_noise_is_detected_as_garbled():
    assert assess_text_layer(_GARBAGE) == TEXT_GARBLED


def test_fix_visual_persian_restores_readable_words():
    fixed = fix_visual_persian(_VISUAL_HEADING)
    assert any("بخش" in token for token in fixed.split())
    assert "شرایط" in fixed.split()
    assert "2" in fixed.split()
    # presentation forms are folded to plain letters
    assert assess_text_layer(fixed) == TEXT_OK


def test_fix_visual_persian_glues_chunks_the_font_split_inside_a_word():
    # "ﺖ ﺳا" is the single word «است» drawn as two chunks.
    assert "است" in fix_visual_persian("ﺖ ﺳا").split()


def test_fix_visual_persian_keeps_latin_and_digit_runs_readable():
    fixed = fix_visual_persian("ﻪﺤﻔﺻ6 CFT-0001BD زا47")
    assert "CFT-0001BD" in fixed
    assert "47" in fixed.split()


def _context(pages):
    return IngestionContext(document_id=uuid.uuid4(), file_path="/fake/doc.pdf", db=None, pages=pages)


async def test_ocr_step_replaces_a_bad_text_layer_with_page_ocr():
    page = DocumentPage(page_number=3, text="متن تعمیرشده", needs_ocr=True, metadata={"page": 3, "text_layer": "visual_persian"})
    rendered = ExtractedImage(data=b"x" * 200, name="p.png", format="png")

    with (
        patch("app.features.documents.ingestion.pipeline.render_pdf_page", return_value=rendered),
        patch(
            "app.features.documents.ingestion.pipeline.extract_text_from_image",
            new=AsyncMock(return_value="متن درست و کامل صفحه که از تصویر خوانده شد"),
        ),
    ):
        await OCRStep().run(_context([page]))

    assert page.text == "متن درست و کامل صفحه که از تصویر خوانده شد"
    assert page.metadata["text_layer"] == "ocr"


async def test_ocr_step_keeps_the_repaired_text_when_page_ocr_fails():
    page = DocumentPage(page_number=1, text="متن تعمیرشده", needs_ocr=True, metadata={"page": 1, "text_layer": "visual_persian"})
    rendered = ExtractedImage(data=b"x" * 200, name="p.png", format="png")

    with (
        patch("app.features.documents.ingestion.pipeline.render_pdf_page", return_value=rendered),
        patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=AsyncMock(return_value="")),
    ):
        await OCRStep().run(_context([page]))

    assert page.text == "متن تعمیرشده"
    assert page.metadata["text_layer"] == "visual_persian"


async def test_ocr_step_runs_pages_concurrently_but_within_the_limit():
    running = 0
    peak = 0

    async def slow_ocr(data, fmt):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.05)
        running -= 1
        return "متن خوانده شده از تصویر صفحه"

    pages = [DocumentPage(page_number=i, text="x", needs_ocr=True) for i in range(1, 9)]
    rendered = ExtractedImage(data=b"x" * 200, name="p.png", format="png")
    with (
        patch("app.features.documents.ingestion.pipeline.render_pdf_page", return_value=rendered),
        patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=slow_ocr),
        patch("app.features.documents.ingestion.pipeline.get_settings") as settings,
    ):
        settings.return_value.ocr_enabled = True
        settings.return_value.ocr_concurrency = 3
        settings.return_value.ocr_max_images_per_doc = 50
        settings.return_value.ocr_max_replaced_pages = 300
        settings.return_value.ocr_replace_bad_text_layer = True
        await OCRStep().run(_context(pages))

    assert 1 < peak <= 3
    assert all(page.metadata.get("text_layer") == "ocr" for page in pages)


async def test_ocr_step_respects_the_replaced_pages_cap():
    pages = [DocumentPage(page_number=i, text="x", needs_ocr=True) for i in range(1, 5)]
    rendered = ExtractedImage(data=b"x" * 200, name="p.png", format="png")
    with (
        patch("app.features.documents.ingestion.pipeline.render_pdf_page", return_value=rendered),
        patch(
            "app.features.documents.ingestion.pipeline.extract_text_from_image",
            new=AsyncMock(return_value="متن خوانده شده از تصویر صفحه"),
        ),
        patch("app.features.documents.ingestion.pipeline.get_settings") as settings,
    ):
        settings.return_value.ocr_enabled = True
        settings.return_value.ocr_concurrency = 4
        settings.return_value.ocr_max_images_per_doc = 50
        settings.return_value.ocr_max_replaced_pages = 2
        settings.return_value.ocr_replace_bad_text_layer = True
        await OCRStep().run(_context(pages))

    assert sum(1 for page in pages if page.metadata.get("text_layer") == "ocr") == 2
