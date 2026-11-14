"""PDF report table extractor for the volume-report pipeline.

Converts vector PDF pages into a WorkbookData of SheetData grids, mirroring Excel sheets.
Extracts rows and columns based on text coordinates (X, Y) without requiring OCR or LLM.
"""

import logging
import re
import statistics
import struct
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
_RTL_CHAR_RE = re.compile(r"[\u0600-\u06FF\uFE70-\uFEFF\uFDF0-\uFDFF]")
_SUBHEADER_TOKENS = frozenset({
    "شکست", "ضریب", "بالاسری", "منطقه", "ای", "پیشنهادی", "مبنا", "شاخص", "سه", "ماهه", "اول", "دوم", "سوم", "چهارم",
})
_MAX_SUBHEADER_DROP_PT = 11.0
_MAX_UNIT_WRAP_PT = 12.0
_MAX_DESC_WRAP_PT = 18.0

# Canonical Bornayekta B-series (B Nazanin / B Zar / B Titr / B Mitra / ...) glyph-ID -> Unicode map.
# Nitro PDF Pro (and some legacy PDF writers) embed these fonts with a Symbol cmap (pid=3, eid=0) and
# omit Persian entries from /ToUnicode, leaving byte codes mapped to raw ASCII/control bytes.
# Ligatures (205..215) emit single presentation-form codepoints so `_to_logical_rtl` keeps their
# internal letter order intact when reversing visual RTL strings, then `_clean_word` (`NFKC`) folds them.
_BORN_GID_TO_UNICODE: dict[int, str] = {
    3: " ", 4: "!", 5: "%", 6: "(", 7: ")", 8: "*", 9: "+", 10: ",", 11: "-", 12: ".", 13: "/",
    **{14 + d: str(d) for d in range(10)},
    24: ":", 25: "=", 44: "،", 47: "ـ", 54: "ّ",
    76: "ء", 77: "آ", 78: "آ", 79: "أ", 80: "أ", 81: "ؤ", 82: "ؤ", 83: "إ", 84: "إ",
    85: "ئ", 86: "ئ", 87: "ئ", 88: "ئ", 89: "ا", 90: "ا",
    91: "ب", 92: "ب", 93: "ب", 94: "ب", 95: "پ", 96: "پ", 97: "پ", 98: "پ",
    99: "ت", 100: "ت", 101: "ت", 102: "ت", 103: "ث", 104: "ث", 105: "ث", 106: "ث",
    107: "ج", 108: "ج", 109: "ج", 110: "ج", 111: "چ", 112: "چ", 113: "چ", 114: "چ",
    115: "ح", 116: "ح", 117: "ح", 118: "ح", 119: "خ", 120: "خ", 121: "خ", 122: "خ",
    123: "د", 124: "د", 125: "ذ", 126: "ذ", 127: "ر", 128: "ر", 129: "ز", 130: "ز",
    131: "ژ", 132: "ژ", 133: "س", 134: "س", 135: "س", 136: "س",
    137: "ش", 138: "ش", 139: "ش", 140: "ش", 141: "ص", 142: "ص", 143: "ص", 144: "ص",
    145: "ض", 146: "ض", 147: "ض", 148: "ض", 149: "ط", 150: "ط", 151: "ط", 152: "ط",
    153: "ظ", 154: "ظ", 155: "ظ", 156: "ظ", 157: "ع", 158: "ع", 159: "ع", 160: "ع",
    161: "غ", 162: "غ", 163: "غ", 164: "غ", 165: "ف", 166: "ف", 167: "ف", 168: "ف",
    169: "ق", 170: "ق", 171: "ق", 172: "ق", 173: "ک", 174: "ک", 175: "ک", 176: "ک",
    177: "گ", 178: "گ", 179: "گ", 180: "گ", 181: "ل", 182: "ل", 183: "ل", 184: "ل",
    185: "م", 186: "م", 187: "م", 188: "م", 189: "ن", 190: "ن", 191: "ن", 192: "ن",
    193: "و", 194: "و", 195: "ه", 196: "ه", 197: "ه", 198: "ه",
    199: "ة", 200: "ة", 201: "ی", 202: "ی", 203: "ی", 204: "ی",
    205: "\uFEF5", 206: "\uFEF5", 207: "\uFEF7", 208: "\uFEF7",
    209: "\uFEF9", 210: "\uFEF9", 211: "\uFEFB", 212: "\uFEFB",
    215: "\uFDF2",
}
_BORN_ANCHOR_TO_GID: dict[str, int] = {
    ch: gid for gid, ch in _BORN_GID_TO_UNICODE.items() if gid <= 25
}
_BORN_FONT_NAME_RE = re.compile(
    r"(?:^|[+/])(?:[A-Z]{6}\+)?B[-,\s]?(?:Zar|Nazanin|Titr|Mitra|Lotus|Koodak|Traffic|Roya|Yagut|Yaqut|"
    r"Jadid|Homa|Ferdosi|Elham|Davat|Compset|Badr|Arash)\b",
    re.IGNORECASE,
)
_BORN_GLYPH_COUNTS = frozenset({217, 221})
_BF_CHAR_BLOCK_RE = re.compile(r"beginbfchar\s*(.*?)\s*endbfchar", re.DOTALL)
_BF_RANGE_BLOCK_RE = re.compile(r"beginbfrange\s*(.*?)\s*endbfrange", re.DOTALL)
_HEX_TOKEN_RE = re.compile(r"<([0-9A-Fa-f]+)>")


