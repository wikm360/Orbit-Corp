"""PDF report table extractor for the volume-report pipeline.

Converts vector PDF pages into a WorkbookData of SheetData grids, mirroring Excel sheets.
Extracts rows and columns based on text coordinates (X, Y) without requiring OCR or LLM.
"""

import logging
import re
import statistics
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
_REFERENCE_FONT = 4.8  # body font size (pt) the two distances above were tuned for; wide sheets are shrunk to fit one page
_MIN_SCALE, _MAX_SCALE = 0.4, 1.5
_QTY_TERMS = frozenset({"حجم", "درصد حجم", "حجم درصد", "مقدار", "احجام"})


def _cluster_words_into_rows(words: list[tuple[float, float, str]], tolerance: float = _Y_ROW_TOLERANCE) -> list[tuple[float, list[tuple[float, str]]]]:
    """Groups words into horizontal rows sorted by descending Y (top of page to bottom)."""
    y_buckets: dict[float, list[tuple[float, str]]] = defaultdict(list)
    for x, y, text in words:
        matched_y = None
        for by in y_buckets:
            if abs(by - y) <= tolerance:
                matched_y = by
                break
        if matched_y is None:
            matched_y = y
        y_buckets[matched_y].append((x, text))

    sorted_ys = sorted(y_buckets.keys(), reverse=True)
    return [(y, sorted(y_buckets[y], key=lambda w: -w[0])) for y in sorted_ys]


_DESC_LABELS = frozenset({"فعالیت", "شرح فعالیت", "شرح عملیات", "شرح کار", "شرح آیتم", "آیتم", "موضوع"})
_QTY_WITH_TEXT = re.compile(r"^(?P<text>.*?[^\d\s.,\-/٫])\s+(?P<num>\d[\d,.٫]*|-)$")
_TIE_RATIO = 0.35


def _label_index(headers: list[str], labels: frozenset[str]) -> int | None:
    return next((i for i, h in enumerate(headers) if h in labels), None)


