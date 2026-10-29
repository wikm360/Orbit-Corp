"""Quality checks (and a cheap repair) for the text layer extracted from PDF pages.

Two real-world failure modes were found on company PDFs:

1. **Visual-order Persian** (typical of "Machine Translated by Google" / print-to-PDF files): the text layer holds Arabic
   *presentation forms* (U+FB50-FDFF, U+FE70-FEFF), the letters of every word reversed, and spurious spaces inside words.
   Extracted as is, it shares no words with the real text (0 % word overlap measured), so neither embeddings nor full-text
   search can find anything.
2. **Garbled layer**: a scanned page whose old OCR layer is symbol noise (`~ m -· . "" .;.,..-`).

`assess_text_layer` classifies a page; `fix_visual_persian` repairs (1) deterministically. The repair is only a fallback:
measured against the real text of a document that exists as both PDF and DOCX it recovers ~70 % of the words, while
vision OCR of the rendered page recovers ~93-95 %, so the ingestion pipeline prefers OCR for flagged pages.
"""

import re
import unicodedata

TEXT_OK = "ok"
TEXT_VISUAL_PERSIAN = "visual_persian"
TEXT_GARBLED = "garbled"

_ARABIC_LETTER = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_PRESENTATION_FORM = re.compile(r"[ﭐ-﷿ﹰ-﻿]")
_LTR_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-\./:_,%+()=]*")
_NOISE = frozenset("~·•`'^|\\_=;\"<>*#@$&?{}[]!:/")
_GLYPH_TOKEN = re.compile(r"^/[a-zA-Z]?\d+$")
_CONTROL_CHAR = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

_MIN_ARABIC_LETTERS = 20
_VISUAL_RATIO = 0.15
_MIN_GARBLED_CHARS = 40
_LEGACY_ANSI_SYMBOLS = frozenset("{}|[]«»§¶\\")



def assess_text_layer(text: str) -> str:
    """`TEXT_VISUAL_PERSIAN`, `TEXT_GARBLED`, or `TEXT_OK` for one page's extracted text."""
    compact = re.sub(r"\s", "", text or "")
    if not compact:
        return TEXT_OK

    arabic = len(_ARABIC_LETTER.findall(compact))
    if arabic >= _MIN_ARABIC_LETTERS and len(_PRESENTATION_FORM.findall(compact)) / arabic >= _VISUAL_RATIO:
        return TEXT_VISUAL_PERSIAN

    tokens = text.split()

    # 1. Unmapped font glyph index tokens (e.g. /i255, /0, /1 typical of Windows Distiller PDFs without ToUnicode CMap)
    glyph_tokens = sum(1 for tok in tokens if _GLYPH_TOKEN.match(tok))
    if (len(tokens) >= 5 and glyph_tokens / len(tokens) >= 0.20) or (len(tokens) < 5 and glyph_tokens >= 1):
        return TEXT_GARBLED

    # 2. Control characters or unmapped raw bytes
    ctrl_count = len(_CONTROL_CHAR.findall(text))
    if ctrl_count >= 10 or (len(compact) >= 40 and ctrl_count / len(compact) >= 0.05):
        return TEXT_GARBLED

    # 3. Legacy non-Unicode Persian encoding (Zarnegar / IranSystem / ANSI-mapped Persian fonts like Parwin/Shitab/Maryam)
    # where Persian letters are mapped to Latin Extended (0x80-0x024F) or symbols ({, }, |, etc.) without Arabic Unicode.
    if len(compact) >= 30 and (arabic / len(compact) < 0.15):
        legacy_count = sum(1 for c in compact if (0x80 <= ord(c) <= 0x024F) or c in _LEGACY_ANSI_SYMBOLS)
        if legacy_count / len(compact) >= 0.18:
            return TEXT_GARBLED

    # 4. High noise / low wordlike ratio (residual OCR garbage, symbols)
    if len(compact) >= _MIN_GARBLED_CHARS:
        wordlike = sum(1 for t in tokens if sum(c.isalpha() for c in t) >= 3) / max(1, len(tokens))
        noise = sum(c in _NOISE for c in compact) / len(compact)
        if wordlike < 0.15 and noise >= 0.10:
            return TEXT_GARBLED
    return TEXT_OK


def _joining_form(char: str) -> str | None:
    decomposition = unicodedata.decomposition(char)
    for form in ("initial", "medial", "final", "isolated"):
        if decomposition.startswith(f"<{form}>"):
            return form
    return None


def fix_visual_persian(text: str) -> str:
    """Best-effort conversion of a visual-order presentation-form line to logical-order Persian.

    Per line: glue chunks that the font split inside one word (a space between two glyphs that must connect), reverse the
    letters of each word, NFKC-fold the presentation forms to plain letters, and put Latin/digit runs back in reading order.
    Word order across the line is already logical in these files. Words that were glued without any space stay glued.
    """
    return "\n".join(_fix_line(line) for line in text.split("\n"))


def _fix_line(line: str) -> str:
    merged: list[str] = []
    for token in line.split(" "):
        if not token:
            continue
        if merged:
            previous = merged[-1]
            # In logical order token[0] is followed by previous[-1]: they belong to one word when the first must connect
            # forward (initial/medial) or the second must connect backward (medial/final).
            if _joining_form(token[0]) in ("initial", "medial") or _joining_form(previous[-1]) in ("medial", "final"):
                merged[-1] = previous + token
                continue
        merged.append(token)

    words = [unicodedata.normalize("NFKC", word[::-1]) for word in merged]
    fixed = " ".join(_LTR_RUN.sub(lambda m: m.group()[::-1], word) for word in words)
    fixed = re.sub(r"([A-Za-z0-9])([؀-ۿ])", r"\1 \2", fixed)
    return re.sub(r"([؀-ۿ])([A-Za-z0-9])", r"\1 \2", fixed)
