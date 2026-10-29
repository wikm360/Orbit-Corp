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


def test_unmapped_pdf_glyph_tokens_detected_as_garbled():
    glyph_stream = "/0 /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14 /15 /i255"
    assert assess_text_layer(glyph_stream) == TEXT_GARBLED
    single_glyph = "/i255"
    assert assess_text_layer(single_glyph) == TEXT_GARBLED


def test_control_character_stream_detected_as_garbled():
    ctrl_stream = "ÊÀ§\x03\xad\x7fY|»\x03sÔ\x8fY\x03\x18Ê»Y\x80³\x03Ã|À¿YÂy\x03ÊËY\x80mY"
    assert assess_text_layer(ctrl_stream) == TEXT_GARBLED


def test_legacy_non_unicode_ansi_persian_detected_as_garbled():
    # Zarnegar / IranSystem / ANSI-mapped Persian fonts (common in نشریه 101, ضابطه 773)
    sample_nashrieh_101 = (
        "Ê¯Zy cZÌ¸¼  /  ¹Á{ ¶§01/06 /1404˺˾\n"
        "g:    ZÆ¿M dYu Á ¨u Âf{ Ä¯ Ê¿Zfy{ ÄyZ ZË Äf§³ Y« Ì» cÁZn» { Ä¯ Ê¿Zfy{ ÄyZ Är¿ZÀq\n"
        "|¿Â « dy{ ÄÀe ®Ë{¿ Y |ËZ] |ÀZ] Ã| ÃY ºËu ¶yY{ f» lÀa {Á|u Ã| Ã{Y{.    ¾ËY «"
    )
    assert assess_text_layer(sample_nashrieh_101) == TEXT_GARBLED

    # MacPersian / Zarnegar B-variant mapping into Latin Extended-A/B
    sample_latin_ext = "ŭƺººƫ ŜººƫŚƣ Źŵ řŹ ƶººƗƺưŬƯ Ʋººƿř ƾººƨǀƳƹźŤƨƫř ƶŴººƀƳ ƾººƴƟ ƽŚƷŹŚǀººƘƯ ƹ ƎŝřƺººƋ ƲººƿƹŶţ"
    assert assess_text_layer(sample_latin_ext) == TEXT_GARBLED


def test_european_languages_with_accents_are_not_flagged_as_garbled():
    french = "Le modèle d'intelligence artificielle est très efficace pour détecter les anomalies et gérer l'ensemble des données."
    german = "Die Überprüfung der Qualität und die Ausführung der Bauarbeiten sind für die Sicherheit von größter Bedeutung."
    spanish = "La evaluación técnica de las operaciones ejecutadas según la norma oficial establecida por el ministerio."
    assert assess_text_layer(french) == TEXT_OK
    assert assess_text_layer(german) == TEXT_OK
    assert assess_text_layer(spanish) == TEXT_OK



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


def _distinct_render(file_path, page_number):
    """A different image per page (identical images are read only once per document)."""
    return ExtractedImage(data=f"page-{page_number}".encode() * 40, name="p.png", format="png")


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

    async def slow_ocr(data, fmt, report=None):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.05)
        running -= 1
        return "متن خوانده شده از تصویر صفحه"

    pages = [DocumentPage(page_number=i, text="x", needs_ocr=True) for i in range(1, 9)]
    with (
        patch("app.features.documents.ingestion.pipeline.render_pdf_page", side_effect=_distinct_render),
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


async def test_identical_images_in_one_document_are_read_once():
    logo = ExtractedImage(data=b"logo-bytes" * 30, name="logo.png", format="png")
    pages = [DocumentPage(page_number=i, text=f"صفحه {i}", images=[logo]) for i in range(1, 6)]
    ocr = AsyncMock(return_value="شرکت نمونه")

    with patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr):
        await OCRStep().run(_context(pages))

    assert ocr.await_count == 1
    assert all("شرکت نمونه" in page.text for page in pages)  # every page still gets the text


async def test_repeated_images_do_not_use_up_the_image_budget():
    logo = ExtractedImage(data=b"logo-bytes" * 30, name="logo.png", format="png")
    unique = ExtractedImage(data=b"table-bytes" * 30, name="t.png", format="png")
    pages = [DocumentPage(page_number=i, text="x", images=[logo]) for i in range(1, 6)]
    pages.append(DocumentPage(page_number=6, text="x", images=[unique]))
    ocr = AsyncMock(side_effect=lambda data, fmt, report=None: "لوگو" if data.startswith(b"logo") else "جدول")

    with (
        patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr),
        patch("app.features.documents.ingestion.pipeline.get_settings") as settings,
    ):
        settings.return_value.ocr_enabled = True
        settings.return_value.ocr_concurrency = 4
        settings.return_value.ocr_max_images_per_doc = 2  # room for exactly the two distinct images
        settings.return_value.ocr_max_replaced_pages = 300
        settings.return_value.ocr_replace_bad_text_layer = True
        await OCRStep().run(_context(pages))

    assert ocr.await_count == 2
    assert "جدول" in pages[5].text and all("لوگو" in page.text for page in pages[:5])


