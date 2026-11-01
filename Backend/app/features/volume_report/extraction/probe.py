"""Sheet discovery: which sheets of a workbook are income sheets we may read, and why the others are skipped."""

import re
from dataclasses import dataclass

from app.features.volume_report.extraction.normalize import normalize_text
from app.features.volume_report.extraction.workbook import SheetData, WorkbookData

_INCOME_WORDS = ("درآمد", "درامد")
_COMPANY_PATTERN = re.compile(r"شرکت\s+(?:[^\s،,:;()\d]+\s*){1,5}")
_COMPANY_SCAN_ROWS = 12
_COMPANY_SCAN_COLS = 12


@dataclass(frozen=True)
class SheetProbe:
    sheet: str
    visibility: str
    kind: str  # income | planned | expense | summary | other | hidden
    used: bool
    reason: str | None


def classify_sheet(sheet: SheetData) -> SheetProbe:
    name = normalize_text(sheet.name)
    if sheet.is_hidden:
        return SheetProbe(sheet.name, sheet.visibility, "hidden", False, "hidden")
    # Any "برنامه" sheet is a plan, not actuals -- also when the word "درآمد" is missing from its name.
    if "برنامه" in name:
        return SheetProbe(sheet.name, sheet.visibility, "planned", False, "planned_sheet")
    if "هزینه" in name:
        return SheetProbe(sheet.name, sheet.visibility, "expense", False, "expense_sheet")
    if any(word in name for word in _INCOME_WORDS):
        return SheetProbe(sheet.name, sheet.visibility, "income", True, None)
    return SheetProbe(sheet.name, sheet.visibility, "other", False, "not_income_sheet")


def probe_workbook(workbook: WorkbookData) -> list[SheetProbe]:
    return [classify_sheet(sheet) for sheet in workbook.sheets]


def suggest_company(workbook: WorkbookData, probes: list[SheetProbe]) -> str | None:
    """Looks for "شرکت …" near the top of the visible non-income (summary) sheets. A wizard suggestion only."""
    for sheet, probe in zip(workbook.sheets, probes):
        if probe.kind != "other":
            continue
        for row in sheet.rows()[:_COMPANY_SCAN_ROWS]:
            for cell in row[:_COMPANY_SCAN_COLS]:
                if not isinstance(cell, str):
                    continue
                match = _COMPANY_PATTERN.search(normalize_text(cell))
                if match:
                    return match.group().strip()
    return None
