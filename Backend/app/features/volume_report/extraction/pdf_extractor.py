"""PDF report table extractor for the volume-report pipeline.

Converts vector PDF pages into a WorkbookData of SheetData grids, mirroring Excel sheets.
Extracts rows and columns based on text coordinates (X, Y) without requiring OCR or LLM.
"""

import logging
import re
import statistics
import unicodedata
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
_QTY_TERMS = frozenset({"حجم", "درصد حجم", "حجم درصد", "مقدار", "احجام", "تعداد دستگاه"})
_RTL_BRACKET_MIRROR = str.maketrans("()[]«»", ")(][»«")
_SUBHEADER_TOKENS = frozenset({
    "شکست", "ضریب", "بالاسری", "منطقه", "ای", "پیشنهادی", "مبنا", "شاخص", "سه", "ماهه", "اول", "دوم", "سوم", "چهارم",
})
_MAX_SUBHEADER_DROP_PT = 11.0
_MAX_UNIT_WRAP_PT = 12.0
_MAX_DESC_WRAP_PT = 18.0


def _clean_word(text: str) -> str:
    """Some PDFs embed Arabic presentation-form glyphs ("ﺣﺠﻢ", "ﻗ") and Arabic ي/ك; fold them to the plain Persian letters
    so header labels and descriptions match regardless of the font the sheet was exported with."""
    return unicodedata.normalize("NFKC", text).replace("ي", "ی").replace("ك", "ک").strip()


def _page_y(cm: Any, tm: Any) -> float:
    """Text Y in the usual bottom-up convention. Some exporters flip the page (`cm` with a negative d), which would
    otherwise list the table bottom-to-top."""
    try:
        flipped = float(cm[3]) < 0
    except (TypeError, IndexError, ValueError):
        flipped = False
    return -float(tm[5]) if flipped else float(tm[5])


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
_DESC_BOUNDARY_SHARE = 0.2  # of the gap between the description header and the next column, measured from the next column


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
        stripped = _clean_word(text)
        if stripped:
            words.append((float(tm[4]), _page_y(cm, tm), stripped))
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
        # Plain visitor_text can collapse multi-column TJ arrays (e.g. Foxit PDFs); try layout spans
        layout_grid = _tjs_grid(page)
        if _has_income_layout(layout_grid):
            return layout_grid
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
    # Numeric columns are centred under their header, so the midpoint separates them. A description column is
    # right-aligned text whose start moves left with its length: its boundary sits close to the next column instead.
    col_bounds = []
    for i in range(len(col_defs) - 1):
        right, left = col_defs[i]["center"], col_defs[i + 1]["center"]
        share = _DESC_BOUNDARY_SHARE if col_defs[i]["text"] in _DESC_LABELS else 0.5
        col_bounds.append(left + share * (right - left))

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
    plain_grid = grid[:body_start] + _attach_wrapped_descriptions(grid[body_start:], body_ys, headers)
    if not _has_income_layout(plain_grid):
        layout_grid = _tjs_grid(page)
        if _has_income_layout(layout_grid):
            return layout_grid
    return plain_grid


def _has_income_layout(grid: list[list[Any]]) -> bool:
    """Return True when the extracted grid has a header row parseable by income_parser."""
    from app.features.volume_report.extraction.income_parser import find_layout

    return bool(grid) and find_layout(grid) is not None


def _to_logical_rtl(vis: str) -> str:
    """Convert visually left-to-right RTL glyph text into logical Persian word order."""
    from unicodedata import bidirectional

    if not any(bidirectional(ch) in ("R", "AL") for ch in vis):
        return _clean_word(vis)

    ltr_classes = ("L", "EN", "AN")
    joiners = set(".,/-٫٬،:")
    rev = vis.translate(_RTL_BRACKET_MIRROR)[::-1]
    out: list[str] = []
    n = len(rev)
    i = 0
    while i < n:
        if bidirectional(rev[i]) not in ltr_classes:
            out.append(rev[i])
            i += 1
            continue
        j = i + 1
        last_ltr = i
        while j < n:
            bd = bidirectional(rev[j])
            if bd in ltr_classes:
                last_ltr = j
                j += 1
            elif rev[j] in joiners or (rev[j] == " " and rev[j - 1] not in (",", "،")):
                j += 1
            else:
                break
        out.append(rev[i : last_ltr + 1][::-1])
        i = last_ltr + 1
    return _clean_word("".join(out))


