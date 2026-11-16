"""Sheet discovery: which sheets of a workbook are income sheets we may read, and why the others are skipped."""

import re
from dataclasses import dataclass

from app.features.volume_report.extraction.normalize import normalize_text
from app.features.volume_report.extraction.workbook import SheetData, WorkbookData

_INCOME_WORDS = ("درآمد", "درامد")
_PLAN_WORDS = ("برنامه", "پیش بینی", "پیش‌بینی", "pishbini", "pish bini", "forecast")
_COMPANY_PATTERN = re.compile(r"شرکت\s+(?:[^\s،,:;()\d]+\s*){1,5}")
_COMPANY_SCAN_ROWS = 12
_COMPANY_SCAN_COLS = 12


@dataclass(frozen=True)
class SheetProbe:
    sheet: str
    visibility: str
    kind: str  # income | planned (income-layout forecast, read) | expense | summary | other | hidden
    used: bool
    reason: str | None


def classify_sheet(sheet: SheetData) -> SheetProbe:
    name = normalize_text(sheet.name)
    if sheet.is_hidden:
        return SheetProbe(sheet.name, sheet.visibility, "hidden", False, "hidden")
    # A plan ("برنامه" / "پیش بینی") is never actuals. An income-layout plan sheet (its name still says "درآمد") is read as
    # the forecast for the next period; any other plan sheet (e.g. the EVM summary "پیش بینی") is not a quantity table.
    if any(word in name for word in _PLAN_WORDS):
        if any(word in name for word in _INCOME_WORDS):
            return SheetProbe(sheet.name, sheet.visibility, "planned", True, None)
        return SheetProbe(sheet.name, sheet.visibility, "planned", False, "planned_sheet")
    if "هزینه" in name:
        return SheetProbe(sheet.name, sheet.visibility, "expense", False, "expense_sheet")
    if any(word in name for word in _INCOME_WORDS):
        return SheetProbe(sheet.name, sheet.visibility, "income", True, None)
    return SheetProbe(sheet.name, sheet.visibility, "other", False, "not_income_sheet")


def probe_workbook(workbook: WorkbookData) -> list[SheetProbe]:
    return [classify_sheet(sheet) for sheet in workbook.sheets]


def _company_in(sheet: SheetData, strict: bool = False) -> str | None:
    """strict (income / expense pages): only a title cell that BEGINS with "شرکت" in the first rows; a contractor listed in a
    cost table ("شرکت عمران پویش سیرجان") is not the report's company."""
    for row in sheet.rows()[: 3 if strict else _COMPANY_SCAN_ROWS]:
        for cell in row[:_COMPANY_SCAN_COLS]:
            if not isinstance(cell, str):
                continue
            text = normalize_text(cell)
            if strict and not text.startswith("شرکت"):
                continue
            match = _COMPANY_PATTERN.search(text)
            if match:
                return match.group().strip()
    return None


def suggest_company(workbook: WorkbookData, probes: list[SheetProbe]) -> str | None:
    """Looks for "شرکت …" near the top of the visible non-income (summary) sheets; failing that, of any visible sheet (a forecast
    PDF has only income pages, each headed with the company). A wizard suggestion only."""
    for sheet, probe in zip(workbook.sheets, probes):
        if probe.kind == "other" and (found := _company_in(sheet)):
            return found
    for sheet, probe in zip(workbook.sheets, probes):
        if probe.kind != "other" and not sheet.is_hidden and (found := _company_in(sheet, strict=True)):
            return found
    return None
