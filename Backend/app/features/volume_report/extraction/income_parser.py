"""Reads one income sheet into quantity lines. Deterministic, no LLM, no DB.

Layout varies between files (header on row 4 or 5, description column 0/1/2, "درصد/حجم" instead of "حجم"), so columns
are found by header label, never by position. Rows below the first "جمع …" row are notes and are never read."""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.features.volume_report.extraction.normalize import (
    Lexicon,
    light_clean,
    normalize_text,
    parse_quantity,
    persian_months_in,
    role_hint,
)
from app.features.volume_report.extraction.units import normalize_unit

HEADER_SCAN_ROWS = 12
TITLE_SCAN_ROWS = 3
_QTY_LABELS = {"حجم", "درصد حجم", "حجم درصد"}
_QUOTES = '"«»“”'
_MINING_WORDS = ("معدن", "باطله")


@dataclass
class ParsedLine:
    row_no: int  # 1-based, as shown in Excel
    sheet_name: str
    section_heading: str | None
    description_raw: str
    description_norm: str
    tokens: list[str]
    role_hint: str
    unit_raw: str
    unit_norm: str
    unit_dim: str
    quantity: Decimal
    flags: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedSheet:
    sheet_name: str
    status: str  # ok | layout_unknown
    header_row: int | None = None
    columns: dict[str, int | None] = field(default_factory=dict)
    site_name: str = ""
    site_name_norm: str = ""
    site_kind_guess: str = "road"
    basis: str = "actual"  # actual | planned (forecast for the period after the report's)
    lines: list[ParsedLine] = field(default_factory=list)
    rows_total: int = 0
    rows_nonzero: int = 0
    rows_nonphysical: int = 0
    warnings: list[dict[str, Any]] = field(default_factory=list)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def find_layout(rows: list[list[Any]]) -> tuple[int, dict[str, int | None]] | None:
    """(0-based header row index, columns) or None. The header row has a quantity label and "واحد"."""
    for index, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        labels = [normalize_text(cell) if isinstance(cell, str) else "" for cell in row]
        qty = next((i for i, label in enumerate(labels) if label in _QTY_LABELS), None)
        unit = next((i for i, label in enumerate(labels) if label == "واحد"), None)
        if qty is None or unit is None:
            continue
        activity = next((i for i, label in enumerate(labels) if label == "فعالیت"), None)
        sharh = next((i for i, label in enumerate(labels) if label == "شرح"), None)
        desc_compound = next(
            (i for i, label in enumerate(labels) if label in {"شرح فعالیت", "شرح عملیات", "شرح کار", "شرح آیتم", "آیتم", "موضوع"}),
            None,
        )
        desc = activity if activity is not None else (sharh if sharh is not None else desc_compound)
        if desc is None:
            continue
        section: int | None = sharh if sharh is not None and sharh != desc else None
        if section is None and desc != 0:
            section = 0  # column A carries section titles such as "عملیات آسفالت"; validated per cell below
        return index, {"desc": desc, "section": section, "qty": qty, "unit": unit}
    return None


_DATE = r"\d{2,4}\s*[/\-.]\s*\d{1,2}\s*[/\-.]\s*\d{1,4}"
_MONTHS = "|".join(("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"))
_PERIOD_TAIL = re.compile(
    rf"(?:(?:\s+از)?\s*{_DATE}\s+الی\s+{_DATE}|\s*(?:تاریخ\s*[:：]?\s*)?{_DATE}|\s+(?:{_MONTHS})\s*ماه(?:\s+\d{{4}})?|\s+تاریخ\s*[:：]?)\s*$"
)


def strip_period_from_name(name: str) -> str:
    """A site is the same site every week: drop the report date / month the title carries after the project name
    ("… زاهدان خاش 1405/08/11", "… قطعه 2 آبان ماه 1405 تاریخ : 1405/08/11"). Digits that are part of the name stay."""
    previous = None
    while previous != name:
        previous = name
        name = _PERIOD_TAIL.sub("", name).strip(" :-–")
    return name


def extract_site_name(rows: list[list[Any]], sheet_name: str) -> str:
    """"…پروژه <name> در ماه …" from the title rows; falls back to the sheet name minus "درآمد"."""
    for row in rows[:TITLE_SCAN_ROWS]:
        for cell in row:
            if not isinstance(cell, str):
                continue
            text = light_clean(cell)
            squashed = normalize_text(text)
            if "پروژه" not in squashed:
                continue
            after = text.split("پروژه", 1)[1]
            after = re.split(r"\s+در\s+ماه\b", after, maxsplit=1)[0]
            name = re.sub(f"[{re.escape(_QUOTES)}]", "", after)
            name = strip_period_from_name(re.sub(r"\s+", " ", name).strip(" :-–"))
            if name:
                return name
    fallback = re.sub(r"در[آا]مد|برنامه(?:\s*ای)?|پیش\s*بینی", "", light_clean(sheet_name))
    fallback = re.sub(r"\(صفحه\s*\d+\)", "", fallback)
    return re.sub(r"\s+", " ", fallback).strip(" -_") or sheet_name.strip()


def guess_site_kind(site_name_norm: str) -> str:
    return "mining" if any(word in site_name_norm for word in _MINING_WORDS) else "road"


def _title_text(rows: list[list[Any]]) -> str:
    return " ".join(cell for row in rows[:TITLE_SCAN_ROWS] for cell in row if isinstance(cell, str))


