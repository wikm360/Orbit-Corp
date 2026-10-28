"""High-level service for executing natural-language questions against the Rahkaran accounting database.

Coordinates:
1. Schema-hints retrieval (hybrid vector + BM25)
2. T-SQL generation and multi-step validation/repair loop
3. Safe query execution on SQL Server with row limits and timeouts
4. Persian accounting result formatting (Rial to Toman/billion Toman, markdown tables)
5. Comprehensive audit logging into db_query_logs and user feedback collection
"""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import model_registry  # noqa: F401
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.features.db_connector.artifacts import build_sql_result_artifact
from app.features.db_connector.executor import DbExecutionError, QueryResult, data_freshness, execute_query
from app.features.db_connector.formatter import format_query_result
from app.features.db_connector.generator import NO_SQL_PREFIX, Attempt, CannotAnswer, SqlGenerator, extract_sql, get_sql_generator
from app.features.db_connector.hints import retrieve_hints
from app.features.db_connector.models import DbQueryLog, QueryStatus
from app.features.db_connector.schemas import DbQueryStats
from app.features.db_connector.summary import compute_totals, empty_result_feedback
from app.features.db_connector.sql_validator import SqlValidationError, validate_sql

logger = logging.getLogger(__name__)


MODEL_NOTE = (
    "توجه: کاربر جدول کامل این نتیجه و کوئری SQL مرجع را همراه پاسخ تو در رابط کاربری می‌بیند. پاسخ را کوتاه و دقیق بنویس، "
    "اعداد را عیناً از همین جدول نقل کن (نه از حافظه)، نام و واحد ستون‌ها را درست به کار ببر (مثلاً دستمزد ماهانه ≠ مزد پایه)، "
    "و اگر داده‌ها موقت یا ناقص‌اند صریحاً بگو. جدول را دوباره در پاسخ تکرار نکن. "
    "درباره‌ی تعداد ردیف‌های جدول یا ردیف‌های نمایش‌داده‌شده خودت عدد نساز؛ فقط «تعداد کل ردیف‌ها»ی ذکرشده در نتیجه را نقل کن. "
    "وضعیت قطعی/موقت فقط برای اسناد حسابداری مطرح است؛ برای حقوق ماهانه آن را نگو."
)


_REFUSAL_CHALLENGE = (
    "فقط اگر هیچ view مرتبطی در دانش بالا نیست NO_SQL بده. برای پرسش کلی پیش‌فرض بگذار (آخرین ماه/سال موجود، همه‌ی ردیف‌ها، ستون‌های اصلی) "
    "و یک SELECT بنویس. «وضعیت قطعی/موقت» فقط برای اسناد حسابداری است و برای حقوق لازم نیست. اگر باز هم ممکن نیست، دقیقاً همان NO_SQL را با دلیل واقعی تکرار کن."
)


@dataclass
class AccountingAnswer:
    """What the accounting tool produced: `text` goes to the model; `artifact` (exact SQL + rows) goes to the client with the reply."""

    text: str
    artifact: dict | None = None
    query_id: str | None = None
    status: QueryStatus = QueryStatus.OK


async def query_accounting_db(
    db: AsyncSession,
    *,
    question: str,
    user_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    generator: SqlGenerator | None = None,
) -> str:
    """Answers a business question using the accounting database and returns user-ready Markdown (with the SQL block)."""
    answer = await run_accounting_query(
        db, question=question, user_id=user_id, conversation_id=conversation_id, generator=generator, include_sql_in_text=True
    )
    return answer.text