def _clean_word(text: str) -> str:
    """Some PDFs embed Arabic presentation-form glyphs ("ﺣﺠﻢ", "ﻗ") and Arabic ي/ك; fold them to the plain Persian letters
    so header labels and descriptions match regardless of the font the sheet was exported with."""
    return unicodedata.normalize("NFKC", text).replace("ي", "ی").replace("ك", "ک").strip()


def _page_xy(cm: Any, tm: Any, rotation: int = 0) -> tuple[float, float]:
    """Text (X, Y) in upright display orientation so rotated landscape pages sort top-to-bottom cleanly."""
    px, py = float(tm[4]), float(tm[5])
    rot = (rotation or 0) % 360
    if rot == 90:
        return py, -px
    if rot == 180:
        return -px, -py
    if rot == 270:
        return -py, px
    try:
        flipped = float(cm[3]) < 0
    except (TypeError, IndexError, ValueError):
        flipped = False
    return px, (-py if flipped else py)


def _page_y(cm: Any, tm: Any, rotation: int = 0) -> float:
    """Text Y in the usual bottom-up display convention."""
    return _page_xy(cm, tm, rotation)[1]


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


_NOTES_BOUNDARY_GAP = 0.08  # keep 8% margin from neighboring ratio column (SPI/CPI) for notes column
_MAX_EVM_WRAP_PT = 35.0
_EVM_AMOUNT_RE = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d{6,})")
_SMALL_INT_RE = re.compile(r"^\d{1,3}$")


def _to_ascii_digits(text: str) -> str:
    text = re.sub(r"[۰-۹]", lambda m: str(ord(m.group()) - 0x06F0), text)
    return re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), text)


def _split_evm_prefix(text: str) -> tuple[str, str, str]:
    """Split an EVM anchor row into (leading_row_index, inline_project_name, amounts_and_ratios)."""
    m = _EVM_AMOUNT_RE.search(_to_ascii_digits(text))
    if m is None:
        return "", text.strip(), ""
    prefix = text[: m.start()].strip()
    rest = text[m.start() :].strip()
    tokens = prefix.split()
    row_idx = ""
    if tokens and _SMALL_INT_RE.match(_to_ascii_digits(tokens[0])):
        row_idx = tokens[0]
        tokens = tokens[1:]
    return row_idx, " ".join(tokens), rest


