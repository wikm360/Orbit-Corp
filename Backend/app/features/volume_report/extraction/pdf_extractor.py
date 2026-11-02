"""PDF report table extractor for the volume-report pipeline.

Converts vector PDF pages into a WorkbookData of SheetData grids, mirroring Excel sheets.
Extracts rows and columns based on text coordinates (X, Y) without requiring OCR or LLM.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import pypdf

from app.core.exceptions import BadRequestError
from app.features.volume_report.extraction.workbook import Rows, SheetData, WorkbookData

logger = logging.getLogger(__name__)

# Distance thresholds for horizontal clustering and column separation
_Y_ROW_TOLERANCE = 2.8  # points
_X_WORD_DISTANCE = 18.0  # points: adjacent words within this distance belong to the same cell header
_QTY_TERMS = frozenset({"حجم", "درصد حجم", "حجم درصد", "مقدار", "احجام"})


def _cluster_words_into_rows(words: list[tuple[float, float, str]]) -> list[tuple[float, list[tuple[float, str]]]]:
    """Groups words into horizontal rows sorted by descending Y (top of page to bottom)."""
    y_buckets: dict[float, list[tuple[float, str]]] = defaultdict(list)
    for x, y, text in words:
        matched_y = None
        for by in y_buckets:
            if abs(by - y) <= _Y_ROW_TOLERANCE:
                matched_y = by
                break
        if matched_y is None:
            matched_y = y
        y_buckets[matched_y].append((x, text))

    sorted_ys = sorted(y_buckets.keys(), reverse=True)
    return [(y, sorted(y_buckets[y], key=lambda w: -w[0])) for y in sorted_ys]


def extract_pdf_page_grid(page: pypdf.PageObject) -> Rows:
    """Extracts a 2D table grid (Rows = list[list[Any]]) from a PDF page."""
    words: list[tuple[float, float, str]] = []

    def visitor(text: str, cm: Any, tm: Any, font_dict: Any, font_size: Any) -> None:
        stripped = text.strip()
        if stripped:
            words.append((float(tm[4]), float(tm[5]), stripped))

    try:
        page.extract_text(visitor_text=visitor)
    except Exception as exc:
        logger.warning("pypdf visitor failed on page: %s", exc)
        return []

    if not words:
        return []

    rows_by_y = _cluster_words_into_rows(words)
    if not rows_by_y:
        return []

    # 1. Look for table header row (contains a quantity label and "واحد")
    header_idx: int | None = None
    for idx, (_, row_words) in enumerate(rows_by_y[:20]):
        row_text = " ".join(w[1] for w in row_words)
        if any(term in row_text for term in _QTY_TERMS) and ("واحد" in row_text or "قیمت" in row_text):
            header_idx = idx
            break

    if header_idx is None:
        # No clear table header found: return lines as single-cell rows
        return [[" ".join(w[1] for w in row_words)] for _, row_words in rows_by_y]

    _, hw = rows_by_y[header_idx]

    # 2. Cluster header words into column headers based on horizontal distance
    col_anchors: list[list[tuple[float, str]]] = []
    current_col = [hw[0]]
    for w in hw[1:]:
        if abs(w[0] - current_col[-1][0]) < _X_WORD_DISTANCE:
            current_col.append(w)
        else:
            col_anchors.append(current_col)
            current_col = [w]
    col_anchors.append(current_col)

    col_defs = []
    for anchor in col_anchors:
        x_min = min(w[0] for w in anchor)
        x_max = max(w[0] for w in anchor)
        text = " ".join(w[1] for w in anchor)
        col_defs.append({"text": text, "center": (x_min + x_max) / 2.0})

    # Sort RTL (descending center x)
    col_defs.sort(key=lambda c: -c["center"])

    # Column boundary midpoints
    col_bounds = [
        (col_defs[i]["center"] + col_defs[i + 1]["center"]) / 2.0
        for i in range(len(col_defs) - 1)
    ]

    def assign_col(x: float) -> int:
        for idx, bound in enumerate(col_bounds):
            if x >= bound:
                return idx
        return len(col_defs) - 1

    grid: Rows = []

    # Prepend top title lines so extract_site_name can find the project name
    for _, row_words in rows_by_y[:header_idx]:
        title_text = " ".join(w[1] for w in row_words)
        title_row: list[Any] = [None] * len(col_defs)
        title_row[0] = title_text
        grid.append(title_row)

    # Header row
    grid.append([c["text"] for c in col_defs])

    # 3. Parse table body rows
    prev_row: list[Any] | None = None
    for _, row_words in rows_by_y[header_idx + 1:]:
        row_cells: list[list[tuple[float, str]]] = [[] for _ in range(len(col_defs))]
        for x, text in row_words:
            c_idx = assign_col(x)
            row_cells[c_idx].append((x, text))

        row: list[Any] = []
        for cell_words in row_cells:
            if not cell_words:
                row.append(None)
            else:
                cell_words.sort(key=lambda item: -item[0])  # RTL within cell
                row.append(" ".join(w[1] for w in cell_words))

        if not any(c is not None for c in row):
            continue

        # Handle multi-line descriptions: if only column 0 has text and no other columns,
        # merge with previous row if previous row exists and isn't a total row.
        desc_cell = row[0]
        other_cells = row[1:]
        if (
            desc_cell
            and not any(other_cells)
            and prev_row is not None
            and not str(desc_cell).strip().startswith("جمع")
        ):
            prev_row[0] = f"{prev_row[0] or ''} {desc_cell}".strip()
            continue

        grid.append(row)
        prev_row = row

    return grid


def _detect_pdf_sheet_name(page_num: int, page: pypdf.PageObject) -> str:
    """Inspects the top lines of a page to give the virtual sheet a descriptive title."""
    words: list[tuple[float, float, str]] = []

    def visitor(text: str, cm: Any, tm: Any, font_dict: Any, font_size: Any) -> None:
        stripped = text.strip()
        if stripped:
            words.append((float(tm[4]), float(tm[5]), stripped))

    try:
        page.extract_text(visitor_text=visitor)
    except Exception:
        return f"صفحه {page_num}"

    if not words:
        return f"صفحه {page_num}"

    rows_by_y = _cluster_words_into_rows(words)
    top_texts = [" ".join(w[1] for w in row_words) for _, row_words in rows_by_y[:8]]
    combined = " ".join(top_texts)

    site = ""
    for line in top_texts[:4]:
        if "پروژه" in line:
            parts = line.split("پروژه", 1)
            site = parts[1].split("در ماه", 1)[0].replace("در", "").strip()
            break

    # Determine kind for probe.py classification
    if "برنامه" in combined:
        prefix = "برنامه"
    elif "درآمد" in combined or "درامد" in combined:
        prefix = "درآمد"
    elif "هزینه" in combined or "هزينه" in combined:
        prefix = "هزینه"
    else:
        prefix = "صفحه"

    name_parts = [prefix]
    if site:
        name_parts.append(site)
    name_parts.append(f"(صفحه {page_num})")
    return " ".join(name_parts).strip()


def open_pdf_as_workbook(path: str) -> WorkbookData:
    """Opens a PDF file as a WorkbookData with one SheetData per page."""
    try:
        reader = pypdf.PdfReader(path)
    except Exception as exc:
        raise BadRequestError(f"Could not open PDF file {Path(path).name}: {exc}") from exc

    sheets: list[SheetData] = []
    for i, page in enumerate(reader.pages, start=1):
        name = _detect_pdf_sheet_name(i, page)
        sheets.append(
            SheetData(
                name=name,
                visibility="visible",
                _loader=lambda p=page: extract_pdf_page_grid(p),
            )
        )
    return WorkbookData(sheets=sheets)

