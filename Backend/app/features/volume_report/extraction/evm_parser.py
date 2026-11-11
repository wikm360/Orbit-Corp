"""EVM summary sheet ("گزارش مدیریت ارزش کسب شده"): one row per project (+ a "جمع" row) with PV / EV / ev / AC / CPI / SPI.

Pure (no DB). The sheet is found by its *content* (a header that mentions CPI, SPI and "مبلغ قرارداد"), not by its name, because
the same summary arrives as an Excel sheet or as the first page of a vector PDF whose cells are merged unpredictably. Every
row is therefore turned into a flat token list and read by its numeric shape rather than by column position:

    [index] [name...] contract [months %% %%] [BCWS(M)] [PV] [EV] [ev] [AC] CPI SPI [notes]

Absent columns are simply missing (a project without a work programme has no PV; a project with no cost yet has only M/PV),
so the roles are assigned from the *count* of amounts and verified against the printed CPI (= ev / AC).
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.features.volume_report.extraction.normalize import normalize_text

_HEADER_SCAN_ROWS = 20
_AMOUNT = re.compile(r"^\d{1,3}(?:,\d{3})+$")
_AMOUNT_ANY = re.compile(r"\d{1,3}(?:,\d{3})+")
_BIG_INT = re.compile(r"^\d{5,}$")
_DECIMAL = re.compile(r"^\d+\.\d{1,3}$")
_RATIO = re.compile(r"^\d{1,2}(?:\.\d{1,3})?$")  # after the amounts: CPI, SPI (an Excel 0.0 / 1.0 arrives as "0" / "1")
_INT = re.compile(r"^\d{1,4}$")
_TOTAL_WORDS = ("جمع",)
_PLAN_WORDS = ("پیش بینی",)
_TOLERANCE = Decimal("0.02")
# Header cells that wrap onto the rows below the CPI/SPI row; a text row with one of these is never part of a project name.
_HEADER_WORDS = ("ریال", "ردیف", "bcws", "ضریب", "واقعی", "برنامه ای", "توضیحات", "مدت", "پیشرفت", "درصد", "( ماه )", "نام پروژه", "کارکرد")


@dataclass
class EvmRowData:
    row_no: int
    project_name: str | None
    is_total: bool
    contract_amount: Decimal | None = None
    bcws: Decimal | None = None
    pv: Decimal | None = None
    ev: Decimal | None = None  # EV: کارکرد (with overhead)
    ev_net: Decimal | None = None  # ev: کارکرد پس از کسر ضریب بالاسری
    ac: Decimal | None = None
    cpi: Decimal | None = None
    spi: Decimal | None = None


@dataclass
class ParsedEvm:
    sheet_name: str
    basis: str  # actual | planned
    rows: list[EvmRowData] = field(default_factory=list)
    header_row: int = 0
    warnings: list[dict[str, Any]] = field(default_factory=list)


def _digits(value: str) -> str:
    value = re.sub(r"[۰-۹]", lambda m: str(ord(m.group()) - 0x06F0), value)
    value = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), value)
    return value.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")


def _number_token(value: float | int) -> str:
    """Excel numeric cells: amounts get thousand separators (like the PDF text), ratios two decimals, small ints stay."""
    number = float(value)
    if number == 0:
        return "0"
    if abs(number) >= 1000 and abs(number - round(number)) < 1e-6 or abs(number) >= 100000:
        return f"{round(number):,}"
    if number == int(number):
        return str(int(number))
    return f"{number:.2f}"


def _row_tokens(row: list[Any]) -> list[str]:
    tokens: list[str] = []
    for cell in row:
        if cell is None or isinstance(cell, bool):
            continue
        if isinstance(cell, (int, float)):
            tokens.append(_number_token(cell))
            continue
        for part in _digits(str(cell).replace("،", ",").replace("٫", ".").replace("٬", ",")).split():
            if "," in part and re.fullmatch(r"[\d,]+", part) and not _AMOUNT.match(part):
                tokens.extend(_AMOUNT_ANY.findall(part) or [part])  # "3,724,759,215,00319,833,333,333" = two amounts glued together
            else:
                tokens.append(part)
    return tokens


def _is_amount(token: str) -> bool:
    return bool(_AMOUNT.match(token) or _BIG_INT.match(token))


def _is_zero(token: str) -> bool:
    return token in ("0", "-")  # "0.00" is a ratio / progress, never an amount


def _to_decimal(token: str) -> Decimal | None:
    try:
        return Decimal(token.replace(",", ""))
    except InvalidOperation:
        return None


def _find_header(rows: list[list[Any]]) -> int | None:
    """Index of the row that names CPI/SPI, provided "مبلغ قرارداد" is somewhere in the header block."""
    for index, row in enumerate(rows[:_HEADER_SCAN_ROWS]):
        text = " ".join(str(c) for c in row if c is not None).lower()
        if "cpi" in text and "spi" in text:
            block = " ".join(" ".join(str(c) for c in r if c is not None) for r in rows[: index + 4])
            if "قرارداد" in normalize_text(block):
                return index
    return None


def _basis(rows: list[list[Any]], header_index: int, sheet_name: str, file_name: str | None) -> str:
    title = normalize_text(" ".join(str(c) for r in rows[:header_index] for c in r if c is not None))
    names = normalize_text(f"{sheet_name} {file_name or ''}")
    return "planned" if any(w in title or w in names for w in _PLAN_WORDS) else "actual"


def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return (numerator / denominator).quantize(Decimal("0.01"))


def _assign(row: EvmRowData, amounts: list[Decimal], printed_cpi: Decimal | None) -> bool:
    """Roles by the number of amounts (after the contract amount). False when the shape is not understood."""
    n = len(amounts)
    if n == 5:
        row.bcws, row.pv, row.ev, row.ev_net, row.ac = amounts
    elif n == 3:
        row.ev, row.ev_net, row.ac = amounts
    elif n == 2:
        row.bcws, row.pv = amounts
    elif n == 4:
        # (PV, EV, ev, AC) when the printed CPI agrees with ev / AC, otherwise (M, PV, EV, ev) with the cost still empty.
        guess = _ratio(amounts[2], amounts[3])
        if guess is not None and printed_cpi is not None and abs(guess - printed_cpi) <= _TOLERANCE:
            row.pv, row.ev, row.ev_net, row.ac = amounts
        else:
            row.bcws, row.pv, row.ev, row.ev_net = amounts
    else:
        return False
    return True


def _parse_row(row_no: int, tokens: list[str]) -> tuple[EvmRowData | None, list[str], str | None]:
    """(row, name tokens, problem). A row without any amount returns (None, name tokens, None): it is a name fragment."""
    is_total = any(t in _TOTAL_WORDS for t in tokens[:3])
    strong = [i for i, t in enumerate(tokens) if _is_amount(t)]
    if not strong:
        return None, [t for t in tokens if not _INT.match(t) or len(tokens) > 1], None
    last = strong[-1]
    first = 0 if is_total else strong[0]
    ratios = [_to_decimal(t) for t in tokens[last + 1:] if _RATIO.match(t)][:2]
    ratios += [None] * (2 - len(ratios))
    contract = None
    start = first
    if not is_total:
        contract = _to_decimal(tokens[strong[0]])
        start = strong[0] + 1
    amounts = [_to_decimal(t) for t in tokens[start:last + 1] if _is_amount(t) or _is_zero(t)]
    if any(a is None for a in amounts):
        return None, [], "unparsable_amount"
    data = EvmRowData(row_no=row_no, project_name=None, is_total=is_total, contract_amount=contract)
    printed_cpi, printed_spi = ratios
    if not _assign(data, amounts, printed_cpi):
        return None, [], f"unexpected_amount_count:{len(amounts)}"
    # A printed ratio only counts when both of its operands exist (the sheet prints 0.00 for "no data").
    data.cpi = printed_cpi if data.ev_net is not None and data.ac is not None and data.ac > 0 else None
    data.spi = printed_spi if data.ev is not None and data.pv is not None and data.pv > 0 else None
    if data.cpi is not None:
        computed = _ratio(data.ev_net, data.ac)
        if computed is not None and abs(computed - data.cpi) > _TOLERANCE and printed_spi is not None:
            # The two printed ratios came out swapped (right-to-left tables): trust the one that matches the amounts.
            alt_spi = _ratio(data.ev, data.pv)
            if alt_spi is not None and abs(alt_spi - data.cpi) <= _TOLERANCE and computed is not None and abs(computed - printed_spi) <= _TOLERANCE:
                data.cpi, data.spi = printed_spi, data.cpi
    name_tokens: list[str] = []
    if not is_total:
        name_tokens = list(tokens[: strong[0]])
        if name_tokens and _INT.match(name_tokens[0]):
            name_tokens = name_tokens[1:]  # the row number
        if not any(not _INT.match(t) for t in name_tokens):  # right-to-left tables: the name trails the ratios
            tail = [t for t in tokens[last + 1:] if not _RATIO.match(t)]
            name_tokens = [*tail, *name_tokens]
    return data, name_tokens, None


def _join(tokens: list[str]) -> str:
    return " ".join(tokens).strip()


def parse_evm_sheet(sheet_name: str, rows: list[list[Any]], file_name: str | None = None) -> ParsedEvm | None:
    """None when the sheet is not an EVM summary at all."""
    header = _find_header(rows)
    if header is None:
        return None
    parsed = ParsedEvm(sheet_name=sheet_name, basis=_basis(rows, header, sheet_name, file_name), header_row=header + 1)
    pending: list[str] = []  # name fragments seen since the previous numeric row
    last_row: EvmRowData | None = None
    for offset, raw in enumerate(rows[header + 1:], start=header + 2):
        tokens = _row_tokens(raw)
        if not tokens:
            continue
        data, name_tokens, problem = _parse_row(offset, tokens)
        if problem:
            parsed.warnings.append({"row": offset, "code": problem})
            continue
        if data is None:
            if parsed.rows and (_is_legend(tokens) or any(t in _TOTAL_WORDS for t in tokens[:3])):
                break  # "جمع" without amounts / the footnotes: the table is over
            if _is_header_text(tokens):
                continue
            fragment = _join(name_tokens)
            if not fragment:
                continue
            if last_row is not None and _open_paren(last_row.project_name):
                last_row.project_name = f"{last_row.project_name} {fragment}"  # "( حدفاصل" ... "کیلومتر 53 )"
            else:
                pending.append(fragment)
            continue
        inline = _join(name_tokens)
        if data.is_total:
            data.project_name = None
            parsed.rows.append(data)
            break
        data.project_name = re.sub(r"^\d{1,2}\s+", "", _join([*pending, inline])) or None  # a row number that spilled into the name
        pending = []
        parsed.rows.append(data)
        last_row = data
    if pending and last_row is not None and not last_row.is_total:
        last_row.project_name = _join([last_row.project_name or "", *pending]) or None  # the name's second line sits below the numbers
    if not parsed.rows:
        return None
    return parsed


def _open_paren(name: str | None) -> bool:
    return bool(name) and name.count("(") > name.count(")")


def _is_header_text(tokens: list[str]) -> bool:
    text = normalize_text(" ".join(tokens))
    return any(word in text for word in _HEADER_WORDS)


def _is_legend(tokens: list[str]) -> bool:
    """Footnotes such as "T : مدت قرارداد ac : هزینه ماهیانه" end the table."""
    return bool(tokens) and tokens[0].lower() in ("t", "t:", "ac", "ev", "pv") and ":" in " ".join(tokens[:3])