def _find_evm_notes_filter(
    rows_by_y: list[tuple[float, list[tuple[float, str]]]],
    evm_idx: int,
    tjs_probe: Any | None = None,
) -> tuple[int | None, Any | None]:
    """Return (notes_header_row_idx, is_notes_word_x_fn) when the EVM header has a dedicated "توضیحات" column."""
    from app.features.volume_report.extraction.normalize import normalize_text

    hdr_lo = max(0, evm_idx - 2)
    hdr_hi = min(len(rows_by_y), evm_idx + 4)
    notes_pos: tuple[int, float] | None = None
    for idx in range(hdr_lo, hdr_hi):
        for wx, txt in rows_by_y[idx][1]:
            if normalize_text(txt).strip(": ") == "توضیحات":
                notes_pos = (idx, wx)
                break
        if notes_pos is not None:
            break
    if notes_pos is None:
        return None, None

    notes_r, notes_x = notes_pos
    same_row = rows_by_y[notes_r][1]
    right_hdr = [(wx, txt) for wx, txt in same_row if wx > notes_x + 10.0 and normalize_text(txt).strip(": ") != "توضیحات"]
    left_hdr = [(wx, txt) for wx, txt in same_row if wx < notes_x - 10.0 and normalize_text(txt).strip(": ") != "توضیحات"]
    if not right_hdr and not left_hdr:
        hdr_words = [(wx, txt) for idx in range(hdr_lo, hdr_hi) for wx, txt in rows_by_y[idx][1]]
        right_hdr = [(wx, txt) for wx, txt in hdr_words if wx > notes_x + 10.0 and "spi" in txt.lower()]
        left_hdr = [(wx, txt) for wx, txt in hdr_words if wx < notes_x - 10.0 and "spi" in txt.lower()]

    if right_hdr:
        adj_x, adj_txt = min(right_hdr, key=lambda p: p[0])
        if tjs_probe is not None and "cpi" in adj_txt.lower() and "spi" in adj_txt.lower():
            for _, cells in tjs_probe()[:20]:
                for x0, _, span_txt in cells:
                    if "spi" in span_txt.lower() and notes_x < x0 < adj_x:
                        adj_x = x0
        bound = adj_x - max(2.5, _NOTES_BOUNDARY_GAP * (adj_x - notes_x))
        return notes_r, (lambda wx, b=bound: wx < b)

    if left_hdr:
        adj_x, _ = max(left_hdr, key=lambda p: p[0])
        bound = adj_x + 0.55 * (notes_x - adj_x)
        return notes_r, (lambda wx, b=bound: wx >= b)

    return None, None


def _attach_wrapped_evm_names(
    body_mains: list[str],
    body_ys: list[float],
    is_header_fragment: Any,
    max_wrap_pt: float,
) -> tuple[dict[int, list[str]], dict[int, list[str]], set[int], set[int]]:
    """Group multi-line project names above/below each numeric EVM row by Y distance without crossing row barriers."""
    anchors: list[int] = []
    barriers: set[int] = set()
    fragments: list[int] = []
    inline_names: dict[int, str] = {}
    for k, m_txt in enumerate(body_mains):
        if not m_txt:
            continue
        ascii_txt = _to_ascii_digits(m_txt)
        if _EVM_AMOUNT_RE.search(ascii_txt):
            anchors.append(k)
            inline_names[k] = _split_evm_prefix(m_txt)[1]
        elif _SMALL_INT_RE.match(ascii_txt.strip()):
            barriers.add(k)
        elif not is_header_fragment(m_txt):
            fragments.append(k)

    anchor_set = set(anchors)
    head: dict[int, list[str]] = {a: [] for a in anchors}
    foot: dict[int, list[str]] = {a: [] for a in anchors}
    attached: set[int] = set()
    for f in fragments:
        above = next((k for k in range(f - 1, -1, -1) if k in anchor_set or k in barriers), None)
        if above is not None and above in barriers:
            above = None
        below = next((k for k in range(f + 1, len(body_mains)) if k in anchor_set or k in barriers), None)
        if below is not None and below in barriers:
            below = None
        if above is None and below is None:
            continue
        fy = body_ys[f]
        d_above = abs(body_ys[above] - fy) if above is not None else float("inf")
        d_below = abs(body_ys[below] - fy) if below is not None else float("inf")
        if min(d_above, d_below) > max_wrap_pt:
            continue
        if above is not None and below is not None and abs(d_above - d_below) <= _TIE_RATIO * min(d_above, d_below):
            has_a = bool(inline_names[above] or head[above] or foot[above])
            has_b = bool(inline_names[below] or head[below] or foot[below])
            target: int | None = below if (has_a and not has_b) else above
        else:
            target = below if (below is not None and d_below < d_above) else above
        assert target is not None
        (foot if target < f else head)[target].append(body_mains[f])
        attached.add(f)

    return head, foot, anchor_set, attached


