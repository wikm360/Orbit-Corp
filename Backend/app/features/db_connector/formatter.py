"""Formats accounting database query results for the LLM agent and end-users.

Handles conversion of Rial amounts to human-friendly Toman / billion Toman figures,
Persian dates, row caps, and query execution metadata (snapshot freshness, timing, query ID).
"""

import datetime
import decimal
from typing import Any

from app.core.config import get_settings

_MONEY_PATTERNS = (
    "amount",
    "debit",
    "credit",
    "balance",
    "net_debit",
    "cost",
    "price",
    "revenue",
    "salary",
    "fee",
    "gross_pay",
    "net_pay",
    "payable",
    "receivable",
    "turnover",
    "total",
)


def is_money_column(col_name: str) -> bool:
    name = col_name.lower()
    # avoid columns like 'line_count', 'employee_count', 'vouchers_count'
    if "count" in name or "id" in name or "code" in name or "no" in name or "year" in name or "month" in name:
        return False
    return any(p in name for p in _MONEY_PATTERNS)


def format_currency_value(value: int | float | decimal.Decimal) -> str:
    """Format Rial amount, adding Toman and billion Toman equivalent where helpful."""
    rial = int(value) if isinstance(value, (int, float, decimal.Decimal)) and value == int(value) else value
    if not isinstance(rial, (int, float, decimal.Decimal)):
        return str(value)

    rial_val = int(rial)
    abs_rial = abs(rial_val)

    if abs_rial < 10_000:
        return f"{rial_val:,} ریال"

    toman = rial_val // 10
    abs_toman = abs(toman)

    if abs_toman >= 1_000_000_000:  # >= 1 billion Tomans (10 billion Rials)
        billion_toman = toman / 1_000_000_000
        return f"{rial_val:,} ریال ({billion_toman:,.2f} میلیارد تومان)"
    elif abs_toman >= 1_000_000:  # >= 1 million Tomans
        million_toman = toman / 1_000_000
        return f"{rial_val:,} ریال ({million_toman:,.1f} میلیون تومان)"
    else:
        return f"{rial_val:,} ریال ({toman:,} تومان)"


def format_cell(col_name: str, val: Any) -> str:
    if val is None:
        return "-"
    if isinstance(val, (int, float, decimal.Decimal)):
        if is_money_column(col_name):
            return format_currency_value(val)
        if isinstance(val, int):
            return f"{val:,}" if abs(val) >= 1000 and "year" not in col_name.lower() and "code" not in col_name.lower() else str(val)
        return f"{val:,.2f}"
    if isinstance(val, (datetime.date, datetime.datetime)):
        return str(val)[:10]
    return str(val)


def format_query_result(
    *,
    columns: list[str],
    rows: list[list[Any]],
    sql: str,
    duration_ms: int,
    query_id: str | None = None,
    truncated: bool = False,
    data_as_of: dict[str, str] | None = None,
    include_sql: bool = True,
    total_rows: int | None = None,
    column_sums: dict[str, Any] | None = None,
) -> str:
    """Renders the query execution outcome as structured Markdown for the assistant."""
    settings = get_settings()
    max_rows = settings.rahkaran_db_rows_to_model

    lines: list[str] = []
    lines.append("### نتیجه‌ی پرس‌وجو از پایگاه داده مالی و حسابداری راهکاران")
    lines.append("")

    # Executed SQL block (the chat UI shows the SQL itself from the message artifact, so the model copy omits it)
    if include_sql:
        lines.append("<details>")
        lines.append("<summary>مشاهده کوئری SQL اجرا شده</summary>\n")
        lines.append("```sql")
        lines.append(sql.strip())
        lines.append("```")
        lines.append("</details>")
        lines.append("")

    if not rows:
        lines.append(
            "**نتیجه:** این کوئری بدون خطا اجرا شد ولی ۰ ردیف برگرداند. این الزاماً به معنی نبودن داده نیست: ممکن است فیلتر "
            "(نام واحد/مرکز هزینه/پروژه یا ماه) با مقدارهای واقعی داده نخواند. نگو «داده‌ای وجود ندارد»؛ بگو چه فیلترهایی اعمال شد "
            "(از SQL مرجع) و پیشنهاد بده کاربر نام را دقیق‌تر یا به شکل دیگری بنویسد."
        )
    else:
        fetched_rows = len(rows)
        shown_rows = rows[:max_rows]

        # Markdown table
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        lines.append(header)
        lines.append(separator)

        for row in shown_rows:
            formatted_cells = [format_cell(col, val) for col, val in zip(columns, row)]
            lines.append("| " + " | ".join(formatted_cells) + " |")

        lines.append("")
        if fetched_rows > max_rows or truncated:
            if total_rows is not None:
                size = f"تعداد کل ردیف‌های نتیجه **{total_rows:,}** است"
            else:
                size = f"تعداد کل ردیف‌ها بیش از {fetched_rows:,} است (عدد دقیق نامشخص)"
            lines.append(
                f"> ⚠️ **مهم:** {size}، ولی فقط {len(shown_rows)} ردیف اول در همین جدول به تو داده شده؛ کاربر همه‌ی ردیف‌ها را در جدول و اکسل می‌بیند. "
                "هر جا تعداد کل را می‌گویی همین عدد را بگو، نه تعداد ردیف‌های این جدول. از این ردیف‌های ناقص جمع، میانگین یا رتبه نساز."
            )
            for name, total in (column_sums or {}).items():
                lines.append(f"> • جمع ستون «{name}» در همه‌ی ردیف‌ها: {format_cell(name, total)}")

    lines.append("")
    lines.append("---")
    lines.append("**اطلاعات اجرا:**")
    meta_items: list[str] = [f"⏱️ زمان اجرا: {duration_ms} میلی‌ثانیه", f"📊 تعداد کل ردیف‌ها: {total_rows if total_rows is not None else len(rows)}{'+' if truncated and total_rows is None else ''}"]
    if query_id:
        meta_items.append(f"🔖 شناسه پیگیری پرس‌وجو: `{query_id}`")
    lines.append(" • ".join(meta_items))

    if data_as_of:
        freshness_notes: list[str] = []
        for k in (
            "تاریخ جلالی آخرین سند حسابداری معتبر",
            "آخرین زمان ثبت/ویرایش سند (نشانه‌ی تاریخ بک‌آپ)",
            "سال مالی جاری (آخرین سال با بیش از 100 سند)",
            "آخرین ماه محاسبه حقوق (YYYYMM جلالی)",
        ):
            if k in data_as_of:
                freshness_notes.append(f"{k}: **{data_as_of[k]}**")
        if freshness_notes:
            lines.append("")
            lines.append("📅 **وضعیت تازگی داده‌ها:** " + " | ".join(freshness_notes))

    return "\n".join(lines)

