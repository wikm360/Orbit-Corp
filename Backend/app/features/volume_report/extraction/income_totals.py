"""Totals block at the bottom of an income sheet (label-anchored, so it does not depend on the table layout):

    جمع صورت وضعیت بدون اعمال ضرایب · جمع صورت وضعیت با اعمال ضرایب · جمع تعدیل · جمع کل درآمد · جمع صورت وضعیت تجمعی

Pure (no DB). Several labels can share one flattened PDF row and the value may be glued to the label, so the text of the whole
sheet is scanned once: each label owns the first number between its end and the next label.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.features.volume_report.extraction.normalize import normalize_text

_LABELS: tuple[tuple[str, str], ...] = (  # longest first: a prefix must never shadow its longer sibling
    ("جمع صورت وضعیت تجمعی", "cumulative"),
    ("جمع صورت وضعیت بدون اعمال ضرایب", "statement_base"),
    ("جمع صورت وضعیت با اعمال ضرایب", "statement_coef"),
    ("جمع کل درآمد با کسر", "_net"),
    ("جمع کل درآمد از ابتدای", "_ytd"),
    ("جمع کل درآمد", "income_total"),
    ("جمع تعدیل", "adjustment"),
    ("مقایسه درآمد و هزینه", "_stop"),  # the profit block follows: its numbers are not part of any label above
)
def _loose(label: str) -> str:
    """Letters may come out of a PDF separated by spaces ("جمع ک ل درآمد"): allow optional whitespace between characters."""
    return r"\s*".join(re.escape(ch) for ch in label.replace(" ", ""))


_LABEL_RE = re.compile("|".join(_loose(label) for label, _ in _LABELS))
_LABEL_KEYS = {re.sub(r"\s+", "", label): key for label, key in _LABELS}
_NUMBER = re.compile(r"-?\d{1,3}(?:,\d{3})+|-?\d+")


@dataclass
class IncomeTotals:
    statement_base: Decimal | None = None
    statement_coef: Decimal | None = None
    adjustment: Decimal | None = None
    income_total: Decimal | None = None
    cumulative: Decimal | None = None

    def found(self) -> bool:
        return self.income_total is not None


def _clean_row(row: list[Any]) -> str:
    raw = " ".join(str(c) for c in row if c is not None)
    # Some PDFs (Arabic-Indic digits + "،") come out in visual order, i.e. every number reversed: "٣٣٤،٠٧٠،٠٦٩،٤٢" is 24,960,070,433.
    raw = re.sub(r"[٠-٩،٬]{3,}", lambda m: m.group()[::-1], raw)
    raw = raw.replace("،", ",").replace("٬", ",")
    raw = re.sub(r"[۰-۹]", lambda m: str(ord(m.group()) - 0x06F0), raw)
    raw = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), raw)
    raw = re.sub(r"(?<=\d)\s*,\s*(?=\d)", ",", raw)
    raw = re.sub(r"[()]", " ", raw)
    raw = raw.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    return re.sub(r"\s+", " ", re.sub(r"(?<![\d,])ریال(?![\d,])", " ", raw))


def _row_values(raw: str) -> list[tuple[str, Decimal | None]]:
    """(key, number) per label of one row. The two RTL layouts of the same sheet are told apart by what comes first: a row that
    starts with a number reads "number label number label" (the number belongs to the label after it), otherwise the number
    follows its label ("label number label number", or a prefix like "مطالبات … 0" before the first label)."""
    matches = list(_LABEL_RE.finditer(raw))
    if not matches:
        return []
    before = _starts_with_number(raw)
    out: list[tuple[str, Decimal | None]] = []
    for index, match in enumerate(matches):
        key = _LABEL_KEYS[re.sub(r"\s+", "", match.group())]
        if before:
            start = matches[index - 1].end() if index else 0
            found = _NUMBER.findall(raw[start:match.start()])
            number = found[-1] if found else None
        else:
            end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
            found = _NUMBER.findall(raw[match.end():end])
            number = found[0] if found else None
        out.append((key, Decimal(number.replace(",", "")) if number else None))
    return out


def parse_income_totals(rows: list[list[Any]]) -> IncomeTotals | None:
    """None when the sheet has no "جمع کل درآمد" (not an income summary at all)."""
    cleaned = [_clean_row(row) for row in rows]
    values: dict[str, Decimal] = {}
    for index, raw in enumerate(cleaned):
        pairs = _row_values(raw)
        for position, (key, number) in enumerate(pairs):
            if number is None and position == len(pairs) - 1 and index + 1 < len(cleaned):
                # "label" at the end of one row, its number opening the next (after-layout only)
                nxt = _NUMBER.search(cleaned[index + 1])
                label = _LABEL_RE.search(cleaned[index + 1])
                if nxt and (label is None or nxt.start() < label.start()) and not _starts_with_number(raw):
                    number = Decimal(nxt.group().replace(",", ""))
            if key.startswith("_") or number is None or key in values:
                continue
            values[key] = number
    totals = IncomeTotals()
    for key, value in values.items():
        setattr(totals, key, value)
    return totals if totals.found() else None


def _starts_with_number(raw: str) -> bool:
    return bool(re.match(r"\s*-?\d", raw))


def detect_basis(sheet_name: str, rows: list[list[Any]], file_name: str | None) -> str:
    """planned = a forecast ("پیش بینی" in the file name, the sheet name or the title lines, or a "برنامه درآمد" sheet)."""
    title = normalize_text(" ".join(str(c) for r in rows[:4] for c in r if c is not None))
    names = normalize_text(f"{sheet_name} {file_name or ''}")
    if "پیش بینی" in title or "پیش بینی" in names or ("برنامه" in names and "درآمد" in names):
        return "planned"
    return "actual"
