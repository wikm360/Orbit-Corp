import pytest

from app.features.db_connector.generator import (
    Attempt,
    CannotAnswer,
    build_messages,
    extract_sql,
)


def test_extract_sql_from_markdown():
    text = "Here is the query:\n```sql\nSELECT TOP 5 * FROM ai.vouchers\n```\nHope it helps."
    assert extract_sql(text) == "SELECT TOP 5 * FROM ai.vouchers"


def test_extract_sql_cannot_answer():
    text = "NO_SQL: داده‌های فروش در سیستم وجود ندارد"
    with pytest.raises(CannotAnswer) as exc:
        extract_sql(text)
    assert "داده‌های فروش" in str(exc.value)


def test_build_messages():
    msgs = build_messages(
        question="سود شرکت در ۱۴۰۴ چقدر است؟",
        hint_blocks=["block 1", "block 2"],
        previous=[Attempt(sql="SELECT * FROM bad", error="Validation error")],
    )
    assert len(msgs) == 4
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"
    assert msgs[3]["role"] == "user"
    assert "Validation error" in msgs[3]["content"]

