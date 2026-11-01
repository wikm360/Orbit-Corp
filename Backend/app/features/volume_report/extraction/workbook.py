"""Uniform read access to .xls/.xlsx/.xlsm workbooks. Blocking I/O: call from a worker/thread, never an async handler.

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


def _open_xlsx(path: str, stack: ExitStack) -> WorkbookData:
    from openpyxl import load_workbook

    workbook = load_workbook(path, data_only=True, read_only=True)
    stack.callback(workbook.close)
    sheets = []
    for worksheet in workbook.worksheets:
        def loader(ws=worksheet) -> Rows:
            return [
                [_clean(cell) for cell in row]
                for row in ws.iter_rows(min_row=1, max_row=MAX_ROWS, max_col=MAX_COLS, values_only=True)
            ]

        sheets.append(SheetData(worksheet.title, worksheet.sheet_state or "visible", loader))
    return WorkbookData(sheets)


_XLRD_VISIBILITY = {0: "visible", 1: "hidden", 2: "veryHidden"}


def _open_xls(path: str, stack: ExitStack) -> WorkbookData:
    import xlrd

    book = xlrd.open_workbook(path, on_demand=True)
    stack.callback(book.release_resources)
    sheets = []
    for index in range(book.nsheets):
        sheet = book.sheet_by_index(index)

        def loader(idx=index) -> Rows:
            ws = book.sheet_by_index(idx)
            rows: Rows = []
            for r in range(min(ws.nrows, MAX_ROWS)):
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
        elif suffix in (".xlsx", ".xlsm"):
            try:
                data = _open_xlsx(path, stack)
            except Exception as error:
                raise BadRequestError("The spreadsheet could not be read.") from error
        else:
            raise BadRequestError("Only .xls, .xlsx and .xlsm files are supported.")
        yield data