def _extract_tjs_spans(page: Any) -> list[Any]:
    """Extract non-rotated positioned text-show spans via pypdf's layout engine."""
    from pypdf._text_extraction._layout_mode._fixed_width_page import recurs_to_target_op
    from pypdf._text_extraction._layout_mode._text_state_manager import TextStateManager
    from pypdf.generic import ContentStream

    if not hasattr(page, "_layout_mode_fonts") or page.get("/Contents") is None:
        return []
    fonts = page._layout_mode_fonts()
    ops = iter(ContentStream(page["/Contents"].get_object(), page.pdf, "bytes").operations)
    state_mgr = TextStateManager()
    spans: list[Any] = []
    for operands, op in ops:
        if op in (b"BT", b"q"):
            _, tjs = recurs_to_target_op(ops, state_mgr, b"ET" if op == b"BT" else b"Q", fonts, strip_rotated=True)
            spans.extend(tjs)
        else:
            state_mgr.set_state_param(op, operands)
    return [t for t in spans if not t.rotated and t.txt]


def _cluster_tjs_rows(spans: list[Any]) -> list[tuple[float, list[tuple[float, float, str]]]]:
    """Group tjs spans into y-rows and merge horizontally adjacent fragments into cells."""
    if not spans:
        return []
    ordered = sorted(spans, key=lambda s: (-s.ty, s.tx))
    grouped: list[list[Any]] = []
    anchor_y = ordered[0].ty
    for sp in ordered:
        if grouped and abs(sp.ty - anchor_y) <= _Y_ROW_TOLERANCE:
            grouped[-1].append(sp)
        else:
            grouped.append([sp])
            anchor_y = sp.ty

    rows: list[tuple[float, list[tuple[float, float, str]]]] = []
    for row_spans in grouped:
        row_spans.sort(key=lambda s: s.tx)
        heights = sorted(float(s.font_height) for s in row_spans if float(s.font_height) > 0)
        med_h = heights[len(heights) // 2] if heights else _REFERENCE_FONT
        gap_tol = max(3.2, min(4.5, med_h * 0.58))
        space_tol = max(1.5, med_h * 0.28)
        cells_raw: list[tuple[float, float, str]] = []
        cx0, cx1, ctxt = row_spans[0].tx, row_spans[0].displaced_tx, row_spans[0].txt
        for sp in row_spans[1:]:
            gap = sp.tx - cx1
            if gap <= gap_tol:
                sep = " " if (gap > space_tol and not ctxt.endswith(" ") and not sp.txt.startswith(" ")) else ""
                ctxt = f"{ctxt}{sep}{sp.txt}"
                cx1 = max(cx1, sp.displaced_tx)
            else:
                text = _to_logical_rtl(ctxt)
                if text:
                    cells_raw.append((cx0, cx1, text))
                cx0, cx1, ctxt = sp.tx, sp.displaced_tx, sp.txt
        text = _to_logical_rtl(ctxt)
        if text:
            cells_raw.append((cx0, cx1, text))
        if cells_raw:
            avg_y = sum(float(s.ty) for s in row_spans) / len(row_spans)
            rows.append((avg_y, cells_raw))
    return rows


def _is_subheader_continuation(text: str) -> bool:
    """Return True for wrapped multi-line sub-header labels right below the main header row."""
    from app.features.volume_report.extraction.normalize import normalize_text

    norm = normalize_text(text)
    if not norm:
        return True
    cleaned = re.sub(r"\(\s*\d{4}\s*\)", "", norm).strip()
    if not cleaned:
        return True
    return all(tok in _SUBHEADER_TOKENS for tok in cleaned.split())


def _attach_wrapped_tjs_descriptions(
    body_rows: list[list[Any]],
    body_ys: list[float],
    desc_col: int,
    qty_col: int,
) -> list[list[Any]]:
    """Attach wrapped desc-only continuation lines (above or below) to the nearest qty row."""
    from app.features.volume_report.extraction.normalize import parse_quantity

    qty_indices = [i for i, row in enumerate(body_rows) if parse_quantity(row[qty_col]) is not None]
    if not qty_indices:
        return body_rows

    qty_set = set(qty_indices)
    attached: dict[int, list[tuple[float, str]]] = {}
    for q_idx in qty_indices:
        d_val = str(body_rows[q_idx][desc_col]).strip() if body_rows[q_idx][desc_col] is not None else ""
        if d_val:
            attached[q_idx] = [(body_ys[q_idx], d_val)]

    consumed: set[int] = set()
    for idx, row in enumerate(body_rows):
        if idx in qty_set:
            continue
        d_val = str(row[desc_col]).strip() if row[desc_col] is not None else ""
        if not d_val:
            continue
        if any(col != desc_col and cell is not None and str(cell).strip() for col, cell in enumerate(row)):
            continue
        # Only consider qty rows not separated from `idx` by another qty row
        candidates: list[int] = []
        for q_idx in qty_indices:
            lo, hi = (idx, q_idx) if idx < q_idx else (q_idx, idx)
            if any(k in qty_set for k in range(lo + 1, hi)):
                continue
            if abs(body_ys[idx] - body_ys[q_idx]) <= _MAX_DESC_WRAP_PT:
                candidates.append(q_idx)
        if not candidates:
            continue
        best_q = min(candidates, key=lambda q: abs(body_ys[idx] - body_ys[q]))
        attached.setdefault(best_q, []).append((body_ys[idx], d_val))
        consumed.add(idx)

    for q_idx, parts in attached.items():
        parts.sort(key=lambda item: -item[0])
        body_rows[q_idx][desc_col] = " ".join(p for _, p in parts)

    return [row for idx, row in enumerate(body_rows) if idx not in consumed]


def _attach_wrapped_units(
    body_rows: list[list[Any]],
    body_ys: list[float],
    qty_idx: int,
    unit_idx: int,
    desc_idx: int,
) -> tuple[list[list[Any]], list[float]]:
    """Merge multi-line wrapped units (e.g. 'مترمکعب-' / 'کیلومتر') into the adjacent qty row."""
    from app.features.volume_report.extraction.normalize import parse_quantity

    empty_unit_qty = [
        i for i, row in enumerate(body_rows)
        if parse_quantity(row[qty_idx]) is not None and not (row[unit_idx] and str(row[unit_idx]).strip())
    ]
    if not empty_unit_qty:
        return body_rows, body_ys

    fragments: dict[int, list[tuple[float, str]]] = {}
    consumed: set[int] = set()
    for idx, row in enumerate(body_rows):
        u_val = str(row[unit_idx]).strip() if row[unit_idx] is not None else ""
        if not u_val:
            continue
        if (row[qty_idx] is not None and str(row[qty_idx]).strip()) or (row[desc_idx] is not None and str(row[desc_idx]).strip()):
            continue
        if any(
            col not in (unit_idx,) and cell is not None and str(cell).strip()
            for col, cell in enumerate(row)
        ):
            continue
        best_q = min(empty_unit_qty, key=lambda qi: abs(body_ys[idx] - body_ys[qi]))
        if abs(body_ys[idx] - body_ys[best_q]) <= _MAX_UNIT_WRAP_PT:
            fragments.setdefault(best_q, []).append((body_ys[idx], u_val))
            consumed.add(idx)

    for q_idx, parts in fragments.items():
        parts.sort(key=lambda item: -item[0])
        body_rows[q_idx][unit_idx] = " ".join(p for _, p in parts)

    kept_rows = [row for idx, row in enumerate(body_rows) if idx not in consumed]
    kept_ys = [y for idx, y in enumerate(body_ys) if idx not in consumed]
    return kept_rows, kept_ys


def _tjs_grid(page: Any) -> list[list[Any]]:
    """Reconstruct a multi-column PDF grid from positioned text-show (tjs) spans."""
    from bisect import bisect_right
    from app.features.volume_report.extraction.income_parser import find_layout
    from app.features.volume_report.extraction.normalize import normalize_text

    rows = _cluster_tjs_rows(_extract_tjs_spans(page))
    if not rows:
        return []

    header_idx: int | None = None
    for idx, (_, cells) in enumerate(rows[:20]):
        row_norm = normalize_text(" ".join(c[2] for c in cells))
        if any(term in row_norm for term in _QTY_TERMS) and ("واحد" in row_norm or "قیمت" in row_norm):
            header_idx = idx
            break
    if header_idx is None:
        return [[" ".join(c[2] for c in cells)] for _, cells in rows]

    header_y, header_cells = rows[header_idx]
    n_cols = len(header_cells)
    boundaries = [0.5 * (header_cells[i][1] + header_cells[i + 1][0]) for i in range(n_cols - 1)]
    prefix_rows = [[" ".join(c[2] for c in cells)] for _, cells in rows[:header_idx]]
    header_row = [c[2] for c in header_cells]

    layout_probe = find_layout([header_row])
    qty_col = layout_probe[1]["qty"] if layout_probe else None
    unit_col = layout_probe[1]["unit"] if layout_probe else None
    desc_col = layout_probe[1]["desc"] if layout_probe else None

    body_rows: list[list[Any]] = []
    body_ys: list[float] = []
    in_subheader = True
    for y_val, cells in rows[header_idx + 1 :]:
        if in_subheader and (header_y - y_val) <= _MAX_SUBHEADER_DROP_PT:
            combined = " ".join(c[2] for c in cells)
            if _is_subheader_continuation(combined):
                continue
        in_subheader = False

        grid_row: list[Any] = [None] * n_cols
        col_dist: list[float] = [float("inf")] * n_cols
        for cx0, cx1, ctext in cells:
            mid = 0.5 * (cx0 + cx1)
            col = bisect_right(boundaries, mid)
            hx_mid = 0.5 * (header_cells[col][0] + header_cells[col][1])
            dist = abs(mid - hx_mid)
            if grid_row[col] is None:
                grid_row[col] = ctext
                col_dist[col] = dist
            elif col == qty_col:
                if dist < col_dist[col]:
                    grid_row[col] = ctext
                    col_dist[col] = dist
            else:
                grid_row[col] = f"{grid_row[col]} {ctext}"
        body_rows.append(grid_row)
        body_ys.append(y_val)

    if qty_col is not None and unit_col is not None and desc_col is not None:
        body_rows, body_ys = _attach_wrapped_units(body_rows, body_ys, qty_col, unit_col, desc_col)

    if desc_col is not None and qty_col is not None:
        return prefix_rows + [header_row] + _attach_wrapped_tjs_descriptions(body_rows, body_ys, desc_col, qty_col)
    return prefix_rows + [header_row] + _attach_wrapped_descriptions(body_rows, body_ys, header_row)


def _detect_pdf_sheet_name(page_num: int, page: pypdf.PageObject) -> str:
    """Inspects the top lines of a page to give the virtual sheet a descriptive title."""
    words: list[tuple[float, float, str]] = []

    def visitor(text: str, cm: Any, tm: Any, font_dict: Any, font_size: Any) -> None:
        stripped = _clean_word(text)
        if stripped:
            words.append((float(tm[4]), _page_y(cm, tm), stripped))

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
    if "پیش بینی" in combined and ("درآمد" in combined or "درامد" in combined):
        prefix = "برنامه درآمد"  # forecast of the next period, same table layout as the income page
    elif "برنامه" in combined or "پیش بینی" in combined:
        prefix = "برنامه"  # EVM / budget summary page: not a quantity table
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