def _extract_evm_grid(
    rows_by_y: list[tuple[float, list[tuple[float, str]]]],
    scale: float = 1.0,
    tjs_probe: Any | None = None,
) -> Rows | None:
    """Structure an EVM summary PDF page: isolate the "توضیحات" column and attach wrapped project names to rows."""
    from app.features.volume_report.extraction.evm_parser import HEADER_WORDS
    from app.features.volume_report.extraction.normalize import normalize_text

    evm_idx: int | None = None
    for idx, (_, row_words) in enumerate(rows_by_y[:20]):
        text = " ".join(w[1] for w in row_words).lower()
        if "cpi" in text and "spi" in text:
            block = " ".join(w[1] for _, rw in rows_by_y[: min(len(rows_by_y), idx + 4)] for w in rw)
            if "قرارداد" in normalize_text(block):
                evm_idx = idx
                break
    if evm_idx is None:
        return None

    notes_r, is_notes_x = _find_evm_notes_filter(rows_by_y, evm_idx, tjs_probe)
    hdr_start = min(evm_idx, notes_r) if notes_r is not None else evm_idx

    def is_header_fragment(text: str) -> bool:
        norm = normalize_text(text)
        return bool(norm) and any(word in norm for word in HEADER_WORDS)

    split_rows: list[tuple[float, str, str | None]] = []
    past_total = False
    for idx, (y_val, row_words) in enumerate(rows_by_y):
        in_table = idx >= hdr_start and not past_total
        if is_notes_x is None or not in_table:
            main_s, note_s = " ".join(w[1] for w in row_words).strip(), None
        else:
            main_w = [w[1] for w in row_words if not is_notes_x(w[0])]
            note_w = [w[1] for w in row_words if is_notes_x(w[0])]
            main_s = " ".join(main_w).strip()
            note_s = " ".join(note_w).strip() or None
        if idx > evm_idx and not past_total and main_s and "جمع" in normalize_text(main_s).split()[:3]:
            past_total = True
        split_rows.append((y_val, main_s, note_s))

    body_start = evm_idx + 1
    while body_start < len(split_rows):
        m_txt = split_rows[body_start][1]
        if m_txt and (_EVM_AMOUNT_RE.search(_to_ascii_digits(m_txt)) or not is_header_fragment(m_txt)):
            break
        body_start += 1

    total_cutoff = len(split_rows)
    for idx in range(body_start, len(split_rows)):
        if "جمع" in normalize_text(split_rows[idx][1]).split()[:3]:
            total_cutoff = idx
            break

    body = split_rows[body_start:total_cutoff]
    head, foot, anchor_set, attached = _attach_wrapped_evm_names(
        [m for _, m, _ in body],
        [y for y, _, _ in body],
        is_header_fragment,
        max(_MAX_EVM_WRAP_PT, _MAX_EVM_WRAP_PT * scale),
    )

    def format_row(main_s: str, note_s: str | None) -> list[Any]:
        if is_notes_x is None:
            return [main_s] if main_s else []
        return [main_s or None, note_s]

    grid: Rows = [format_row(m, n) for _, m, n in split_rows[:body_start]]
    for k, (_, m_txt, n_txt) in enumerate(body):
        if k in attached:
            continue
        if k in anchor_set and (head[k] or foot[k]):
            row_idx, inline, rest = _split_evm_prefix(m_txt)
            merged = " ".join(p for p in (*head[k], inline, *foot[k]) if p).strip()
            m_txt = " ".join(p for p in (row_idx, merged, rest) if p)
        formatted = format_row(m_txt, n_txt)
        if formatted:
            grid.append(formatted)
    grid.extend(format_row(m, n) for _, m, n in split_rows[total_cutoff:])
    return [r for r in grid if any(c not in (None, "") for c in r)]


