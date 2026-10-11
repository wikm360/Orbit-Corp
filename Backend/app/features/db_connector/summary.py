"""Exact totals for results the model only sees part of, and discovery of real column values for zero-row results.

The executor caps the rows it fetches and the model sees fewer still, so a "list" question would otherwise be answered with the size of the
fetched slice. Here the true row count and the money-column sums are computed over the whole result (in Python when everything was fetched,
with one wrapping aggregate query otherwise).
"""

import logging
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from app.features.db_connector.artifacts import column_kind
from app.features.db_connector.executor import DbExecutionError, QueryResult, execute_query

logger = logging.getLogger(__name__)

_MAX_SUM_COLUMNS = 6
_MAX_DISCOVERY_COLUMNS = 3
_DISCOVERY_VALUES = 40


@dataclass
class ResultTotals:
    total_rows: int | None  # None: more than fetched, exact count unavailable
    column_sums: dict[str, float | int] = field(default_factory=dict)


def _quote(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


def _money_columns(columns: list[str], rows: list[list]) -> list[tuple[int, str]]:
    found = []
    for i, name in enumerate(columns):
        if column_kind(name, [r[i] for r in rows if i < len(r)]) == "money":
            found.append((i, name))
    return found[:_MAX_SUM_COLUMNS]


def build_totals_sql(sql: str, money_cols: list[str]) -> str | None:
    """`SELECT COUNT(*), SUM(..) FROM (<sql without ORDER BY>) q`; None when the statement cannot be wrapped (UNION, TOP)."""
    try:
        tree = sqlglot.parse_one(sql, dialect="tsql")
    except sqlglot.errors.SqlglotError:
        return None
    if not isinstance(tree, exp.Select) or tree.args.get("limit") is not None:
        return None  # an explicit TOP already is the requested result size
    with_key = next((k for k in tree.args if k.startswith("with")), None)
    with_clause = tree.args.pop(with_key) if with_key and tree.args.get(with_key) else None
    tree.set("order", None)
    projections = [exp.Count(this=exp.Star()).as_("n")]
    for i, name in enumerate(money_cols, 1):
        projections.append(exp.Alias(this=exp.Anonymous(this="SUM", expressions=[sqlglot.parse_one(f"CAST({_quote(name)} AS DECIMAL(38,2))", dialect="tsql")]), alias=exp.to_identifier(f"s{i}")))
    outer = exp.select(*projections).from_(tree.subquery("q"))
    if with_clause is not None:
        outer.set(with_key, with_clause)
    return outer.sql(dialect="tsql")


def _number(value):
    if value is None:
        return 0
    return int(value) if float(value) == int(value) else float(value)


async def compute_totals(sql: str, result: QueryResult, model_rows: int) -> ResultTotals | None:
    """Totals only when the model/client sees a partial result; None when the fetched rows are all there is (or on failure)."""
    money = _money_columns(result.columns, result.rows)
    if not result.truncated:
        if len(result.rows) <= model_rows:
            return None
        sums = {name: _number(sum(r[i] for r in result.rows if isinstance(r[i], (int, float)))) for i, name in money}
        return ResultTotals(total_rows=len(result.rows), column_sums=sums)

    totals_sql = build_totals_sql(sql, [name for _, name in money])
    if totals_sql is None:
        return ResultTotals(total_rows=None)
    try:
        counted = await execute_query(totals_sql, max_rows=1)
    except DbExecutionError as exc:
        logger.info("Totals query failed (%s); falling back to a lower bound", exc.message)
        return ResultTotals(total_rows=None)
    row = counted.rows[0] if counted.rows else []
    if not row:
        return ResultTotals(total_rows=None)
    sums = {name: _number(row[i + 1]) for i, (_, name) in enumerate(money) if i + 1 < len(row)}
    return ResultTotals(total_rows=int(row[0]), column_sums=sums)


def _string_filters(tree: exp.Expression) -> list[tuple[str, str]]:
    """(view, column) pairs that are compared with a text literal (=, LIKE, IN)."""
    aliases: dict[str, str] = {}
    tables = list(tree.find_all(exp.Table))
    for table in tables:
        full = f"{table.db}.{table.name}" if table.db else table.name
        aliases[table.alias_or_name.lower()] = full
        aliases[table.name.lower()] = full
    pairs: list[tuple[str, str]] = []
    for node in tree.find_all(exp.EQ, exp.Like, exp.In):
        column = node.this if isinstance(node.this, exp.Column) else None
        if column is None:
            continue
        literals = [node.expression] if not isinstance(node, exp.In) else list(node.expressions)
        if not any(isinstance(lit, exp.National) or (isinstance(lit, exp.Literal) and lit.is_string) for lit in literals):
            continue
        if column.table:
            view = aliases.get(column.table.lower())
        elif len(tables) == 1:
            view = aliases.get(tables[0].alias_or_name.lower())
        else:
            view = None
        if view and view.lower().startswith("ai.") and (view, column.name) not in pairs:
            pairs.append((view, column.name))
    return pairs


async def empty_result_feedback(sql: str) -> str | None:
    """Repair hint for a statement that ran but returned no rows: the real values of the text columns it filtered on."""
    try:
        tree = sqlglot.parse_one(sql, dialect="tsql")
    except sqlglot.errors.SqlglotError:
        return None
    pairs = _string_filters(tree)
    if not pairs:
        return None
    lines = []
    for view, column in pairs[:_MAX_DISCOVERY_COLUMNS]:
        probe = f"SELECT DISTINCT TOP {_DISCOVERY_VALUES} {_quote(column)} FROM {view} WHERE {_quote(column)} IS NOT NULL"
        try:
            found = await execute_query(probe, max_rows=_DISCOVERY_VALUES)
        except DbExecutionError:
            continue
        values = [str(r[0])[:60] for r in found.rows]
        if values:
            suffix = " ..." if found.row_count >= _DISCOVERY_VALUES else ""
            lines.append(f"- {view}.{column}: " + " | ".join(values) + suffix)
    values_text = "\n".join(lines) if lines else "(مقادیر ستون‌ها قابل دریافت نبود)"
    return (
        "این SQL بدون خطا اجرا شد ولی ۰ ردیف برگرداند. معمولاً یعنی مقدار فیلتر در این ستون وجود ندارد (نه اینکه داده نباشد). "
        "نمونه‌ی مقدارهای واقعی ستون‌های فیلترشده:\n"
        f"{values_text}\n"
        "اگر مقداری که کاربر گفته (مثلاً شعبه، مرکز هزینه، پروژه یا قرارداد) در این ستون نیست، آن را در ستون یا view مناسب دیگر "
        "(مثل cost_center، project_name، contract_name) جستجو کن؛ شرط ماه/سال را هم با داده‌ی موجود مطابقت بده. SQL اصلاح‌شده را بنویس."
    )
