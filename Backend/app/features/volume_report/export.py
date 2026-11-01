"""XLSX/CSV export of a report's results (RTL, bold header, frozen header row, BOM for CSV, formula-injection guard)."""

import csv
import io

_COLUMNS = ["شرکت", "کارگاه", "آیتم", "مقدار", "واحد", "تعداد ردیف", "تأییدنشده"]


def safe_cell(value):
    """Text starting with = + - @ would be a formula in Excel; store it as text. (Numbers pass through.)"""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def build_csv(rows: list[list]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_COLUMNS)
    writer.writerows([[safe_cell(v) for v in row] for row in rows])
    return ("﻿" + buffer.getvalue()).encode("utf-8")


def build_xlsx(rows: list[list], extra_title: str = "سایر و مشکل‌دار", extra_columns: list[str] | None = None,
               extra_rows: list[list] | None = None) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    sheets = [("نتایج", _COLUMNS, rows)]
    if extra_rows:
        sheets.append((extra_title, extra_columns or [], extra_rows))
    for index, (title, columns, data) in enumerate(sheets):
        ws = wb.active if index == 0 else wb.create_sheet()
        ws.title = title
        ws.sheet_view.rightToLeft = True
        ws.append(columns)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="163B48")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for row in data:
            ws.append([safe_cell(v) for v in row])
        ws.freeze_panes = "A2"
        for idx, name in enumerate(columns, start=1):
            sample = [len(str(r[idx - 1])) for r in data[:200] if idx - 1 < len(r) and r[idx - 1] is not None]
            ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = min(max([len(name)] + sample) + 3, 60)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