def extract_pdf_page_grid(page: pypdf.PageObject) -> Rows:
    """Extracts a 2D table grid (Rows = list[list[Any]]) from a PDF page."""
    _repair_page_fonts(page)
    rot = (getattr(page, "rotation", 0) or 0) % 360
    words: list[tuple[float, float, str]] = []
    font_sizes: list[float] = []

    def visitor(text: str, cm: Any, tm: Any, font_dict: Any, font_size: Any) -> None:
        stripped = _clean_word(text)
        if stripped:
            wx, wy = _page_xy(cm, tm, rot)
            words.append((wx, wy, stripped))
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
        # Plain visitor_text can collapse multi-column TJ arrays (e.g. Foxit/Nitro PDFs); try layout spans.
        # On rotated pages, prefer layout spans whenever non-empty because visitor_text reorders RTL substrings.
        if rot == 0:
            evm_grid = _extract_evm_grid(
                rows_by_y,
                scale=scale,
                tjs_probe=lambda: _cluster_tjs_rows(_extract_tjs_spans(page)),
            )
            if evm_grid is not None:
                return evm_grid
        layout_grid = _tjs_grid(page)
        if _has_income_layout(layout_grid) or (rot != 0 and layout_grid):
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
            if col_defs[c_idx]["text"] == "واحد" and text.strip() in {"ریال", "ريال"} and c_idx + 1 < len(col_defs):
                c_idx += 1
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
    """Extract positioned text-show spans in display orientation via pypdf's layout engine."""
    from pypdf._text_extraction._layout_mode._fixed_width_page import recurs_to_target_op
    from pypdf._text_extraction._layout_mode._text_state_manager import TextStateManager
    from pypdf.generic import ContentStream

    if not hasattr(page, "_layout_mode_fonts") or page.get("/Contents") is None:
        return []
    rot = (getattr(page, "rotation", 0) or 0) % 360
    fonts = page._layout_mode_fonts()
    ops = iter(ContentStream(page["/Contents"].get_object(), page.pdf, "bytes").operations)
    state_mgr = TextStateManager()
    spans: list[Any] = []
    for operands, op in ops:
        if op in (b"BT", b"q"):
            _, tjs = recurs_to_target_op(ops, state_mgr, b"ET" if op == b"BT" else b"Q", fonts, strip_rotated=(rot == 0))
            spans.extend(tjs)
        else:
            state_mgr.set_state_param(op, operands)
    if rot == 0:
        return [t for t in spans if not t.rotated and t.txt]

    out: list[Any] = []
    for sp in spans:
        if not sp.txt:
            continue
        if rot in (90, 270) and not sp.rotated:
            continue
        adv = max(0.0, float(sp.displaced_tx) - float(sp.tx))
        ox, oy = float(sp.tx), float(sp.ty)
        if rot == 90:
            sp.tx, sp.ty, sp.displaced_tx = oy, -ox, oy + adv
        elif rot == 270:
            sp.tx, sp.ty, sp.displaced_tx = -oy, ox, -oy + adv
        elif rot == 180:
            sp.tx, sp.ty, sp.displaced_tx = -ox, -oy, -ox + adv
        out.append(sp)
    return out


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


def _has_rtl(text: str) -> bool:
    return bool(_RTL_CHAR_RE.search(text))


def _join_tjs_cells(cells: list[tuple[float, float, str]]) -> str:
    """Join horizontally sorted cells in reading order (RTL when Arabic/Persian script is present)."""
    ordered = reversed(cells) if any(_has_rtl(c[2]) for c in cells) else cells
    return " ".join(c[2] for c in ordered)


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
        tjs_word_rows = [
            (y_val, [(c[0], c[2]) for c in (reversed(cells) if any(_has_rtl(c[2]) for c in cells) else cells)])
            for y_val, cells in rows
        ]
        evm_grid = _extract_evm_grid(tjs_word_rows)
        if evm_grid is not None:
            return evm_grid
        return [[_join_tjs_cells(cells)] for _, cells in rows]

    header_y, header_cells = rows[header_idx]
    n_cols = len(header_cells)
    boundaries = [0.5 * (header_cells[i][1] + header_cells[i + 1][0]) for i in range(n_cols - 1)]
    prefix_rows = [[_join_tjs_cells(cells)] for _, cells in rows[:header_idx]]
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
            elif _has_rtl(ctext) or _has_rtl(str(grid_row[col])):
                # `cells` are sorted left-to-right, so the later fragment sits to the right (earlier in RTL reading).
                grid_row[col] = f"{ctext} {grid_row[col]}"
            else:
                grid_row[col] = f"{grid_row[col]} {ctext}"
        body_rows.append(grid_row)
        body_ys.append(y_val)

    if qty_col is not None and unit_col is not None and desc_col is not None:
        body_rows, body_ys = _attach_wrapped_units(body_rows, body_ys, qty_col, unit_col, desc_col)

    if desc_col is not None and qty_col is not None:
        return prefix_rows + [header_row] + _attach_wrapped_tjs_descriptions(body_rows, body_ys, desc_col, qty_col)
    return prefix_rows + [header_row] + _attach_wrapped_descriptions(body_rows, body_ys, header_row)


