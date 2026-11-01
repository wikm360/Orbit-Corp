"""Tiny synthetic workbooks reproducing the traps of the real company files. No real data lives in the repo."""

from pathlib import Path

from openpyxl import Workbook


def add_income_sheet(
    wb: Workbook,
    name: str,
    rows: list[tuple],
    *,
    title: str = "گزارش درآمد پروژه آزمایشی یک در ماه شهریور 1405",
    header_row: int = 4,
    desc_col: int = 1,
    section_col: int | None = None,
    qty_label: str = "حجم",
    state: str = "visible",
):
    """rows: (section_or_None, description, unit, quantity) tuples; a bare ("جمع …",) tuple writes a total row."""
    ws = wb.create_sheet(name)
    ws.sheet_state = state
    ws.cell(2, 2, title)
    sharh_col = section_col if section_col is not None else None
    ws.cell(header_row, 1, "ردیف")
    ws.cell(header_row, desc_col + 1, "فعالیت")
    if sharh_col is not None:
        ws.cell(header_row, sharh_col + 1, "شرح")
    unit_col, qty_col = 5, 6
    ws.cell(header_row, unit_col, "واحد")
    ws.cell(header_row, qty_col, qty_label)
    r = header_row + 1
    for row in rows:
        if len(row) == 1:
            ws.cell(r, 2, row[0])
        else:
            section, desc, unit, qty = row
            if section is not None and sharh_col is not None:
                ws.cell(r, sharh_col + 1, section)
            if desc is not None:
                ws.cell(r, desc_col + 1, desc)
            ws.cell(r, unit_col, unit)
            ws.cell(r, qty_col, qty)
        r += 1
    return ws


def save(wb: Workbook, tmp_path: Path, filename: str = "book.xlsx") -> str:
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    path = tmp_path / filename
    wb.save(path)
    return str(path)
