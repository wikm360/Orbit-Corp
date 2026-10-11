from app.features.db_connector.formatter import (
    format_cell,
    format_currency_value,
    format_query_result,
    is_money_column,
)


def test_is_money_column():
    assert is_money_column("total_debit") is True
    assert is_money_column("amount") is True
    assert is_money_column("contract_net_amount") is True
    assert is_money_column("gross_pay") is True
    assert is_money_column("voucher_id") is False
    assert is_money_column("fiscal_year") is False
    assert is_money_column("line_count") is False


def test_format_currency_value():
    assert "ریال" in format_currency_value(5000)
    # 50 million Rials = 5 million Tomans
    formatted_50m = format_currency_value(50_000_000)
    assert "میلیون تومان" in formatted_50m

    # 50 billion Rials = 5 billion Tomans
    formatted_50b = format_currency_value(50_000_000_000)
    assert "میلیارد تومان" in formatted_50b


def test_format_query_result():
    res = format_query_result(
        columns=["voucher_id", "total_debit", "jalali_date"],
        rows=[[101, 15_000_000_000, "1404/05/10"]],
        sql="SELECT TOP 1 * FROM ai.vouchers",
        duration_ms=45,
        query_id="test-uuid",
        truncated=False,
        data_as_of={"سال مالی جاری": "1404"},
    )
    assert "SELECT TOP 1 * FROM ai.vouchers" in res
    assert "101" in res
    assert "میلیارد تومان" in res
    assert "45 میلی‌ثانیه" in res
    assert "test-uuid" in res
    assert "1404" in res

