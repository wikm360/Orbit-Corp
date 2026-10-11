import pytest

from app.features.db_connector.sql_validator import (
    SqlValidationError,
    strip_comments,
    validate_sql,
)


def test_strip_comments():
    sql = "SELECT /* block comment */ col1, col2 -- inline comment\nFROM ai.vouchers WHERE x = 'foo--bar' AND y = '/*baz*/'"
    stripped = strip_comments(sql)
    assert "/* block comment */" not in stripped
    assert "-- inline comment" not in stripped
    assert "'foo--bar'" in stripped
    assert "'/*baz*/'" in stripped


def test_validate_sql_valid_simple():
    sql = "SELECT TOP 10 voucher_id, voucher_date, total_debit FROM ai.vouchers WHERE is_valid_for_reports = 1"
    res = validate_sql(sql)
    assert res.views == ("vouchers",)
    assert "SELECT TOP 10" in res.sql


def test_validate_sql_with_cte():
    sql = """
    WITH cost_cte AS (
        SELECT contract_name, SUM(amount) AS total_cost
        FROM ai.cost_lines
        WHERE fiscal_year = 1404
        GROUP BY contract_name
    )
    SELECT TOP 5 * FROM cost_cte ORDER BY total_cost DESC
    """
    res = validate_sql(sql)
    assert res.views == ("cost_lines",)


def test_validate_sql_persian_strings():
    sql = "SELECT TOP 5 * FROM ai.ledger_lines WHERE counterparty_name LIKE N'%جهاد نصر%' AND fiscal_year = 1404"
    res = validate_sql(sql)
    assert res.views == ("ledger_lines",)


@pytest.mark.parametrize(
    "bad_sql, expected_error_fragment",
    [
        ("", "Empty SQL"),
        ("   ", "Empty SQL"),
        ("DROP TABLE ai.vouchers", "only select"),
        ("INSERT INTO ai.vouchers (voucher_id) VALUES (1)", "only select"),
        ("UPDATE ai.vouchers SET voucher_id = 1", "only select"),
        ("DELETE FROM ai.vouchers", "only select"),
        ("SELECT 1; SELECT 2", "Only one statement is allowed"),
        ("EXEC sp_who", "'exec' is not allowed"),
        ("SELECT * INTO #temp FROM ai.vouchers", "Into statements are not allowed"),
        ("SELECT * FROM sys.tables", "System catalogs and other databases are not accessible"),
        ("SELECT * FROM FIN3.Voucher", "Only views of schema ai"),
        ("SELECT * FROM ai.vouchers OPTION (MAXDOP 1)", "not allowed"),
        ("SELECT * FROM OPENROWSET('SQLNCLI', 'x', 'select 1')", "not allowed"),
        ("SELECT 1", "The query must read from at least one ai.* view"),
    ],
)
def test_validate_sql_rejections(bad_sql, expected_error_fragment):
    with pytest.raises(SqlValidationError) as exc:
        validate_sql(bad_sql)
    assert expected_error_fragment.lower() in str(exc.value).lower()
