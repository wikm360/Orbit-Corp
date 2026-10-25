"""Recognises pages whose extracted text cannot carry their meaning: engineering drawings and charts.

OCR turns a drawing into loose numbers and labels ("3.00", "0.55", "1657.28", "مقطع 1-1") with no hint of what each
number measures. The agent then either guesses from other pages or says it cannot tell. Such pages are flagged
(`metadata.page_kind = "drawing"`) and get a note at the top of their text pointing to the `view_document_page` tool, which
attaches the page image to the chat model's next message so it reads the drawing itself.

Calibrated on 12 pages of a real 144-page statement (4 drawings/charts, 8 tables/prose): see `looks_like_drawing`.
"""

import re

DRAWING_KIND = "drawing"

DRAWING_NOTE = (
    "[توجه: این صفحه یک نقشه یا نمودار فنی است. متن این صفحه فقط نوشته‌ها و اعداد پراکنده‌ی استخراج‌شده است و مشخص نیست "
    "هر عدد کدام بُعد، تراز یا نما را نشان می‌دهد؛ از روی این اعداد طول، دهانه یا ارتفاع را حدس نزن. برای پرسش دربارهٔ "
    "اندازه‌ها و برچسب‌های نقشه از ابزار view_document_page (document_id و شماره‌ی همین صفحه) استفاده کن تا تصویر صفحه را خودت ببینی.]"
)

# Elevation labels of a longitudinal/bridge drawing ("PL=1657.55", "GL=1655.00"): both present = a drawing.
_ELEVATION = re.compile(r"\b(PL|GL)\s*[=:]\s*[\d.]+", re.IGNORECASE)
# Lines that name a view of a drawing: plan, elevation, section, detail, centre line.
_VIEW_LABEL = re.compile(
    r"^\s*(?:پلان|نما|مقطع(?:\s*[\w\-ـ]+){0,3}|[\w]+\s*-\s*[\w]+\s+مقطع|جزی[یئ]ات|برش(?:\s*[\w\-]+)?|C\.?\s?L\.?|PLAN|ELEVATION|SECTION(?:\s*[\w\-]+)?|DETAIL)\s*$",
    re.IGNORECASE,
)
_NUMERIC_LINE = re.compile(r"^[\s\-+.,/=:×x*mMcCkKgGLPl()\d۰-۹٠-٩%°\"']*$")
_WORD = re.compile(r"[\w؀-ۿ]+")


def looks_like_drawing(text: str) -> bool:
    """True for a page that is mostly a drawing/chart rather than prose or a table.

    Any one of: (a) both `PL=` and `GL=` elevation labels; (b) at least 3 view-label lines (plan / elevation / section /
    detail); (c) a page of loose fragments: >= 15 non-table lines of which >= 60% are bare numbers or <= 2 words (a chart's
    axis labels, dimension strings). Markdown table rows (lines with `|`) are not counted in (c): a table page is not a
    drawing, and a drawing that also contains a table is caught by (a) or (b)."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return False
    kinds = {m.group(1).upper() for m in _ELEVATION.finditer(text)}
    if {"PL", "GL"} <= kinds:
        return True
    if sum(1 for line in lines if _VIEW_LABEL.match(line)) >= 3:
        return True
    loose = [line for line in lines if "|" not in line]
    if len(loose) >= 15:
        fragments = sum(1 for line in loose if _NUMERIC_LINE.match(line) or len(_WORD.findall(line)) <= 2)
        if fragments / len(loose) >= 0.6:
            return True
    return False


def mark_drawing_page(page) -> bool:
    """Flags `page` (a `DocumentPage`) when it looks like a drawing; idempotent. Returns whether it is flagged."""
    if page.metadata.get("page_kind") == DRAWING_KIND:
        return True
    if not page.text or not looks_like_drawing(page.text):
        return False
    page.metadata["page_kind"] = DRAWING_KIND
    page.text = f"{DRAWING_NOTE}\n\n{page.text}"
    return True