async def test_ocr_results_are_cached_across_documents(db_session):
    image = ExtractedImage(data=b"scan-bytes" * 30, name="scan.png", format="png")
    ocr = AsyncMock(return_value="متن خوانده‌شده از اسکن")

    def context():
        page = DocumentPage(page_number=1, text="", images=[image])
        return IngestionContext(document_id=uuid.uuid4(), file_path="/f.pdf", db=db_session, pages=[page]), page

    with patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr):
        first_ctx, first_page = context()
        await OCRStep().run(first_ctx)
        second_ctx, second_page = context()
        await OCRStep().run(second_ctx)  # a different document with the same image

    assert ocr.await_count == 1
    assert first_page.text == second_page.text == "متن خوانده‌شده از اسکن"


async def test_empty_ocr_results_are_not_cached(db_session):
    image = ExtractedImage(data=b"blank-bytes" * 30, name="b.png", format="png")
    ocr = AsyncMock(return_value="")

    with patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr):
        for _ in range(2):
            page = DocumentPage(page_number=1, text="", images=[image])
            await OCRStep().run(IngestionContext(document_id=uuid.uuid4(), file_path="/f.pdf", db=db_session, pages=[page]))

    assert ocr.await_count == 2  # a failure or blank read is retried next time


async def test_changing_the_ocr_model_does_not_reuse_old_text(db_session):
    image = ExtractedImage(data=b"scan-bytes2" * 30, name="scan.png", format="png")
    ocr = AsyncMock(return_value="متن مدل اول")

    async def run():
        page = DocumentPage(page_number=1, text="", images=[image])
        await OCRStep().run(IngestionContext(document_id=uuid.uuid4(), file_path="/f.pdf", db=db_session, pages=[page]))

    with (
        patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr),
        patch("app.features.documents.ingestion.ocr_cache.vision_model_name", return_value="model-a"),
    ):
        await run()
    with (
        patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr),
        patch("app.features.documents.ingestion.ocr_cache.vision_model_name", return_value="model-b"),
    ):
        await run()

    assert ocr.await_count == 2


async def test_the_rotation_found_at_ocr_time_is_stored_in_the_page_metadata_for_scan_pages_and_image_files():
    from pathlib import Path

    async def ocr_that_reports(data, fmt, report=None):
        if report is not None:
            report["rotation"] = 270
        return "متن خوانده شده از تصویر صفحه"

    # 1. a scan page read as a whole rendered page
    scan = DocumentPage(page_number=4, text="", needs_ocr=True, metadata={"page": 4, "text_layer": "scan"})
    rendered = ExtractedImage(data=b"x" * 200, name="p.png", format="png")
    with (
        patch("app.features.documents.ingestion.pipeline.render_pdf_page", return_value=rendered),
        patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr_that_reports),
    ):
        await OCRStep().run(_context([scan]))
    assert scan.metadata["rotation"] == 270

    # 2. an uploaded image file: the image is the page
    image_page = DocumentPage(page_number=1, text="", images=[ExtractedImage(data=b"i" * 200, name="s.png", format="png")], metadata={"page": 1})
    context = IngestionContext(document_id=uuid.uuid4(), file_path="/uploads/scan.PNG", db=None, pages=[image_page])
    with patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr_that_reports):
        await OCRStep().run(context)
    assert image_page.metadata["rotation"] == 270

    # 3. an image embedded in a PDF page says nothing about the page's own rotation
    embedded = DocumentPage(page_number=2, text="متن", images=[ExtractedImage(data=b"e" * 200, name="e.png", format="png")], metadata={"page": 2})
    with patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr_that_reports):
        await OCRStep().run(_context([embedded]))
    assert "rotation" not in embedded.metadata

    # 4. a read that did not determine the rotation stores nothing
    plain = DocumentPage(page_number=3, text="", needs_ocr=True, metadata={"page": 3})
    with (
        patch("app.features.documents.ingestion.pipeline.render_pdf_page", return_value=rendered),
        patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=AsyncMock(return_value="متن خوانده شده از تصویر صفحه")),
    ):
        await OCRStep().run(_context([plain]))
    assert "rotation" not in plain.metadata


async def test_a_cache_hit_still_returns_the_stored_rotation(db_session):
    from app.features.documents.ingestion.ocr_cache import get_cached_ocr, put_cached_ocr
    from app.features.documents.ingestion.pipeline import OcrRead, _OcrReader

    key = f"key-{uuid.uuid4()}"
    await put_cached_ocr(db_session, key, "متن", 90)
    assert await get_cached_ocr(db_session, key) == ("متن", 90)
    await put_cached_ocr(db_session, f"{key}-old", "بدون چرخش")  # rows from before the column existed / undetermined
    assert await get_cached_ocr(db_session, f"{key}-old") == ("بدون چرخش", None)

    ocr = AsyncMock(side_effect=AssertionError("a cache hit must not call the vision model"))
    reader = _OcrReader(db_session, 2)
    with (
        patch("app.features.documents.ingestion.pipeline.extract_text_from_image", new=ocr),
        patch("app.features.documents.ingestion.pipeline.ocr_cache_key", return_value=key),
    ):
        assert await reader.read(b"anything", "png") == OcrRead("متن", 90)
    assert reader.cache_hits == 1 and reader.api_calls == 0
