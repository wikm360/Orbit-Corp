"""Uniform read access to .xls/.xlsx/.xlsm/.xlsb workbooks. Blocking I/O: call from a worker/thread, never an async handler.

Only the cells the parser needs are materialised (<= MAX_ROWS x MAX_COLS per sheet) and only for sheets asked for."""

import logging
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)

MAX_ROWS = 400
MAX_COLS = 40

Rows = list[list[Any]]


@dataclass
class SheetData:
    name: str
    visibility: str  # visible | hidden | veryHidden
    _loader: Callable[[], Rows]
    _rows: Rows | None = None

    @property
    def is_hidden(self) -> bool:
        return self.visibility != "visible"

    def rows(self) -> Rows:
        if self._rows is None:
            self._rows = self._loader()
        return self._rows


@dataclass
class WorkbookData:
    sheets: list[SheetData]


def _clean(value: Any) -> Any:
    return None if value == "" else value


def _xlsx_hidden_rows(path: str) -> dict[str, set[int]]:
    """sheet title -> 1-based numbers of the rows the operator hid (or an autofilter hid), among the first MAX_ROWS. openpyxl's read-only
    mode does not expose row visibility, so the sheet XML is scanned."""
    import posixpath
    import re
    import zipfile
    from xml.etree import ElementTree as ET

    out: dict[str, set[int]] = {}
    ns_main = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    ns_rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    try:
        with zipfile.ZipFile(path) as zf:
            rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))}
            for sheet in ET.fromstring(zf.read("xl/workbook.xml")).iter(f"{ns_main}sheet"):
                target = rels.get(sheet.get(f"{ns_rel}id"))
                if not target:
                    continue
                member = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
                hidden: set[int] = set()
                with zf.open(member) as stream:
                    for _, element in ET.iterparse(stream, events=("end",)):
                        if element.tag != f"{ns_main}row":
                            continue
                        number = int(element.get("r") or 0)
                        if number > MAX_ROWS:
                            break
                        if element.get("hidden") in ("1", "true"):
                            hidden.add(number)
                        element.clear()
                out[sheet.get("name")] = hidden
    except Exception:  # a layout we cannot scan: read every row, as before
        logger.warning("Could not read the hidden rows of %s", Path(path).name)
        return {}
    return out


def _open_xlsx(path: str, stack: ExitStack) -> WorkbookData:
    from openpyxl import load_workbook

    workbook = load_workbook(path, data_only=True, read_only=True)
    stack.callback(workbook.close)
    hidden_rows = _xlsx_hidden_rows(path)
    sheets = []
    for worksheet in workbook.worksheets:
        def loader(ws=worksheet) -> Rows:
            hidden = hidden_rows.get(ws.title, set())
            rows = [
                [_clean(cell) for cell in row]
                for row in ws.iter_rows(min_row=1, max_row=MAX_ROWS, max_col=MAX_COLS, values_only=True)
            ]
            # A row the operator hid is not part of the report: blank it (keeping the row numbers the questions point at).
            return [[None] * len(row) if number in hidden else row for number, row in enumerate(rows, start=1)]

        sheets.append(SheetData(worksheet.title, worksheet.sheet_state or "visible", loader))
    return WorkbookData(sheets)


_XLRD_VISIBILITY = {0: "visible", 1: "hidden", 2: "veryHidden"}


def _open_xls(path: str, stack: ExitStack) -> WorkbookData:
    import xlrd

    try:
        book = xlrd.open_workbook(path, on_demand=True, formatting_info=True)  # row visibility needs the formatting records
    except Exception:  # some files (odd BIFF records) refuse formatting_info: read them without it
        book = xlrd.open_workbook(path, on_demand=True)
    stack.callback(book.release_resources)
    sheets = []
    for index in range(book.nsheets):
        sheet = book.sheet_by_index(index)

        def loader(idx=index) -> Rows:
            ws = book.sheet_by_index(idx)
            rows: Rows = []
            row_info = getattr(ws, "rowinfo_map", {})
            for r in range(min(ws.nrows, MAX_ROWS)):
                if getattr(row_info.get(r), "hidden", 0):
                    rows.append([None] * min(ws.ncols, MAX_COLS))  # hidden by the operator: not part of the report (row numbers kept)
                    continue
                row = ws.row(r)[:MAX_COLS]
                # xlrd error cells (#N/A, #DIV/0!) carry an int code, not data
                rows.append([None if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_ERROR)
                             else _clean(cell.value) for cell in row])
            return rows

        sheets.append(SheetData(sheet.name, _XLRD_VISIBILITY.get(sheet.visibility, "hidden"), loader))
    return WorkbookData(sheets)


@contextmanager
def open_workbook(path: str) -> Iterator[WorkbookData]:
    """.xls via xlrd, falling back to a LibreOffice-converted copy read with openpyxl; .xlsx/.xlsm via openpyxl.
    The original file is always the source -- never the ingestion pipeline's converted text."""
    suffix = Path(path).suffix.lower()
    with ExitStack() as stack:
        if suffix == ".xls":
            try:
                data = _open_xls(path, stack)
            except Exception as xls_error:  # xlrd raises several unrelated types on odd files
                logger.warning("xlrd could not read %s (%s); trying converted copy", Path(path).name, xls_error)
                from app.features.documents.ingestion.converter import converted_copy

                try:
                    converted = stack.enter_context(converted_copy(path))
                    data = _open_xlsx(converted, stack)
                except Exception as convert_error:
                    raise BadRequestError("The spreadsheet could not be read.") from convert_error
        elif suffix == ".xlsb":
            # openpyxl cannot read the binary format: LibreOffice makes an xlsx twin (as it does for a broken .xls)
            from app.features.documents.ingestion.converter import converted_copy

            try:
                data = _open_xlsx(stack.enter_context(converted_copy(path)), stack)
            except Exception as error:
                raise BadRequestError("The spreadsheet could not be read.") from error
        elif suffix in (".xlsx", ".xlsm"):
            try:
                data = _open_xlsx(path, stack)
            except Exception as error:
                raise BadRequestError("The spreadsheet could not be read.") from error
        elif suffix == ".pdf":
            try:
                from app.features.volume_report.extraction.pdf_extractor import open_pdf_as_workbook

                data = open_pdf_as_workbook(path)
            except Exception as error:
                raise BadRequestError("The PDF document could not be read.") from error
        else:
            raise BadRequestError("Only .xls, .xlsx, .xlsm, .xlsb and .pdf files are supported.")
        yield data
