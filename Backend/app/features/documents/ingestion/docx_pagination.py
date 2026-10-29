"""Page numbers for Word-style documents (.docx and the .doc / .rtf / .odt files converted to it).

A .docx has no pages, only a flow of paragraphs; the page count exists only after a layout engine has run. Taking the whole
body as "page 1" made a 41-page proposal a one-page document: `read_document_pages` could not return pages 2-41 and
citations had no page. Two sources of page boundaries are used, best first:

1. `w:lastRenderedPageBreak` - the marker Word itself writes where it last broke a page, so the numbers match what the
   user sees in Word (`pagination="word"`). Explicit page breaks (`w:br w:type="page"`, `w:pageBreakBefore`) count too.
2. Otherwise (files from LibreOffice / python-docx / Google Docs, or a .doc, whose conversion drops the markers) the
   text is spread over the page count the file declares (`docProps/app.xml`, the .doc summary information, RTF/ODT
   metadata), or over about `_CHARS_PER_PAGE` characters per page, cutting at explicit breaks first
   (`pagination="estimated"`: the right neighbourhood, not the exact page).
"""

import logging
import math
import re
import zipfile
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_RENDERED = "rendered"
_EXPLICIT = "explicit"

_CHARS_PER_PAGE = 1800  # used only when the file does not declare its page count
_SINGLE_PAGE_CHARS = 2200  # shorter text with no breaks stays one page
_MIN_CHARS_PER_PAGE = 300  # bounds for believing a declared page count
_MAX_CHARS_PER_PAGE = 6000


@dataclass
class Block:
    """One paragraph, table row or paragraph fragment, in body order."""

    text: str
    break_before: str | None = None  # "rendered" | "explicit": a new page starts here
    image_rids: list[str] = field(default_factory=list)


def _tag(name: str) -> str:
    return f"{{{_W}}}{name}"


def page_marker_kind(element) -> str | None:
    """`rendered` for Word's own last-render marker, `explicit` for a manual break, else None."""
    if element.tag == _tag("lastRenderedPageBreak"):
        return _RENDERED
    if element.tag == _tag("br") and element.get(_tag("type")) == "page":
        return _EXPLICIT
    return None


def _stronger(a: str | None, b: str | None) -> str | None:
    return _RENDERED if _RENDERED in (a, b) else (a or b)


def image_rids(element) -> list[str]:
    """Relationship ids of the pictures drawn inside `element` (DrawingML blips and legacy VML imagedata)."""
    found = element.xpath(".//*[local-name()='blip']/@*[local-name()='embed']")
    found += element.xpath(".//*[local-name()='imagedata']/@*[local-name()='id']")
    return list(dict.fromkeys(str(r) for r in found))


def paragraph_blocks(p_element, text: str) -> list[Block]:
    """The paragraph as one block, or several if Word broke a page inside it (cut at the marker's position in the text)."""
    props = p_element.find(_tag("pPr"))
    first_break: str | None = None
    if props is not None and props.find(_tag("pageBreakBefore")) is not None:
        first_break = _EXPLICIT

    cuts: list[tuple[int, str]] = []  # (offset in text, kind)
    offset = 0
    for element in p_element.iter():
        if element.tag == _tag("t"):
            offset += len(element.text or "")
            continue
        kind = page_marker_kind(element)
        if kind is not None:
            cuts.append((offset, kind))

    total = len(text)
    segments: list[Block] = []
    start, pending = 0, first_break
    trailing: str | None = None
    for cut_offset, kind in cuts:
        cut = min(max(cut_offset, 0), total)
        if cut >= total:  # a break at the very end: the next block starts the new page
            trailing = _stronger(trailing, kind)
            continue
        if cut <= start:
            pending = _stronger(pending, kind)
            continue
        # snap to a word boundary so a word is never split between two pages
        snapped = text.rfind(" ", start, cut)
        cut = snapped + 1 if snapped > start else cut
        segments.append(Block(text=text[start:cut].strip(), break_before=pending))
        start, pending = cut, kind
    segments.append(Block(text=text[start:].strip(), break_before=pending))
    segments = [s for s in segments if s.text] or [Block(text=text, break_before=first_break)]
    segments[0].image_rids = image_rids(p_element)
    if trailing is not None:
        segments.append(Block(text="", break_before=trailing))  # carries the pending break to the next block
    return segments


