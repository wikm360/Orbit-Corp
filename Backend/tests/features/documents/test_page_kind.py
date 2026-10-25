import uuid

from app.features.documents.ingestion import pipeline as pipeline_module
from app.features.documents.ingestion.page_kind import DRAWING_NOTE, looks_like_drawing, mark_drawing_page
from app.features.documents.ingestion.parser import DocumentPage
from app.features.documents.ingestion.pipeline import IngestionContext, PageKindStep

# Synthetic stand-ins for what OCR returns (no real document text in the repository).
DRAWING_WITH_ELEVATIONS = """PL=1657.55
GL=1655.00

| ردیف | تعداد | طول (m) |
|---|---|---|
| 1 | 20 | 30.77 |

0.30
0.55
-3.00-
1.8
1654.58
"""

DRAWING_WITH_VIEW_LABELS = """پلان
نما
مقطع طولی
مقطع عرضی
1-1 مقطع
2.5
-3.00-
"""

CHART_OF_FRAGMENTS = "\n".join(
    ["نمودار دانه‌بندی", "Percent passing (%)"] + [str(v) for v in range(100, 0, -10)] + ["0.075", "0.3", "0.6", "1.18", "2.36", "4.75", "9.5", "12.5"]
)

TABLE_PAGE = "\n".join(
    ["| No. | Name | Km | Value |", "| --- | --- | --- | --- |"] + [f"| {i} | {i + 1} | {i}+250.00 | {i * 11.5} |" for i in range(40)]
)

PROSE_PAGE = (
    "طرح مخلوط آسفالتی\n\n"
    "آزمون کنترل کیفی مصالح سنگی مطابق روش های استاندارد انجام پذیرفته و نتایج آنها در جدول ارائه شده است. "
    "اندازه مصالح سنگی برای انجام آزمایش های مختلف در روش های استاندارد آزمایش مشخص شده است.\n\n"
    "وزن مخصوص و جذب آب مصالح سنگی مانده روی الک شماره ۴ به روش استاندارد تعیین شد.\n"
)

SIGNATURE_PAGE = "نماینده مشاور\n\nشرکت نمونه\nکارگاه پروژه\nنماینده پیمانکار\n"


def test_drawings_and_charts_are_recognised():
    assert looks_like_drawing(DRAWING_WITH_ELEVATIONS)  # PL= and GL= labels
    assert looks_like_drawing(DRAWING_WITH_VIEW_LABELS)  # plan / elevation / section labels
    assert looks_like_drawing(CHART_OF_FRAGMENTS)  # axis values and short labels only


def test_tables_prose_and_signature_pages_are_not_drawings():
    assert not looks_like_drawing(TABLE_PAGE)
    assert not looks_like_drawing(PROSE_PAGE)
    assert not looks_like_drawing(SIGNATURE_PAGE)  # "نماینده" starts with "نما" but is not a view label
    assert not looks_like_drawing("")
    assert not looks_like_drawing("PL=1657.55")  # one elevation label alone is not enough


def test_mark_drawing_page_is_idempotent_and_keeps_the_text():
    page = DocumentPage(page_number=75, text=DRAWING_WITH_ELEVATIONS, metadata={"page": 75})
    assert mark_drawing_page(page)
    assert page.metadata["page_kind"] == "drawing" and page.metadata["page"] == 75
    assert page.text.startswith(DRAWING_NOTE) and page.text.endswith(DRAWING_WITH_ELEVATIONS)
    once = page.text
    assert mark_drawing_page(page) and page.text == once  # not doubled on a re-run

    prose = DocumentPage(page_number=1, text=PROSE_PAGE, metadata={"page": 1})
    assert not mark_drawing_page(prose) and "page_kind" not in prose.metadata and prose.text == PROSE_PAGE


def _context(pages):
    return IngestionContext(document_id=uuid.uuid4(), file_path="/f.pdf", db=None, pages=pages)


async def test_page_kind_step_flags_only_drawing_pages_and_can_be_switched_off(monkeypatch):
    pages = [
        DocumentPage(page_number=1, text=PROSE_PAGE, metadata={"page": 1}),
        DocumentPage(page_number=2, text=DRAWING_WITH_VIEW_LABELS, metadata={"page": 2}),
    ]
    await PageKindStep().run(_context(pages))
    assert [p.metadata.get("page_kind") for p in pages] == [None, "drawing"]

    settings = pipeline_module.get_settings()
    monkeypatch.setattr(settings, "ocr_mark_drawing_pages", False)
    other = [DocumentPage(page_number=1, text=DRAWING_WITH_ELEVATIONS, metadata={"page": 1})]
    await PageKindStep().run(_context(other))
    assert "page_kind" not in other[0].metadata and other[0].text == DRAWING_WITH_ELEVATIONS