def period_label_warning(rows: list[list[Any]], period_label: str | None) -> dict[str, Any] | None:
    """Non-blocking: the month in the sheet title differs from the period the user entered."""
    if not period_label:
        return None
    expected, found = persian_months_in(period_label), persian_months_in(_title_text(rows))
    if expected and found and expected.isdisjoint(found):
        return {"code": "period_label_mismatch", "found": sorted(found), "expected": sorted(expected)}
    return None


def _annotate(lines: list[ParsedLine]) -> None:
    """twin_rows: other physical lines on the sheet with the exact same quantity and unit but another description
    (e.g. "بتن‌ریزی شمع" and "حمل مصالح بتن‌ریزی شمع"). A hint for the agent/human -- never auto-deduplicated."""
    by_quantity: dict[tuple[Decimal, str], list[ParsedLine]] = {}
    for line in lines:
        if line.unit_dim != "nonphysical" and line.quantity > 0:
            by_quantity.setdefault((line.quantity, line.unit_norm), []).append(line)
    for group in by_quantity.values():
        for line in group:
            twins = [o.row_no for o in group if o is not line and o.description_norm != line.description_norm]
            if twins:
                line.flags["twin_rows"] = twins


def layout_from_spec(spec: dict[str, Any]) -> tuple[int, dict[str, int | None]]:
    """Agent/human supplied layout (1-based Excel row/column numbers) -> the parser's (0-based header index, columns)."""
    def col(name: str) -> int | None:
        value = spec.get(name)
        return None if value in (None, "") else int(value) - 1

    return int(spec["header_row"]) - 1, {"desc": col("desc_col"), "section": col("section_col"), "qty": col("qty_col"), "unit": col("unit_col")}


def parse_income_sheet(
    sheet_name: str,
    rows: list[list[Any]],
    lexicon: Lexicon,
    period_label: str | None = None,
    layout_override: dict[str, Any] | None = None,
    basis: str = "actual",
) -> ParsedSheet:
    layout = layout_from_spec(layout_override) if layout_override else find_layout(rows)
    stop_marker = normalize_text((layout_override or {}).get("stop_marker") or "جمع")
    name = extract_site_name(rows, sheet_name)
    name_norm = normalize_text(name)
    parsed = ParsedSheet(sheet_name, "ok", site_name=name, site_name_norm=name_norm, site_kind_guess=guess_site_kind(name_norm), basis=basis)
    if layout is None:
        parsed.status = "layout_unknown"
        return parsed
    header_index, columns = layout
    parsed.header_row = header_index + 1
    parsed.columns = columns
    if basis == "actual" and (warning := period_label_warning(rows, period_label)) is not None:  # a forecast names the next period
        parsed.warnings.append(warning)

    desc_col, section_col, qty_col, unit_col = columns["desc"], columns["section"], columns["qty"], columns["unit"]
    section: str | None = None
    missing_cache_rows = 0

    def cell(row: list[Any], col: int | None) -> Any:
        return row[col] if col is not None and col < len(row) else None

    for index in range(header_index + 1, len(rows)):
        row = rows[index]
        row_no = index + 1
        # "جمع …" in any of the first three cells ends the table; what follows are notes and stray numbers.
        if any(isinstance(c, str) and normalize_text(c).startswith(stop_marker) for c in row[:3]):
            break
        section_value = cell(row, section_col)
        if isinstance(section_value, str):
            heading = section_value.strip()
            if heading and parse_quantity(heading) is None:
                section = heading
        desc_value = cell(row, desc_col)
        if desc_value is None or not _text(desc_value):
            continue  # blank row: skipped, not a stop ("پله ۶" follows a blank row in the mining file)
        parsed.rows_total += 1
        quantity = parse_quantity(cell(row, qty_col))
        unit_cell = cell(row, unit_col)
        if quantity is None or quantity == 0:
            # Formula cells saved without a cached result read as None; remember rows that look like that.
            if quantity is None and cell(row, qty_col) is None and _text(unit_cell) and any(
                isinstance(c, (int, float)) and not isinstance(c, bool) and c for i, c in enumerate(row) if i != qty_col
            ):
                missing_cache_rows += 1
            continue
        parsed.rows_nonzero += 1
        unit = normalize_unit(unit_cell)
        description_raw = _text(desc_value)
        description_norm = normalize_text(description_raw)
        tokens = lexicon.tokenize(description_norm)
        flags: dict[str, Any] = {}
        if quantity < 0:
            flags["negative_qty"] = True
        if "SURCHARGE" in tokens:
            flags["has_surcharge_word"] = True
        if unit.unit_dim == "nonphysical":
            flags["nonphysical_unit"] = True
            parsed.rows_nonphysical += 1
        if unit.empty:
            parsed.warnings.append({"code": "unit_missing", "row": row_no})
        parsed.lines.append(
            ParsedLine(
                row_no=row_no,
                sheet_name=sheet_name,
                section_heading=section,
                description_raw=description_raw,
                description_norm=description_norm,
                tokens=tokens,
                role_hint=role_hint(tokens),
                unit_raw=_text(unit_cell),
                unit_norm=unit.unit_norm,
                unit_dim=unit.unit_dim,
                quantity=quantity,
                flags=flags,
            )
        )
    _annotate(parsed.lines)
    if missing_cache_rows >= 3 and parsed.rows_nonzero == 0:
        parsed.warnings.append({"code": "cached_values_missing", "rows": missing_cache_rows})
    return parsed