async def run_accounting_query(
    db: AsyncSession,
    *,
    question: str,
    user_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    generator: SqlGenerator | None = None,
    include_sql_in_text: bool = False,
) -> AccountingAnswer:
    """Retrieve hints -> generate/validate/execute SQL (with repair) -> log -> return model text + client artifact."""
    settings = get_settings()
    generator = generator or get_sql_generator()
    max_attempts = max(1, settings.rahkaran_sql_max_attempts)

    # 1. Retrieve knowledge chunks relevant to the question
    retrieved = await retrieve_hints(db, question)
    hint_blocks = retrieved.blocks
    hint_keys = retrieved.keys

    previous_attempts: list[Attempt] = []
    last_sql: str | None = None
    last_error: str | None = None
    query_result: QueryResult | None = None
    empty_fallback: tuple[str, QueryResult] | None = None
    status: QueryStatus = QueryStatus.ERROR
    started_total = time.monotonic()

    # 2. Generation & repair loop
    for attempt_no in range(1, max_attempts + 1):
        try:
            raw = await generator.generate(question, hint_blocks, previous_attempts)
            sql = extract_sql(raw)
        except CannotAnswer as exc:
            if attempt_no == 1 and max_attempts > 1:
                # Refusals are often lazy ("status column unavailable"); ask once for a default-based query before giving up.
                previous_attempts.append(Attempt(sql="", error=_REFUSAL_CHALLENGE, raw=f"{NO_SQL_PREFIX} {exc.reason}"))
                continue
            # Model explicitly identified this query as unanswerable with the available schema
            duration_ms = int((time.monotonic() - started_total) * 1000)
            log = DbQueryLog(
                user_id=user_id,
                conversation_id=conversation_id,
                question=question,
                hint_keys=hint_keys,
                sql_text=None,
                attempts=attempt_no,
                status=QueryStatus.OK,
                error_message=f"unanswerable: {exc.reason}"[:1000],
                row_count=0,
                truncated=False,
                duration_ms=duration_ms,
            )
            db.add(log)
            await db.commit()
            return AccountingAnswer(
                text=(
                    "سیستم برای این پرسش کوئری نساخت (این به معنی نبودن داده نیست). "
                    f"دلیل اعلام‌شده: {exc.reason}\n"
                    "همین را صادقانه به کاربر بگو و از او بخواه پرسش را دقیق‌تر بنویسد (ماه/سال، نام واحد، مرکز هزینه یا قرارداد). "
                    "نتیجه‌ای از خودت نساز و نگو «داده‌ای وجود ندارد»."
                ),
                query_id=str(log.id),
                status=QueryStatus.OK,
            )
        except Exception as exc:
            logger.warning("SQL generation failed on attempt %d: %s", attempt_no, exc)
            last_error = f"خطا در تولید کوئری: {exc}"
            previous_attempts.append(Attempt(sql=last_sql or "", error=str(exc)))
            continue

        last_sql = sql

        # 3. Static AST & syntax validation
        try:
            validated = validate_sql(sql)
        except SqlValidationError as val_err:
            logger.info("SQL validation rejected attempt %d: %s", attempt_no, val_err)
            last_error = str(val_err)
            status = QueryStatus.REJECTED
            previous_attempts.append(Attempt(sql=sql, error=f"Validation failed: {val_err}"))
            continue

        # 4. Safe execution on SQL Server
        try:
            executed = await execute_query(validated.sql)
        except DbExecutionError as exec_err:
            logger.info("SQL execution error on attempt %d: %s", attempt_no, exec_err)
            last_error = exec_err.message
            status = QueryStatus.ERROR
            previous_attempts.append(Attempt(sql=sql, error=f"SQL Server execution error: {exec_err.message}"))
            continue

        # A name filter that matches nothing usually means a wrong column/value, not missing data: retry once with the real values.
        if executed.row_count == 0 and empty_fallback is None and attempt_no < max_attempts:
            feedback = await empty_result_feedback(validated.sql)
            if feedback:
                empty_fallback = (sql, executed)
                previous_attempts.append(Attempt(sql=sql, error=feedback))
                continue

        query_result = executed
        status = QueryStatus.OK
        last_error = None
        break

    if query_result is None and empty_fallback is not None:
        # The retry failed or never produced a result: report the first (empty) outcome rather than an error.
        last_sql, query_result = empty_fallback
        status = QueryStatus.OK
        last_error = None

    totals = await compute_totals(last_sql or "", query_result, settings.rahkaran_db_rows_to_model) if query_result is not None else None
    if totals is not None and query_result is not None:
        query_result.total_rows = totals.total_rows
        query_result.column_sums = totals.column_sums

    total_duration_ms = int((time.monotonic() - started_total) * 1000)

    # 5. Persist the log entry for audit and evaluation
    log = DbQueryLog(
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        hint_keys=hint_keys,
        sql_text=last_sql,
        attempts=len(previous_attempts) + (1 if status == QueryStatus.OK else 0),
        status=status,
        error_message=last_error,
        row_count=query_result.row_count if query_result else None,
        truncated=query_result.truncated if query_result else False,
        duration_ms=total_duration_ms,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    # 6. Format the output for the assistant
    if status == QueryStatus.OK and query_result is not None:
        freshness = await data_freshness()
        text = format_query_result(
            columns=query_result.columns,
            rows=query_result.rows,
            sql=last_sql or "",
            duration_ms=query_result.duration_ms,
            query_id=str(log.id),
            truncated=query_result.truncated,
            data_as_of=freshness,
            include_sql=include_sql_in_text,
            total_rows=query_result.total_rows,
            column_sums=query_result.column_sums,
        )
        if not include_sql_in_text:
            text = f"{MODEL_NOTE}\n\n{text}"
        artifact = build_sql_result_artifact(
            query_id=str(log.id),
            question=question,
            sql=last_sql or "",
            columns=query_result.columns,
            rows=query_result.rows,
            truncated=query_result.truncated,
            duration_ms=query_result.duration_ms,
            data_as_of=freshness,
            max_rows=settings.rahkaran_artifact_max_rows,
            total_rows=query_result.total_rows,
        )
        return AccountingAnswer(text=text, artifact=artifact, query_id=str(log.id), status=status)

    # On failure after max attempts:
    if last_error and ("timed out" in last_error.lower() or "timeout" in last_error.lower()):
        reason = "زمان اجرای این استعلام به دلیل حجم بالای داده یا پیچیدگی محاسبات بیش از سقف مجاز (۳۰ ثانیه) طول کشید؛ لطفاً بازه زمانی مشخص‌تری تعیین کنید."
    else:
        reason = last_error or "عدم موفقیت در تولید و اجرای کوئری معتبر"
    return AccountingAnswer(
        text=(
            f"⚠️ **خطا در دریافت اطلاعات از پایگاه داده راهکاران**\n\n"
            f"علت: {reason}\n\n"
            f"> شناسه پیگیری: `{log.id}` (می‌توانید پرسش را با جزئیات دقیق‌تر بازنویسی کنید)."
        ),
        query_id=str(log.id),
        status=status,
    )


async def record_feedback(
    db: AsyncSession,
    *,
    query_id: uuid.UUID,
    feedback: int,
    note: str | None = None,
) -> DbQueryLog:
    """Saves user rating (+1 thumbs up, -1 thumbs down) on a specific query execution."""
    stmt = select(DbQueryLog).where(DbQueryLog.id == query_id)
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()
    if log is None:
        raise NotFoundError("Query log not found")

    log.feedback = feedback if feedback != 0 else None
    log.feedback_note = note
    await db.commit()
    await db.refresh(log)
    return log


async def list_query_logs(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    status: QueryStatus | None = None,
) -> list[DbQueryLog]:
    stmt = select(DbQueryLog).order_by(DbQueryLog.created_at.desc())
    if status is not None:
        stmt = stmt.where(DbQueryLog.status == status)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_query_stats(db: AsyncSession) -> DbQueryStats:
    total = await db.scalar(select(func.count(DbQueryLog.id))) or 0
    ok = await db.scalar(select(func.count(DbQueryLog.id)).where(DbQueryLog.status == QueryStatus.OK)) or 0
    rejected = await db.scalar(select(func.count(DbQueryLog.id)).where(DbQueryLog.status == QueryStatus.REJECTED)) or 0
    err = await db.scalar(select(func.count(DbQueryLog.id)).where(DbQueryLog.status == QueryStatus.ERROR)) or 0

    pos = await db.scalar(select(func.count(DbQueryLog.id)).where(DbQueryLog.feedback == 1)) or 0
    neg = await db.scalar(select(func.count(DbQueryLog.id)).where(DbQueryLog.feedback == -1)) or 0

    avg_dur = await db.scalar(select(func.avg(DbQueryLog.duration_ms)))

    return DbQueryStats(
        total_queries=total,
        successful_queries=ok,
        rejected_queries=rejected,
        error_queries=err,
        positive_feedback=pos,
        negative_feedback=neg,
        avg_duration_ms=float(avg_dur) if avg_dur is not None else None,
    )
