"""Continuation pages of a multi-page income table (PDF).

A project's income table often runs over several PDF pages and only the first page repeats the column header. The
following pages come out of the PDF reader as one string per row:

    035101 4,000 مترمکعب 412,500 ریال 1,650,000,000 ریال 1.3 1.28 1.57 4,304,277,120 ریال      (code  qty unit price ... )

and the activity name wraps over the rows above and below ("خاکبرداری از قرضه جهت مصرف در خاکریزی" / … / "معمولی").
`continuation_grid` turns such a page into a small synthetic grid with the standard header (شرح / فعالیت / حجم / واحد) so that
`parse_income_sheet` reads it exactly like a first page. Pure (no DB).
"""

import re
from typing import Any

from app.features.volume_report.extraction.normalize import normalize_text
from app.features.volume_report.extraction.units import normalize_unit

_CODE_ROW = re.compile(r"^\s*(?:\d{1,3}\s+)?(\d{5,6})\b\s*(.*)$")
# quantity, unit (letters, "/" and "-" only), price with thousands separators — the first such triple on the row
_QTY_UNIT_PRICE = re.compile(r"(?<![\d,.])(\d[\d,]*(?:\.\d+)?)\s+([^\d\s][^\d]*?)\s+(\d{1,3}(?:,\d{3})+)(?!\d)")
# Uncoded continuation tables (no "کد" column, e.g. landscape PDF statements) have <qty> <physical_unit> <price|ریال>.
_UNCODED_QTY_UNIT_PRICE = re.compile(
    r"(?<![\d,.])(\d[\d,]*(?:\.\d+)?)\s+([^\d\s][^\d]*?)\s+(?=(?:\d{1,3}(?:,\d{3})+|\bریال\b))"
)
_STOP_WORDS = ("جمع", "مابه التفاوت", "مقایسه درآمد")
_EXPENSE_PAGE_MARKERS = (
    "کد دستگاه",
    "نام دستگاه",
    "هزینه ماشین آلات",
    "هزینه کل",
    "ساعت کل کارکرد",
    "پیمانکاران جزء",
)
_MIN_CODE_ROWS = 3
HEADER = ["شرح", "فعالیت", "حجم", "واحد"]


def _digits(text: str) -> str:
    text = re.sub(r"[۰-۹]", lambda m: str(ord(m.group()) - 0x06F0), text)
    text = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), text)
    return text.replace("،", ",").replace("ي", "ی").replace("ك", "ک").replace("‌", " ")


def _row_text(row: list[Any]) -> str:
    return re.sub(r"\s+", " ", _digits(" ".join(str(c) for c in row if c is not None))).strip()


def _is_noise(text: str) -> bool:
    """A page or section number sitting alone on its row."""
    return bool(re.fullmatch(r"\d{1,3}", text))


def _match_coded_row(text: str) -> tuple[str, str, str, str] | None:
    code = _CODE_ROW.match(text)
    if not code:
        return None
    tail = code.group(2)
    found = _QTY_UNIT_PRICE.search(tail)
    if not found:
        return None
    return tail[: found.start()].strip(), found.group(1), found.group(2).strip(), code.group(1)


def _match_uncoded_row(text: str) -> tuple[str, str, str, str] | None:
    for found in _UNCODED_QTY_UNIT_PRICE.finditer(text):
        unit = found.group(2).strip()
        unit_info = normalize_unit(unit)
        # Require a physical/income BOQ unit (never empty/unknown prose or equipment-rental hours "ساعت").
        if unit_info.unit_norm in ("other", "hr"):
            continue
        return text[: found.start()].strip(), found.group(1), unit, ""
    return None


def _collect_items(lines: list[str], matcher: Any) -> tuple[list[tuple[str, Any]], list[int]]:
    items: list[tuple[str, Any]] = []
    for text in lines:
        if any(normalize_text(text).startswith(word) for word in _STOP_WORDS):
            break
        matched = matcher(text)
        if matched is not None:
            items.append(("code", matched))
        elif not _is_noise(text):
            items.append(("frag", text))
    codes = [i for i, (kind, _) in enumerate(items) if kind == "code"]
    return items, codes


def continuation_grid(rows: list[list[Any]]) -> list[list[Any]] | None:
    """Synthetic grid (header + one row per item row) or None when the page is not an income continuation."""
    lines = [text for row in rows if (text := _row_text(row))]
    items, codes = _collect_items(lines, _match_coded_row)
    if len(codes) < _MIN_CODE_ROWS:
        head_norm = " ".join(normalize_text(line) for line in lines[:10])
        if any(marker in head_norm for marker in _EXPENSE_PAGE_MARKERS):
            return None
        items, codes = _collect_items(lines, _match_uncoded_row)
        if len(codes) < _MIN_CODE_ROWS:
            return None

    before: dict[int, list[str]] = {i: [] for i in codes}
    after: dict[int, list[str]] = {i: [] for i in codes}
    bounds = [-1, *codes, len(items)]
    for left, right in zip(bounds, bounds[1:]):
        fragments = [items[k][1] for k in range(left + 1, right) if items[k][0] == "frag"]
        prev_code = left if left in before else None
        next_code = right if right in before else None
        if not fragments:
            continue
        if prev_code is None:  # text above the first code row
            if next_code is not None:
                before[next_code].extend(fragments)
        elif next_code is None:  # text below the last code row
            after[prev_code].extend(fragments)
        elif len(fragments) == 1:
            prev_empty, next_empty = not items[prev_code][1][0], not items[next_code][1][0]
            # a lone line belongs to the row that has no name of its own; otherwise it is the title of the next row
            (after[prev_code] if prev_empty and not next_empty else before[next_code]).extend(fragments)
        else:
            cut = len(fragments) // 2
            after[prev_code].extend(fragments[:cut])
            before[next_code].extend(fragments[cut:])

    grid: list[list[Any]] = [list(HEADER)]
    for i in codes:
        inline, qty, unit, code_no = items[i][1]
        description = " ".join(part for part in [*before[i], inline, *after[i]] if part).strip()
        fallback = f"ردیف {code_no}" if code_no else ""
        grid.append([None, description or fallback, qty.replace(",", ""), unit])
    return grid
