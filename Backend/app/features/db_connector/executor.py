"""Runs validated SELECTs on the Rahkaran SQL Server with the read-only login, in a worker thread (pymssql is synchronous)."""

import asyncio
import datetime
import decimal
import re
import time
import uuid
from dataclasses import dataclass, field

import pymssql

from app.core.config import get_settings

ROWGOAL_HINT = "OPTION (USE HINT('DISABLE_OPTIMIZER_ROWGOAL'))"
_FRESHNESS_TTL_SECONDS = 600


class DbExecutionError(RuntimeError):
    """Execution failed; `message` is safe to show to the model for a repair attempt."""

    def __init__(self, message: str, *, timeout: bool = False):
        super().__init__(message)
        self.message = message
        self.timeout = timeout


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]  # JSON-safe values
    truncated: bool  # more rows existed than max_rows
    duration_ms: int
    data_as_of: dict[str, str] = field(default_factory=dict)
    # Exact size of the whole result and sums of its money columns, when the fetched rows are only part of it (see summary.compute_totals).
    total_rows: int | None = None
    column_sums: dict[str, float | int] = field(default_factory=dict)

    @property
    def row_count(self) -> int:
        return len(self.rows)


def _jsonable(value):
    if isinstance(value, decimal.Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _connect():
    s = get_settings()
    return pymssql.connect(
        s.rahkaran_db_host,
        user=s.rahkaran_db_user,
        password=s.rahkaran_db_password,
        database=s.rahkaran_db_name,
        port=s.rahkaran_db_port,
        charset="UTF-8",
        login_timeout=15,
        timeout=s.rahkaran_db_query_timeout_seconds,
        autocommit=True,
    )


def _clean_pymssql_error(exc: pymssql.Error) -> tuple[str, bool]:
    text = str(exc)
    code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else None
    is_timeout = code == 20047 or "timeout" in text.lower() or "timed out" in text.lower()

    if is_timeout:
        msg = (
            "Query timed out (>30s). The query execution was too heavy to complete within the time limit. "
            "Please optimize the query (e.g. by applying narrower date/period filters, using TOP, or avoiding full-table scans)."
        )
        return msg, True

    if len(exc.args) > 1:
        raw_msg = exc.args[1]
        msg = raw_msg.decode("utf-8", errors="replace") if isinstance(raw_msg, bytes) else str(raw_msg)
    else:
        msg = text

    # Strip FreeTDS / DB-Lib boilerplate wrappers while preserving the actual database error message
    msg = re.sub(r"DB-Lib error message \d+, severity \d+:\s*", "", msg)
    msg = re.sub(r"Net-Lib error during .*?\n", "", msg)
    msg = re.sub(r"DB-Library:?\s*", "", msg)
    clean = msg.strip().replace("\n", " ")
    return clean[:400] or "SQL Server error", False


def _run_sync(sql: str, max_rows: int) -> tuple[list[str], list[list], bool]:
    conn = _connect()
    try:
        cur = conn.cursor()
        # Server-side cap on rows produced (+1 to detect truncation); the connection is closed afterwards so it cannot leak.
        cur.execute(f"SET ROWCOUNT {int(max_rows) + 1}")
        cur.execute(f"{sql}\n{ROWGOAL_HINT}")
        columns = [d[0] or f"col{i + 1}" for i, d in enumerate(cur.description or [])]
        fetched = cur.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        rows = [[_jsonable(v) for v in row] for row in fetched[:max_rows]]
        return columns, rows, truncated
    except pymssql.Error as exc:
        readable, timeout = _clean_pymssql_error(exc)
        raise DbExecutionError(readable, timeout=timeout) from exc
    finally:
        conn.close()


_freshness_cache: tuple[float, dict[str, str]] | None = None


def _freshness_sync() -> dict[str, str]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT item, value FROM ai.data_freshness")
        return {str(item): str(value) for item, value in cur.fetchall() if value is not None}
    finally:
        conn.close()


async def data_freshness() -> dict[str, str]:
    """Latest-data facts (cached): lets answers say how current the snapshot is. Never raises."""
    global _freshness_cache
    now = time.monotonic()
    if _freshness_cache and now - _freshness_cache[0] < _FRESHNESS_TTL_SECONDS:
        return _freshness_cache[1]
    try:
        info = await asyncio.to_thread(_freshness_sync)
    except Exception:  # freshness is a nicety, never a failure reason
        return _freshness_cache[1] if _freshness_cache else {}
    _freshness_cache = (now, info)
    return info


async def execute_query(sql: str, max_rows: int | None = None) -> QueryResult:
    """Execute an already validated statement. Raises DbExecutionError on any database error."""
    settings = get_settings()
    started = time.monotonic()
    try:
        columns, rows, truncated = await asyncio.to_thread(_run_sync, sql, max_rows or settings.rahkaran_db_max_rows)
    except DbExecutionError:
        raise
    except Exception as exc:  # connection refused, DNS, ...
        raise DbExecutionError(f"Could not reach the accounting database: {type(exc).__name__}") from exc
    return QueryResult(columns=columns, rows=rows, truncated=truncated, duration_ms=int((time.monotonic() - started) * 1000))
