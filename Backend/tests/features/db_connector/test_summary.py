import pytest

from app.features.db_connector.executor import QueryResult
from app.features.db_connector.formatter import format_query_result
from app.features.db_connector.summary import build_totals_sql, compute_totals


def test_totals_sql_wraps_without_order_by_and_keeps_cte():
    sql = build_totals_sql("SELECT employee_name, net_pay FROM ai.payroll_monthly WHERE issue_year_month = 140504 ORDER BY net_pay DESC", ["net_pay"])
    assert "COUNT(*)" in sql and "SUM(CAST([net_pay] AS NUMERIC(38, 2)))" in sql and "ORDER BY" not in sql
    with_cte = build_totals_sql("WITH a AS (SELECT 1 AS x) SELECT x FROM a", [])
    assert with_cte.startswith("WITH a AS")


def test_totals_sql_skipped_for_top_and_union():
    assert build_totals_sql("SELECT TOP 10 a FROM ai.x", []) is None
    assert build_totals_sql("SELECT a FROM ai.x UNION ALL SELECT a FROM ai.y", []) is None


@pytest.mark.asyncio
async def test_truncated_result_gets_exact_total(monkeypatch):
    async def fake_execute(sql, max_rows=None):
        return QueryResult(columns=["n", "s1"], rows=[[526, 1234500]], truncated=False, duration_ms=1)

    monkeypatch.setattr("app.features.db_connector.summary.execute_query", fake_execute)
    result = QueryResult(columns=["employee_name", "net_pay"], rows=[["الف", 10]] * 500, truncated=True, duration_ms=5)
    totals = await compute_totals("SELECT employee_name, net_pay FROM ai.payroll_monthly", result, 60)
    assert totals.total_rows == 526
    assert totals.column_sums == {"net_pay": 1234500}


@pytest.mark.asyncio
async def test_full_fetch_sums_in_python_and_small_results_skip():
    big = QueryResult(columns=["name", "net_pay"], rows=[["a", 10]] * 100, truncated=False, duration_ms=1)
    totals = await compute_totals("SELECT 1", big, 60)
    assert totals.total_rows == 100 and totals.column_sums == {"net_pay": 1000}
    small = QueryResult(columns=["name"], rows=[["a"]] * 5, truncated=False, duration_ms=1)
    assert await compute_totals("SELECT 1", small, 60) is None


def test_formatter_tells_model_the_true_total():
    rows = [["الف", 100]] * 100
    text = format_query_result(columns=["name", "net_pay"], rows=rows, sql="x", duration_ms=1, truncated=True, total_rows=526, column_sums={"net_pay": 5000})
    assert "526" in text and "جمع ستون «net_pay»" in text
    assert "تعداد کل ردیف‌ها: 526" in text
