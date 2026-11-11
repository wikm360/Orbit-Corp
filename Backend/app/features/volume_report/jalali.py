"""Minimal Jalali calendar helpers (no dependency). Years 1300-1500 follow the 33-year leap rule, which matches the
official calendar in that range. Used to turn "پیش بینی آبان" into the date range of that month."""

from datetime import date, timedelta

MONTHS = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
_ANCHOR_YEAR, _ANCHOR_DATE = 1405, date(2026, 3, 21)  # 1405/01/01


def is_leap(jy: int) -> bool:
    return (25 * jy + 11) % 33 < 8  # Esfand has 30 days


def month_length(jy: int, month: int) -> int:
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    return 30 if is_leap(jy) else 29


def new_year(jy: int) -> date:
    """Gregorian date of 1 Farvardin of `jy`."""
    current, day = _ANCHOR_YEAR, _ANCHOR_DATE
    while current < jy:
        day += timedelta(days=366 if is_leap(current) else 365)
        current += 1
    while current > jy:
        current -= 1
        day -= timedelta(days=366 if is_leap(current) else 365)
    return day


def to_gregorian(jy: int, month: int, day: int) -> date:
    offset = sum(month_length(jy, m) for m in range(1, month)) + day - 1
    return new_year(jy) + timedelta(days=offset)


def to_jalali(value: date) -> tuple[int, int, int]:
    jy = _ANCHOR_YEAR + (value - _ANCHOR_DATE).days // 366
    while new_year(jy + 1) <= value:
        jy += 1
    while new_year(jy) > value:
        jy -= 1
    days = (value - new_year(jy)).days
    for month in range(1, 13):
        length = month_length(jy, month)
        if days < length:
            return jy, month, days + 1
        days -= length
    raise ValueError("unreachable")


def month_range(jy: int, month: int) -> tuple[date, date]:
    return to_gregorian(jy, month, 1), to_gregorian(jy, month, month_length(jy, month))


def nearest_month_range(month: int, reference: date) -> tuple[date, date]:
    """The occurrence of `month` (1..12) closest to `reference` (a forecast is for the month around the report period)."""
    ref_year = to_jalali(reference)[0]
    candidates = [month_range(year, month) for year in (ref_year - 1, ref_year, ref_year + 1)]
    return min(candidates, key=lambda r: abs((r[0] + (r[1] - r[0]) / 2 - reference).days))