def _decode_cmap_hex(hex_str: str) -> str:
    padded = hex_str.zfill((len(hex_str) + 3) // 4 * 4) if len(hex_str) > 2 else hex_str.zfill(4)
    return bytes.fromhex(padded).decode("utf-16-be", errors="ignore")


def _read_tounicode_map(font_obj: Any) -> dict[int, str]:
    """Parse existing /ToUnicode CMap bfchar/bfrange entries into `{byte_code: unicode_str}`."""
    tu_ref = font_obj.get("/ToUnicode")
    if tu_ref is None:
        return {}
    try:
        text = tu_ref.get_object().get_data().decode("latin1", errors="ignore")
    except Exception:
        return {}
    mapping: dict[int, str] = {}
    for block in _BF_CHAR_BLOCK_RE.findall(text):
        tokens = _HEX_TOKEN_RE.findall(block)
        for i in range(0, len(tokens) - 1, 2):
            src, dst = int(tokens[i], 16), _decode_cmap_hex(tokens[i + 1])
            if dst:
                mapping[src] = dst
    for block in _BF_RANGE_BLOCK_RE.findall(text):
        for line in block.splitlines():
            tokens = _HEX_TOKEN_RE.findall(line)
            if len(tokens) < 3:
                continue
            start, end = int(tokens[0], 16), int(tokens[1], 16)
            if "[" in line:
                for offset, dst_hex in enumerate(tokens[2 : 2 + end - start + 1]):
                    dst = _decode_cmap_hex(dst_hex)
                    if dst:
                        mapping[start + offset] = dst
            else:
                base = int(tokens[2], 16)
                for offset in range(end - start + 1):
                    mapping[start + offset] = chr(base + offset)
    return mapping


def _parse_ttf_subtable(data: bytes, offset: int) -> dict[int, int]:
    """Decode one TrueType `cmap` subtable (format 0, 4, or 6) into `{char_code: glyph_id}`."""
    fmt = struct.unpack(">H", data[offset : offset + 2])[0]
    mapping: dict[int, int] = {}
    if fmt == 0 and offset + 262 <= len(data):
        for code in range(256):
            gid = data[offset + 6 + code]
            if gid:
                mapping[code] = gid
    elif fmt == 4:
        seg_cnt = struct.unpack(">H", data[offset + 6 : offset + 8])[0] // 2
        end_pos = offset + 14
        start_pos = end_pos + 2 + 2 * seg_cnt
        delta_pos = start_pos + 2 * seg_cnt
        range_pos = delta_pos + 2 * seg_cnt
        ends = struct.unpack(f">{seg_cnt}H", data[end_pos : end_pos + 2 * seg_cnt])
        starts = struct.unpack(f">{seg_cnt}H", data[start_pos : start_pos + 2 * seg_cnt])
        deltas = struct.unpack(f">{seg_cnt}h", data[delta_pos : delta_pos + 2 * seg_cnt])
        ranges = struct.unpack(f">{seg_cnt}H", data[range_pos : range_pos + 2 * seg_cnt])
        for i in range(seg_cnt):
            sc, ec, delta, ro = starts[i], ends[i], deltas[i], ranges[i]
            if sc == 0xFFFF or ec < sc:
                continue
            for code in range(sc, ec + 1):
                if ro == 0:
                    gid = (code + delta) & 0xFFFF
                else:
                    idx_off = range_pos + 2 * i + ro + 2 * (code - sc)
                    if idx_off + 2 > len(data):
                        break
                    gid = struct.unpack(">H", data[idx_off : idx_off + 2])[0]
                    if gid:
                        gid = (gid + delta) & 0xFFFF
                if gid:
                    mapping[code] = gid
    elif fmt == 6:
        first, count = struct.unpack(">HH", data[offset + 6 : offset + 10])
        gids = struct.unpack(f">{count}H", data[offset + 10 : offset + 10 + 2 * count])
        for j, gid in enumerate(gids):
            if gid:
                mapping[first + j] = gid
    return mapping


def _parse_ttf_cmap(data: bytes) -> tuple[int, int, dict[tuple[int, int], dict[int, int]]] | None:
    """Return `(unitsPerEm, numGlyphs, {(platformID, encodingID): {code: gid}})` from an embedded TTF."""
    try:
        if len(data) < 12:
            return None
        num_tables = struct.unpack(">H", data[4:6])[0]
        if len(data) < 12 + num_tables * 16:
            return None
        tables: dict[str, int] = {}
        for i in range(num_tables):
            off = 12 + i * 16
            tag = data[off : off + 4].decode("latin1", errors="ignore")
            tables[tag] = struct.unpack(">I", data[off + 8 : off + 12])[0]
        if not {"head", "maxp", "cmap"}.issubset(tables):
            return None
        upm = struct.unpack(">H", data[tables["head"] + 18 : tables["head"] + 20])[0]
        ng = struct.unpack(">H", data[tables["maxp"] + 4 : tables["maxp"] + 6])[0]
        coff = tables["cmap"]
        nsub = struct.unpack(">H", data[coff + 2 : coff + 4])[0]
        wanted = {(1, 0), (3, 0)} if (upm == 2048 and ng in _BORN_GLYPH_COUNTS) else {(1, 0), (3, 0), (3, 1)}
        cmaps: dict[tuple[int, int], dict[int, int]] = {}
        for i in range(nsub):
            pid, eid, sub_off = struct.unpack(">HHI", data[coff + 4 + i * 8 : coff + 12 + i * 8])
            if (pid, eid) not in wanted:
                continue
            parsed = _parse_ttf_subtable(data, coff + sub_off)
            if parsed:
                cmaps.setdefault((pid, eid), parsed)
        return upm, ng, cmaps
    except (struct.error, IndexError, ValueError):
        return None


def _normalize_symbol_codes(raw_cmap: dict[int, int]) -> dict[int, int]:
    """Symbol TTFs store byte codes under 0xF000..0xF0FF (Windows Symbol) or 0x00..0xFF."""
    out: dict[int, int] = {}
    for code16, gid in raw_cmap.items():
        code = (code16 & 0xFF) if 0xF000 <= code16 <= 0xF0FF else code16
        if code <= 0xFF:
            out[code] = gid
    return out


def _synthesize_ttf_tounicode(font_obj: Any, base_font: str) -> dict[int, str] | None:
    """Build a complete `{byte_code: unicode}` map for TrueType fonts with missing Persian /ToUnicode entries."""
    fd_ref = font_obj.get("/FontDescriptor")
    if fd_ref is None:
        return None
    fd = fd_ref.get_object()
    ff2 = fd.get("/FontFile2")
    if ff2 is None:
        return None
    encoding = font_obj.get("/Encoding")
    # Clean Excel PDFs embed unused /WinAnsiEncoding helper fonts alongside /Type0 fonts; leave those untouched.
    if encoding == "/WinAnsiEncoding" and "/ToUnicode" not in font_obj:
        return None

    parsed = _parse_ttf_cmap(ff2.get_object().get_data())
    if parsed is None:
        return None
    upm, ng, cmaps = parsed
    existing = _read_tounicode_map(font_obj)

    # Case 1: Bornayekta B-series fonts (e.g. Nitro PDF Pro) with Symbol cmap and partial /ToUnicode.
    if upm == 2048 and ng in _BORN_GLYPH_COUNTS and ((3, 0) in cmaps or (1, 0) in cmaps):
        norm_cmap = _normalize_symbol_codes(cmaps.get((3, 0)) or cmaps[(1, 0)])
        anchor_matches = 0
        for code, u_str in existing.items():
            expected_gid = _BORN_ANCHOR_TO_GID.get(u_str)
            actual_gid = norm_cmap.get(code)
            if expected_gid is not None and actual_gid is not None:
                if actual_gid != expected_gid:
                    return None
                anchor_matches += 1
        confirmed = bool(_BORN_FONT_NAME_RE.search(base_font)) or anchor_matches >= 3 or (
            not existing and encoding is None and (3, 0) in cmaps
        )
        if not confirmed:
            return None
        merged = {k: v for k, v in existing.items() if k <= 0xFF and all(ord(ch) >= 0x20 for ch in v)}
        for code, gid in norm_cmap.items():
            if code not in merged and gid in _BORN_GID_TO_UNICODE:
                merged[code] = _BORN_GID_TO_UNICODE[gid]
        return merged if merged and merged != existing else None

    # Case 2: Generic TTF without /ToUnicode and without WinAnsiEncoding whose embedded File has a Unicode BMP cmap.
    if not existing and (3, 1) in cmaps and ((3, 0) in cmaps or (1, 0) in cmaps):
        gid_to_uni: dict[int, str] = {}
        for u_cp, gid in cmaps[(3, 1)].items():
            if 0xE000 <= u_cp <= 0xF8FF and gid in gid_to_uni:
                continue
            if gid not in gid_to_uni or (0xE000 <= ord(gid_to_uni[gid]) <= 0xF8FF):
                gid_to_uni[gid] = chr(u_cp)
        byte_cmap = _normalize_symbol_codes(cmaps.get((3, 0)) or cmaps[(1, 0)])
        rebuilt = {code: gid_to_uni[gid] for code, gid in byte_cmap.items() if gid in gid_to_uni}
        return rebuilt or None

    return None


def _build_tounicode_stream(mapping: dict[int, str]) -> pypdf.generic.DecodedStreamObject:
    lines = [
        "/CIDInit /ProcSet findresource begin",
        "12 dict begin",
        "begincmap",
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
        "/CMapName /Adobe-Identity-UCS def",
        "/CMapType 2 def",
        "1 begincodespacerange",
        "<00> <FF>",
        "endcodespacerange",
    ]
    items = sorted((k, v) for k, v in mapping.items() if 0 <= k <= 0xFF and v)
    for idx in range(0, len(items), 100):
        chunk = items[idx : idx + 100]
        lines.append(f"{len(chunk)} beginbfchar")
        for code, ch in chunk:
            hex_val = "".join(f"{ord(c):04X}" for c in ch)
            lines.append(f"<{code:02X}> <{hex_val}>")
        lines.append("endbfchar")
    lines.extend(["endcmap", "CMapName currentdict /CMap defineresource pop", "end", "end"])
    stream = pypdf.generic.DecodedStreamObject()
    stream.set_data("\n".join(lines).encode("latin1"))
    return stream


def _repair_page_fonts(page: Any) -> None:
    """Populate missing Persian /ToUnicode entries on embedded /TrueType fonts in-place (once per font)."""
    try:
        resources = page.get("/Resources")
        fonts = resources.get("/Font") if resources else None
        if not fonts:
            return
    except Exception:
        return
    for font_ref in fonts.values():
        try:
            font_obj = font_ref.get_object()
            if font_obj.get("/Subtype") != "/TrueType":
                continue
            repaired = _synthesize_ttf_tounicode(font_obj, str(font_obj.get("/BaseFont", "")))
            if repaired:
                font_obj[pypdf.generic.NameObject("/ToUnicode")] = _build_tounicode_stream(repaired)
        except Exception as exc:
            logger.debug("Skipping font repair on %s: %s", font_ref, exc)


def _detect_pdf_sheet_name(page_num: int, page: pypdf.PageObject) -> str:
    """Inspects the top lines of a page to give the virtual sheet a descriptive title."""
    _repair_page_fonts(page)
    rot = (getattr(page, "rotation", 0) or 0) % 360
    top_texts: list[str] = []

    if rot != 0:
        tjs_rows = _cluster_tjs_rows(_extract_tjs_spans(page))
        if tjs_rows:
            top_texts = [_clean_word(_join_tjs_cells(cells)) for _, cells in tjs_rows[:8]]

    if not top_texts:
        words: list[tuple[float, float, str]] = []

        def visitor(text: str, cm: Any, tm: Any, font_dict: Any, font_size: Any) -> None:
            stripped = _clean_word(text)
            if stripped:
                wx, wy = _page_xy(cm, tm, rot)
                words.append((wx, wy, stripped))

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
            if site:
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
        _repair_page_fonts(page)
        name = _detect_pdf_sheet_name(i, page)
        sheets.append(
            SheetData(
                name=name,
                visibility="visible",
                _loader=lambda p=page: extract_pdf_page_grid(p),
            )
        )
    return WorkbookData(sheets=sheets)