def _split_by_breaks(blocks: list[Block]) -> list[list[Block]]:
    pages: list[list[Block]] = [[]]
    carry: str | None = None
    for block in blocks:
        brk = _stronger(carry, block.break_before)
        if not block.text:  # a pure break carrier, or a picture-only paragraph (kept so its image lands on this page)
            carry = brk
            if block.image_rids:
                pages[-1].append(block)
            continue
        carry = None
        if brk and pages[-1]:
            pages.append([])
        pages[-1].append(block)
    return [p for p in pages if p]


def paginate(blocks: list[Block], page_hint: int | None) -> tuple[list[list[Block]], str]:
    """Blocks grouped into pages, and how trustworthy the numbering is (`word` | `estimated`)."""
    if any(b.break_before == _RENDERED for b in blocks):
        return _split_by_breaks(blocks), "word"

    segments = _split_by_breaks(blocks)  # only explicit breaks are left
    total = sum(len(b.text) for seg in segments for b in seg)
    if total == 0:
        return [], "estimated"
    if len(segments) == 1 and total <= _SINGLE_PAGE_CHARS and not (page_hint and page_hint > 1):
        return segments, "estimated"

    # A declared count is trusted only if it fits the amount of text: generators stamp a fixed "Pages=1" on any file.
    plausible = bool(page_hint) and _MIN_CHARS_PER_PAGE <= total / page_hint <= _MAX_CHARS_PER_PAGE
    wanted = page_hint if plausible else max(1, math.ceil(total / _CHARS_PER_PAGE))
    per_page = total / wanted
    pages: list[list[Block]] = []
    for seg in segments:
        seg_chars = sum(len(b.text) for b in seg)
        pages.extend(_greedy_split(seg, max(1, round(seg_chars / per_page))))
    return pages, "estimated"


def _greedy_split(seg: list[Block], count: int) -> list[list[Block]]:
    """Cuts `seg` into `count` consecutive groups of roughly equal text length (a block is never split)."""
    if count <= 1:
        return [seg]
    total = sum(len(b.text) for b in seg)
    groups: list[list[Block]] = [[]]
    done = 0
    for block in seg:
        groups[-1].append(block)
        done += len(block.text)
        if len(groups) < count and done >= total * len(groups) / count:
            groups.append([])
    return [g for g in groups if g]


# ---------------------------------------------------------------------------
# Page counts the file declares about itself
# ---------------------------------------------------------------------------


def docx_declared_pages(file_path: str) -> int | None:
    """`<Pages>` from docProps/app.xml (what Word counted when it last saved)."""
    try:
        with zipfile.ZipFile(file_path) as archive:
            app = archive.read("docProps/app.xml").decode("utf-8", errors="ignore")
        match = re.search(r"<Pages>(\d+)</Pages>", app)
        return int(match.group(1)) if match else None
    except Exception:
        return None


def legacy_declared_pages(file_path: str, suffix: str) -> int | None:
    """Page count stored in a .doc (OLE summary info), .rtf (`\\nofpages`) or .odt (meta.xml)."""
    try:
        if suffix == ".doc":
            import olefile

            with olefile.OleFileIO(file_path) as ole:
                return ole.get_metadata().num_pages or None
        if suffix == ".rtf":
            with open(file_path, "rb") as handle:
                match = re.search(rb"\\nofpages(\d+)", handle.read(8192))
            return int(match.group(1)) if match else None
        if suffix == ".odt":
            with zipfile.ZipFile(file_path) as archive:
                meta = archive.read("meta.xml").decode("utf-8", errors="ignore")
            match = re.search(r'page-count="(\d+)"', meta)
            return int(match.group(1)) if match else None
    except Exception as exc:
        logger.debug("No declared page count for %s: %s", file_path, exc)
    return None
