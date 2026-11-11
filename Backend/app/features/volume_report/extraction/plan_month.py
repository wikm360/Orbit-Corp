"""Is this file a monthly forecast ("پیش بینی آبان ماه"), and for which month? Title lines only; a weekly forecast carries a date
range ("1405/08/18 الی 1405/08/24") or the word "هفته" and is never taken for a monthly one. Pure (no DB)."""

import re
from collections import Counter
from typing import Any

from app.features.volume_report.extraction.normalize import normalize_text
from app.features.volume_report.extraction.workbook import open_workbook
from app.features.volume_report.jalali import MONTHS

_DATE = re.compile(r"\d{2,4}\s*[/\-.]\s*\d{1,2}\s*[/\-.]\s*\d{1,4}")
_DAY_RANGE = re.compile(r"\d{1,2}\s*(?:-|–|تا|الی|لی)\s*\d{1,2}")  # "18-24 آبان", "از 18 الی 24"
_TITLE_ROWS = 4


def _raw_title(rows: list[list[Any]]) -> str:
    """Only the title cells ("گزارش …" / "… پیش بینی …"); other cells of the first rows hold codes such as "22-645"."""
    cells = [str(c) for row in rows[:_TITLE_ROWS] for c in row if isinstance(c, str)]
    return " ".join(c for c in cells if "گزارش" in normalize_text(c) or "پیش بینی" in normalize_text(c))


def _title(rows: list[list[Any]]) -> str:
    return normalize_text(_raw_title(rows))


def is_period_title(rows: list[list[Any]]) -> bool:
    """A title that names a date range or a week: a forecast for one period, not for a month."""
    raw, text = _raw_title(rows), _title(rows)
    return bool(_DATE.search(raw) or _DAY_RANGE.search(raw) or "هفته" in text or "هفتگی" in text)


def month_in_title(rows: list[list[Any]]) -> int | None:
    """1..12 when the title says "پیش بینی" + exactly one month name and gives no date range / week; else None."""
    text = _title(rows)
    if "پیش بینی" not in text or is_period_title(rows):
        return None
    words = text.split()
    found = [index + 1 for index, name in enumerate(MONTHS) if normalize_text(name) in words]
    return found[0] if len(found) == 1 else None


def detect_plan_month(path: str) -> int | None:
    """The month named by the visible sheets' titles; None when any sheet looks like a one-period forecast or the sheets
    disagree (blocking: run in a thread)."""
    with open_workbook(path) as workbook:
        titles = [sheet.rows() for sheet in workbook.sheets if not sheet.is_hidden]
    if any(is_period_title(rows) for rows in titles):
        return None
    votes = Counter(m for rows in titles if (m := month_in_title(rows)) is not None)
    return votes.most_common(1)[0][0] if len(votes) == 1 else None
