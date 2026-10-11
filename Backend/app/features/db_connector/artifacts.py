"""Structured, client-renderable evidence for an accounting-database answer.

The assistant's prose is written by the LLM; this artifact is what the database actually returned (exact SQL, columns, rows) so the UI can
show the reference next to the answer: a table, the SQL, run metadata and feedback. It is stored on the assistant message (`messages.artifacts`).
"""

import datetime
import re
from typing import Any

from app.features.db_connector.money_columns import MONEY_COLUMNS

ARTIFACT_TYPE = "sql_result"
ARTIFACT_VERSION = 1

# Words in a (possibly Persian, LLM-chosen) alias that say the value is already scaled or is not a Rial amount.
_SCALED_OR_NON_MONEY = re.compile(r"میلیارد|میلیون|هزار|تومان|billion|million|toman|درصد|percent|pct|نسبت|ratio|تعداد|count|روز|days|ماه|سال|year|month|شماره|number|کد|code|_id$|^id$|رتبه|rank|index")
_RATIO = re.compile(r"ratio|نسبت|درصد|percent|pct")
_MONEY_WORDS = re.compile(r"ریال|rial|مبلغ|مانده|بدهکار|بستانکار|حقوق|مزایا|کسور|خالص|ناخالص|هزینه|درآمد|سود|زیان|بها|پرداخت|دریافت|طلب|بدهی|بیمه|مالیات")
_MONEY_TOKENS = {"amount", "debit", "credit", "balance", "cost", "revenue", "pay", "wage", "salary", "benefits", "deductions", "insurance", "tax",
                 "allowance", "profit", "payable", "receivable", "turnover", "expense", "margin", "net", "gross"}
_DATE_NAME = re.compile(r"(_date$|^date$|تاریخ)")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_ID_LIKE = re.compile(r"(^|_)(id|code|number|no)$|شماره|کد")
_YEAR_LIKE = re.compile(r"year|month|(^|_)ym$|fiscal|سال|ماه")


def column_kind(name: str, values: list[Any]) -> str:
    """money | ratio | number | date | text - used by the client to format the column."""
    lowered = name.lower()
    non_null = [v for v in values if v is not None]
    numeric = bool(non_null) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_null)
    if _DATE_NAME.search(lowered) or (non_null and all(isinstance(v, str) and _ISO_DATE.match(v) for v in non_null)):
        return "date"
    if not numeric:
        return "text"
    if _ID_LIKE.search(lowered) and not _MONEY_WORDS.search(lowered):
        return "text"
    if _RATIO.search(lowered):
        return "ratio"
    if lowered in MONEY_COLUMNS:
        return "money"
    if _YEAR_LIKE.search(lowered) and not _MONEY_WORDS.search(lowered):
        return "text"  # years / year-months (1404, 140505): shown without thousand separators
    if _SCALED_OR_NON_MONEY.search(lowered):
        return "number"
    if _MONEY_WORDS.search(lowered) or set(re.split(r"[_\s]+", lowered)) & _MONEY_TOKENS:
        return "money"
    return "number"


def build_sql_result_artifact(
    *,
    query_id: str,
    question: str,
    sql: str,
    columns: list[str],
    rows: list[list[Any]],
    truncated: bool,
    duration_ms: int,
    data_as_of: dict[str, str] | None,
    max_rows: int,
    total_rows: int | None = None,
) -> dict:
    shown = rows[:max_rows]
    kinds = [column_kind(col, [r[i] for r in rows if i < len(r)]) for i, col in enumerate(columns)]
    return {
        "type": ARTIFACT_TYPE,
        "version": ARTIFACT_VERSION,
        "query_id": query_id,
        "question": question,
        "sql": sql,
        "columns": [{"name": c, "kind": k} for c, k in zip(columns, kinds)],
        "rows": shown,
        "row_count": total_rows if total_rows is not None else len(rows),
        "rows_fetched": len(rows),
        "total_exact": total_rows is not None or not truncated,
        "rows_shown": len(shown),
        "truncated": truncated,
        "duration_ms": duration_ms,
        "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "data_as_of": data_as_of or {},
        "currency": "IRR",
    }
