"""Monthly PV plan: one row per project with the month's planned work value ("کارکرد ماهانه طبق برنامه‌ی کارگاه (PV)").

It is the "PVF" sheet of the company-wide EVM workbook ("درآمد برنامه ای پروژه‌های … در ماه آبان") or any sheet with the same
shape: a header with «نام پروژه» and a PV column, one project per row. The week's PV is the share of this amount that falls on the
days of the period (see service.plan_factor). Pure (no DB)."""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.features.volume_report.extraction.normalize import normalize_text
from app.features.volume_report.extraction.workbook import open_workbook
from app.features.volume_report.jalali import MONTHS

_HEADER_SCAN_ROWS = 12
_TOTAL_WORDS = ("جمع",)


@dataclass
class PvPlanRow:
    row_no: int
    project_name: str
    pv_month: Decimal


@dataclass
class ParsedPvPlan:
    sheet_name: str
    month: int | None = None  # Jalali month named by the title
    rows: list[PvPlanRow] = field(default_factory=list)


def _number(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = re.sub(r"[٠-٩۰-۹]", lambda m: str(ord(m.group()) & 0xF), str(value)).replace("،", ",").replace(",", "").strip()
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _find_columns(rows: list[list[Any]]) -> tuple[int, int, int] | None:
    """(header row index, name column, PV column). The PV column is the first one labelled PV that is not "PV ماه پیش"."""
    for index, row in enumerate(rows[:_HEADER_SCAN_ROWS]):
        labels = [normalize_text(c) if isinstance(c, str) else "" for c in row]
        if any("cpi" in label or "spi" in label for label in labels):
            return None  # an EVM summary, not a PV plan
        name = next((i for i, label in enumerate(labels) if label == "نام پروژه"), None)
        pv = next((i for i, label in enumerate(labels) if re.search(r"\bpv\b", label) and "ماه پیش" not in label and "قبل" not in label), None)
        if name is not None and pv is not None:
            return index, name, pv
    return None


def _month_of_title(rows: list[list[Any]]) -> int | None:
    text = normalize_text(" ".join(str(c) for row in rows[:4] for c in row if isinstance(c, str) and ("ماه" in c or "برنامه" in c or "پیش" in c)))
    words = text.split()
    found = [index + 1 for index, name in enumerate(MONTHS) if normalize_text(name) in words]
    return found[0] if len(set(found)) == 1 else None


def parse_pv_plan(sheet_name: str, rows: list[list[Any]]) -> ParsedPvPlan | None:
    columns = _find_columns(rows)
    if columns is None:
        return None
    header, name_col, pv_col = columns
    parsed = ParsedPvPlan(sheet_name=sheet_name, month=_month_of_title(rows[:header]))
    for offset, row in enumerate(rows[header + 1:], start=header + 2):
        name = row[name_col] if name_col < len(row) else None
        if isinstance(name, str) and normalize_text(name).startswith(_TOTAL_WORDS):
            break
        first = row[0] if row else None
        if isinstance(first, str) and normalize_text(first).startswith(_TOTAL_WORDS):
            break
        pv = _number(row[pv_col]) if pv_col < len(row) else None
        if isinstance(name, str) and name.strip() and pv is not None and pv >= 0:
            parsed.rows.append(PvPlanRow(row_no=offset, project_name=re.sub(r"\s+", " ", name).strip(), pv_month=pv.quantize(Decimal("0.01"))))
    return parsed if parsed.rows else None


def detect_pv_plan(path: str) -> ParsedPvPlan | None:
    """First visible sheet of the file that is a PV plan (blocking: run in a thread)."""
    with open_workbook(path) as workbook:
        for sheet in workbook.sheets:
            if sheet.is_hidden:
                continue
            parsed = parse_pv_plan(sheet.name, sheet.rows())
            if parsed is not None:
                return parsed
    return None