def _attach_wrapped_descriptions(grid_body: list[list[Any]], ys: list[float], headers: list[str]) -> list[list[Any]]:
    """A long description wraps over several PDF lines, vertically centred on the row that carries the code, unit and
    quantity: the lines above/below land in rows of their own and (on very wide sheets) the text even spills into the
    neighbouring "ضریب شکست"/quantity columns. Without this a row whose description sits on those lines is dropped
    (empty description) together with its quantity. Fragments are glued to the nearest code row by Y; a tie goes to the
    row that still has no text of its own, else to the row above. Rows from the first "جمع …" row on are left alone."""
    desc_col = _label_index(headers, _DESC_LABELS)
    qty_col = next((i for i, h in enumerate(headers) if h in _QTY_TERMS), None)
    unit_col = headers.index("واحد") if "واحد" in headers else None
    if desc_col is None or qty_col is None or unit_col is None or desc_col == 0 or not (desc_col < qty_col <= unit_col or desc_col < unit_col):
        return grid_body

    cutoff = next((i for i, row in enumerate(grid_body) if any(isinstance(c, str) and c.strip().startswith("جمع") for c in row[:3])), len(grid_body))
    body, tail = grid_body[:cutoff], grid_body[cutoff:]

    def text_cells(row: list[Any]) -> list[str]:
        return [str(row[i]).strip() for i in range(1, min(unit_col, len(row))) if i != qty_col and row[i] not in (None, "")]

    codes: list[int] = []
    for i, row in enumerate(body):
        if unit_col < len(row) and row[unit_col] not in (None, ""):
            codes.append(i)
    if not codes:
        return grid_body

    head: dict[int, list[str]] = {c: [] for c in codes}
    own: dict[int, list[str]] = {c: [] for c in codes}
    foot: dict[int, list[str]] = {c: [] for c in codes}
    for c in codes:
        row = body[c]
        own[c] = text_cells(row)
        if isinstance(row[0], str):  # "81 140801 اضافه بها به ردیف های": the description's first words spill into the code cell
            tokens = row[0].split()
            keep = 0
            while keep < len(tokens) and re.fullmatch(r"[\d٠-٩۰-۹.\-]+", tokens[keep]):
                keep += 1
            if 0 < keep < len(tokens):
                row[0] = " ".join(tokens[:keep])
                head[c].append(" ".join(tokens[keep:]))
        qty = row[qty_col] if qty_col < len(row) else None
        if isinstance(qty, str) and (m := _QTY_WITH_TEXT.match(qty.strip())):
            own[c].append(m.group("text"))  # "متر 0": a wrapped word glued to the quantity
            row[qty_col] = m.group("num")

    fragments: list[int] = []
    for i, row in enumerate(body):
        if i in head:
            continue
        if row[0] in (None, "") and not any(c not in (None, "") for c in row[unit_col:]) and text_cells(row):
            fragments.append(i)

    for f in fragments:
        above = max((c for c in codes if c < f), default=None)
        below = min((c for c in codes if c > f), default=None)
        if above is None or below is None:
            target = above if below is None else below
        else:
            d_above, d_below = abs(ys[above] - ys[f]), abs(ys[below] - ys[f])
            if abs(d_above - d_below) <= _TIE_RATIO * min(d_above, d_below):
                has_text = lambda c: bool(own[c] or head[c] or foot[c])  # noqa: E731
                target = below if (has_text(above) and not has_text(below)) else above
            else:
                target = above if d_above < d_below else below
        (foot if (target is not None and target < f) else head)[target].append(" ".join(text_cells(body[f])))

    fragment_set = set(fragments)
    result: list[list[Any]] = []
    for i, row in enumerate(body):
        if i in fragment_set:
            continue
        if i not in head:
            result.append(row)  # section/title rows and anything that is not a wrapped description line
            continue
        pieces = head[i] + own[i] + foot[i]
        new_row = list(row)
        new_row[desc_col] = " ".join(pieces) if pieces else None
        for k in range(1, min(unit_col, len(new_row))):
            if k not in (desc_col, qty_col):
                new_row[k] = None
        result.append(new_row)
    return result + tail


def extract_pdf_page_grid(page: pypdf.PageObject) -> Rows:
    """Extracts a 2D table grid (Rows = list[list[Any]]) from a PDF page."""
    words: list[tuple[float, float, str]] = []
    font_sizes: list[float] = []

    def visitor(text: str, cm: Any, tm: Any, font_dict: Any, font_size: Any) -> None:
        stripped = text.strip()
        if stripped:
            words.append((float(tm[4]), float(tm[5]), stripped))
            if font_size:
                font_sizes.append(float(font_size))

    try:
        page.extract_text(visitor_text=visitor)
    except Exception as exc:
        logger.warning("pypdf visitor failed on page: %s", exc)
        return []

    if not words:
        return []

    # A very wide sheet is shrunk to fit the page, so all distances shrink with the font: scale the thresholds with it,
    # otherwise neighbouring header labels ("ضریب شکست" / "حجم") merge into one cell and the layout is not recognised.
    scale = 1.0
    if font_sizes:
        scale = min(_MAX_SCALE, max(_MIN_SCALE, statistics.median(font_sizes) / _REFERENCE_FONT))
    rows_by_y = _cluster_words_into_rows(words, _Y_ROW_TOLERANCE * scale)
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
        if abs(w[0] - current_col[-1][0]) < _X_WORD_DISTANCE * scale:
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
    body_start = len(grid)
    body_ys: list[float] = []
    for row_y, row_words in rows_by_y[header_idx + 1:]:
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
        body_ys.append(row_y)
        prev_row = row

    headers = [str(h) for h in grid[body_start - 1]]
    return grid[:body_start] + _attach_wrapped_descriptions(grid[body_start:], body_ys, headers)


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

