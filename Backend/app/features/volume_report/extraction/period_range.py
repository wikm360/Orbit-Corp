"""The period a sheet's title talks about: "از 1405/08/18 الی 1405/08/24" or "(18 - 24 آبان ماه)". Pure (no DB)."""

import re
from dataclasses import dataclass
from datetime import date

from app.features.volume_report.jalali import MONTHS, month_length, nearest_month_range, to_gregorian

_FULL = re.compile(r"(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})\s*(?:الی|تا|-|–)\s*(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})")
_SHORT = re.compile(r"(\d{1,2})\s*(?:الی|تا|-|–)\s*(\d{1,2})\s*(" + "|".join(MONTHS) + r")")
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


@dataclass(frozen=True)
class PeriodRange:
    year: int | None  # Jalali; None when the title does not say
    month: int
    first_day: int
    last_day: int
    end_month: int | None = None  # only for a full date range that crosses a month


def find_period_range(text: str) -> PeriodRange | None:
    text = text.translate(_DIGITS)
    full = _FULL.search(text)
    if full:
        y1, m1, d1, y2, m2, d2 = (int(g) for g in full.groups())
        return PeriodRange(y1, m1, d1, d2, end_month=m2 if (m2, y2) != (m1, y1) else None)
    short = _SHORT.search(text)
    if short:
        return PeriodRange(None, MONTHS.index(short.group(3)) + 1, int(short.group(1)), int(short.group(2)))
    return None


def resolve_period(period: PeriodRange, reference: date) -> tuple[date, date] | None:
    """Gregorian (start, end). A title without a year takes the occurrence of its month closest to `reference`."""
    try:
        if period.year is not None:
            start = to_gregorian(period.year, period.month, period.first_day)
            end = to_gregorian(period.year, period.end_month or period.month, period.last_day)
        else:
            month_start, _ = nearest_month_range(period.month, reference)
            year = _jalali_year_of(month_start)
            start, end = to_gregorian(year, period.month, period.first_day), to_gregorian(year, period.month, period.last_day)
    except ValueError:
        return None
    if end < start or (end - start).days > 40 or period.first_day > month_length(period.year or _jalali_year_of(reference), period.month):
        return None
    return start, end


def _jalali_year_of(value: date) -> int:
    from app.features.volume_report.jalali import to_jalali

    return to_jalali(value)[0]
