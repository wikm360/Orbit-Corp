import uuid
import pytest

from app.features.db_connector.executor import QueryResult
from app.features.db_connector.models import DbQueryLog, QueryStatus
from app.features.db_connector.service import (
    get_query_stats,
    list_query_logs,
    query_accounting_db,
    record_feedback,
)


class MockGenerator:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.call_count = 0

    async def generate(self, question, hint_blocks, previous):
        resp = self._responses[self.call_count]
        self.call_count += 1
        return resp


@pytest.mark.asyncio
async def test_query_accounting_db_success(db_session, monkeypatch):
    # Mock executor.execute_query
    async def mock_execute(sql: str):
        return QueryResult(
            columns=["col1", "col2"],
            rows=[[1, "val1"]],
            truncated=False,
            duration_ms=25,
            data_as_of={"سال مالی": "1404"},
        )

    monkeypatch.setattr("app.features.db_connector.service.execute_query", mock_execute)

    gen = MockGenerator(["```sql\nSELECT TOP 1 * FROM ai.vouchers\n```"])
    result = await query_accounting_db(
        db_session,
        question="تست دریافت سند",
        generator=gen,
    )
    assert "نتیجه‌ی پرس‌وجو" in result
    assert "val1" in result

    # Check that a log was created
    logs = await list_query_logs(db_session)
    assert len(logs) == 1
    assert logs[0].status == QueryStatus.OK
    assert logs[0].sql_text == "SELECT TOP 1 * FROM ai.vouchers"


@pytest.mark.asyncio
async def test_query_accounting_db_repair_loop(db_session, monkeypatch):
    async def mock_execute(sql: str):
        return QueryResult(
            columns=["id"],
            rows=[[42]],
            truncated=False,
            duration_ms=10,
        )

    monkeypatch.setattr("app.features.db_connector.service.execute_query", mock_execute)

    # First attempt is invalid (bad schema), second is valid
    gen = MockGenerator([
        "SELECT * FROM FIN3.BadTable",
        "SELECT TOP 1 * FROM ai.vouchers",
    ])
    result = await query_accounting_db(
        db_session,
        question="تست اصلاح خودکار",
        generator=gen,
    )
    assert "نتیجه‌ی پرس‌وجو" in result
    assert "42" in result

    logs = await list_query_logs(db_session)
    assert len(logs) == 1
    assert logs[0].attempts == 2
    assert logs[0].status == QueryStatus.OK


@pytest.mark.asyncio
async def test_query_accounting_db_cannot_answer(db_session):
    # The first refusal is challenged once; a repeated refusal is accepted.
    gen = MockGenerator(["NO_SQL: اطلاعات انبار در این سامانه وجود ندارد"] * 2)
    result = await query_accounting_db(
        db_session,
        question="موجودی انبار چقدر است؟",
        generator=gen,
    )
    assert gen.call_count == 2
    assert "اطلاعات انبار" in result
    assert "نبودن داده نیست" in result

    logs = await list_query_logs(db_session)
    assert len(logs) == 1
    assert logs[0].status == QueryStatus.OK
    assert logs[0].sql_text is None


@pytest.mark.asyncio
async def test_record_feedback_and_stats(db_session):
    log = DbQueryLog(
        question="تست بازخورد",
        hint_keys=["h1"],
        sql_text="SELECT 1 FROM ai.vouchers",
        attempts=1,
        status=QueryStatus.OK,
        row_count=5,
        duration_ms=30,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    updated = await record_feedback(db_session, query_id=log.id, feedback=1, note="عالی بود")
    assert updated.feedback == 1
    assert updated.feedback_note == "عالی بود"

    stats = await get_query_stats(db_session)
    assert stats.total_queries == 1
    assert stats.successful_queries == 1
    assert stats.positive_feedback == 1



@pytest.mark.asyncio
async def test_first_refusal_is_challenged_and_can_become_sql(db_session, monkeypatch):
    async def mock_execute(sql: str, max_rows=None):
        return QueryResult(columns=["employee_name"], rows=[["الف"]], truncated=False, duration_ms=5)

    monkeypatch.setattr("app.features.db_connector.service.execute_query", mock_execute)
    seen = []

    class Gen:
        async def generate(self, question, hint_blocks, previous):
            seen.append(list(previous))
            return "NO_SQL: ستون وضعیت در دسترس نیست" if not previous else "SELECT employee_name FROM ai.payroll_monthly"

    result = await query_accounting_db(db_session, question="لیست حقوق در تیر 1405", generator=Gen())
    assert "الف" in result
    assert seen[1][0].raw.startswith("NO_SQL:")


@pytest.mark.asyncio
async def test_empty_result_retries_with_real_column_values(db_session, monkeypatch):
    calls = []

    async def mock_execute(sql: str, max_rows=None):
        calls.append(sql)
        if "دفتر" in sql and "department_name" in sql:
            return QueryResult(columns=["employee_name"], rows=[], truncated=False, duration_ms=5)
        return QueryResult(columns=["employee_name"], rows=[["الف"], ["ب"]], truncated=False, duration_ms=5)

    async def mock_probe(sql: str, max_rows=None):
        return QueryResult(columns=["department_name"], rows=[["امور مالی"], ["دفتر فنی"]], truncated=False, duration_ms=1)

    monkeypatch.setattr("app.features.db_connector.service.execute_query", mock_execute)
    monkeypatch.setattr("app.features.db_connector.summary.execute_query", mock_probe)
    seen = []

    class Gen:
        async def generate(self, question, hint_blocks, previous):
            seen.append(list(previous))
            if not previous:
                return "SELECT employee_name FROM ai.payroll_monthly WHERE department_name LIKE N'%دفتر مرکزی%'"
            return "SELECT employee_name FROM ai.payroll_monthly WHERE cost_center LIKE N'%دفتر%مرکزی%'"

    result = await query_accounting_db(db_session, question="حقوق دفتر مرکزی", generator=Gen())
    assert "الف" in result
    assert "امور مالی" in seen[1][0].error  # the repair prompt carries the real department values
    logs = await list_query_logs(db_session)
    assert logs[0].row_count == 2 and logs[0].attempts == 2


@pytest.mark.asyncio
async def test_persistent_empty_result_is_reported_as_empty_not_error(db_session, monkeypatch):
    async def mock_execute(sql: str, max_rows=None):
        return QueryResult(columns=["employee_name"], rows=[], truncated=False, duration_ms=5)

    monkeypatch.setattr("app.features.db_connector.service.execute_query", mock_execute)
    monkeypatch.setattr("app.features.db_connector.summary.execute_query", mock_execute)

    class Gen:
        async def generate(self, question, hint_blocks, previous):
            return "SELECT employee_name FROM ai.payroll_monthly WHERE department_name = N'ناموجود'"

    result = await query_accounting_db(db_session, question="x", generator=Gen())
    assert "۰ ردیف" in result and "نگو «داده‌ای وجود ندارد»" in result
