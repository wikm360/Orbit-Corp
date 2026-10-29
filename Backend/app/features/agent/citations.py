"""Sources shown under an answer: the model names the documents/pages it used in a trailing `<sources>` block, the server
checks each against what the tools really returned this turn, and only those reach the client and the stored message."""
import re

from app.features.agent.schemas import SourceCitation

SOURCES_OPEN = "<sources>"
SOURCES_CLOSE = "</sources>"
MAX_DECLARED = 6
FALLBACK_COUNT = 3


class SourcesTagFilter:
    """Splits a streamed answer into the visible text and the `<sources>` block, without ever emitting the tag.

    `feed` returns the part of each delta that is safe to show: text that could still turn out to be the start of the
    tag is held back until the next delta decides it."""

    def __init__(self) -> None:
        self.visible = ""
        self.block = ""
        self._held = ""
        self._in_block = False

    def feed(self, delta: str) -> str:
        if self._in_block:
            self.block += delta
            return ""
        text = self._held + delta
        self._held = ""
        start = text.find(SOURCES_OPEN)
        if start >= 0:
            self._in_block = True
            self.block += text[start + len(SOURCES_OPEN) :]
            return self._emit(text[:start])
        keep = _partial_tag_suffix(text)
        if keep:
            self._held = text[-keep:]
            text = text[:-keep]
        return self._emit(text)

    def finish(self) -> str:
        """Releases text that was only held in case it started the tag (it never did)."""
        held, self._held = self._held, ""
        return self._emit(held)

    def _emit(self, text: str) -> str:
        self.visible += text
        return text


def _partial_tag_suffix(text: str) -> int:
    for size in range(min(len(SOURCES_OPEN) - 1, len(text)), 0, -1):
        if SOURCES_OPEN.startswith(text[-size:]):
            return size
    return 0


def parse_declared(block: str) -> list[tuple[str, int | None]]:
    """`(file name, page or None)` pairs from 'a.pdf|12; b.pdf|3; c.xlsx'."""
    body = block.split(SOURCES_CLOSE, 1)[0]
    declared: list[tuple[str, int | None]] = []
    for item in re.split(r"[;\n]+", body):
        name, _, page = item.strip().partition("|")
        name = name.strip().strip("-•* ").strip()
        if not name:
            continue
        digits = re.search(r"\d+", page.translate(_DIGITS))
        declared.append((name, int(digits.group()) if digits else None))
    return declared[:MAX_DECLARED]


_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _same_file(declared: str, filename: str) -> bool:
    declared, filename = declared.lstrip("@").lower(), filename.lower()
    return declared == filename or declared.endswith("/" + filename)


def _covers(citation: SourceCitation, page: int) -> bool:
    if citation.page is None:
        return True  # not paged (e.g. a spreadsheet): the file as a whole
    return citation.page <= page <= (citation.page_end or citation.page)


def select_citations(collected: list[SourceCitation], block: str) -> list[SourceCitation]:
    """The citations to show: what the model declared and the tools really returned; if it declared nothing usable, the
    best few distinct pages of this turn."""
    chosen: list[SourceCitation] = []
    for name, page in parse_declared(block):
        candidates = [c for c in collected if _same_file(name, c.document_filename)]
        if page is not None:
            candidates = [c for c in candidates if _covers(c, page)]
        if not candidates:
            continue
        exact = [c for c in candidates if page is not None and c.page == page]
        best = max(exact or candidates, key=lambda c: c.score)
        if page is not None and best.page != page:
            best = best.model_copy(update={"page": page, "page_end": None})
        chosen.append(best)
    return _distinct(chosen) or fallback_citations(collected)


def fallback_citations(collected: list[SourceCitation]) -> list[SourceCitation]:
    return _distinct(sorted(collected, key=lambda c: c.score, reverse=True))[:FALLBACK_COUNT]


def _distinct(citations: list[SourceCitation]) -> list[SourceCitation]:
    seen: set = set()
    kept: list[SourceCitation] = []
    for c in citations:
        key = (c.document_id, c.page)
        if key not in seen:
            seen.add(key)
            kept.append(c)
    return kept


def sources_line(sources: list[dict]) -> str:
    """One line for the history replay of a stored answer: which documents/pages it came from."""
    try:
        citations = [SourceCitation(**s) for s in sources]
    except (TypeError, ValueError):
        return ""
    if len(citations) > MAX_DECLARED:  # an older message that stored every tool hit
        citations = fallback_citations(citations)
    labels = [f"{c.document_filename} (صفحه {c.page})" if c.page else c.document_filename for c in _distinct(citations)]
    return "[منابع این پاسخ: " + "، ".join(labels) + "]" if labels else ""
