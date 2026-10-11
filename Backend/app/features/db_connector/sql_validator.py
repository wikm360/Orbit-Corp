"""Static validation of model-generated T-SQL before it touches the accounting database.

Defence in depth: the database login can only SELECT from schema `ai`, and the executor adds a row cap and a timeout.
This module additionally guarantees the statement is ONE read-only query over `ai.*` views (or CTEs), so a prompt-injected
or hallucinated statement is rejected with an actionable message that is fed back to the model for a repair attempt.
"""

import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError

ALLOWED_SCHEMA = "ai"
MAX_SQL_CHARS = 8000

_FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Merge, exp.TruncateTable, exp.Command,
    exp.Use, exp.Set, exp.Into, exp.Transaction, exp.Commit, exp.Rollback, exp.Grant,
)
# Matched on the SQL with string literals blanked out, so Persian text in LIKE patterns can never trigger them.
_FORBIDDEN_WORDS = re.compile(
    r"\b(openrowset|opendatasource|openquery|openxml|xp_\w+|sp_\w+|fn_\w+|dbcc|waitfor|bulk|shutdown|exec|execute|"
    r"declare|kill|backup|restore|reconfigure|grant|revoke|deny|option|tablesample)\b",
    re.IGNORECASE,
)
_SYSTEM_PREFIX = re.compile(r"\b(sys|information_schema|master|msdb|tempdb|model)\s*\.", re.IGNORECASE)


class SqlValidationError(ValueError):
    """The SQL is not acceptable; the message is written for the model (English, actionable)."""


@dataclass(frozen=True)
class ValidatedSql:
    sql: str  # comment-free, single statement, no trailing semicolon
    views: tuple[str, ...]  # ai views referenced (lower-case, without schema)


def strip_comments(sql: str) -> str:
    """Remove `-- ...` and `/* ... */` comments without touching string literals, [bracketed] or "quoted" identifiers."""
    out: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c in ("'", '"', "["):
            close = "]" if c == "[" else c
            j = i + 1
            while j < n:
                if sql[j] == close:
                    if close != "]" and j + 1 < n and sql[j + 1] == close:  # doubled quote escape
                        j += 2
                        continue
                    break
                j += 1
            out.append(sql[i : j + 1])
            i = j + 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j == -1:
                raise SqlValidationError("Unterminated /* comment.")
            out.append(" ")
            i = j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _blank_literals(sql: str) -> str:
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def validate_sql(raw_sql: str) -> ValidatedSql:
    if not raw_sql or not raw_sql.strip():
        raise SqlValidationError("Empty SQL.")
    if len(raw_sql) > MAX_SQL_CHARS:
        raise SqlValidationError(f"SQL is too long ({len(raw_sql)} chars, max {MAX_SQL_CHARS}). Simplify the query.")

    sql = strip_comments(raw_sql).strip()
    sql = re.sub(r";+\s*$", "", sql).strip()
    if not sql:
        raise SqlValidationError("Empty SQL.")

    scrubbed = _blank_literals(sql)
    if ";" in scrubbed:
        raise SqlValidationError("Only one statement is allowed (no ';' separators).")
    word = _FORBIDDEN_WORDS.search(scrubbed)
    if word:
        raise SqlValidationError(
            f"'{word.group(0)}' is not allowed. Use a single plain SELECT over the ai.* views "
            "(query hints such as OPTION are added automatically)."
        )
    if _SYSTEM_PREFIX.search(scrubbed):
        raise SqlValidationError("System catalogs and other databases are not accessible. Use only ai.* views.")

    try:
        statements = [s for s in sqlglot.parse(sql, read="tsql") if s is not None]
    except (ParseError, TokenError) as exc:
        raise SqlValidationError(f"SQL syntax error (T-SQL): {str(exc).splitlines()[0][:300]}") from exc
    if len(statements) != 1:
        raise SqlValidationError("Exactly one SELECT statement is required.")
    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise SqlValidationError("Only SELECT queries (optionally with CTEs / UNION) are allowed.")
    for node_type in _FORBIDDEN_NODES:
        if tree.find(node_type):
            raise SqlValidationError(f"{node_type.__name__} statements are not allowed; only SELECT.")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    views: set[str] = set()
    for table in tree.find_all(exp.Table):
        name = table.name
        if not name:
            raise SqlValidationError("Table-valued functions are not allowed; select FROM ai.<view>.")
        schema = (table.db or "").lower()
        if table.catalog:
            raise SqlValidationError("Cross-database references are not allowed. Use ai.<view>.")
        if not schema and name.lower() in cte_names:
            continue
        if schema != ALLOWED_SCHEMA:
            raise SqlValidationError(
                f"Table '{(table.db + '.' if table.db else '')}{name}' is not allowed. Only views of schema ai "
                "(e.g. ai.ledger_lines) can be queried; qualify every table with 'ai.'."
            )
        views.add(name.lower())
    if not views:
        raise SqlValidationError("The query must read from at least one ai.* view.")
    return ValidatedSql(sql=sql, views=tuple(sorted(views)))
