"""Writes T-SQL for a question with the SQL model, given the core prompt and the retrieved hints; repairs it from error feedback."""

import re
from dataclasses import dataclass
from typing import Protocol

from app.features.db_connector.hints import load_core_prompt
from app.providers.llm_provider import get_sql_llm_provider

NO_SQL_PREFIX = "NO_SQL:"

_OUTPUT_RULES = """\
فرمت خروجی: فقط یک بلوک ```sql ... ``` شامل دقیقاً یک دستور SELECT (T-SQL) بنویس و هیچ توضیح دیگری نده.
اگر پرسش با داده‌های موجود قابل پاسخ نیست (مثلاً داده‌اش ثبت نمی‌شود) فقط یک خط بنویس: NO_SQL: <دلیل کوتاه به فارسی>"""


class CannotAnswer(Exception):
    """The model decided the question cannot be answered from the available data."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class Attempt:
    sql: str
    error: str
    # Set when the earlier answer was not SQL (e.g. a NO_SQL refusal) so it is replayed as given and `error` is sent as the follow-up.
    raw: str | None = None


class SqlGenerator(Protocol):
    async def generate(self, question: str, hint_blocks: list[str], previous: list[Attempt]) -> str: ...


def extract_sql(text: str) -> str:
    text = text.strip()
    if text.upper().startswith(NO_SQL_PREFIX):
        raise CannotAnswer(text[len(NO_SQL_PREFIX) :].strip() or "این پرسش با داده‌های موجود قابل پاسخ نیست.")
    match = re.search(r"```(?:sql|tsql|t-sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    sql = (match.group(1) if match else text).strip()
    if not sql:
        raise CannotAnswer("مدل SQL تولید نکرد.")
    return sql


def build_messages(question: str, hint_blocks: list[str], previous: list[Attempt]) -> list[dict]:
    knowledge = "\n\n---\n\n".join(hint_blocks)
    system = f"{load_core_prompt()}\n\n{_OUTPUT_RULES}\n\n# دانش بازیابی‌شده درباره‌ی view ها و مفاهیم\n\n{knowledge}"
    messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": f"پرسش: {question}"}]
    for attempt in previous:
        if attempt.raw is not None:
            messages.append({"role": "assistant", "content": attempt.raw})
            messages.append({"role": "user", "content": attempt.error})
            continue
        messages.append({"role": "assistant", "content": f"```sql\n{attempt.sql}\n```"})
        messages.append({
            "role": "user",
            "content": f"این SQL خطا داد: {attempt.error}\nSQL اصلاح‌شده را با همان فرمت بنویس. فقط از ستون‌ها و view هایی استفاده کن که در دانش بالا آمده‌اند.",
        })
    return messages


class LLMSqlGenerator:
    async def generate(self, question: str, hint_blocks: list[str], previous: list[Attempt]) -> str:
        provider = get_sql_llm_provider()
        content = ""
        async for event in provider.stream_chat(build_messages(question, hint_blocks, previous)):
            if event["type"] == "content":
                content += event["delta"]
        return extract_sql(content)


def get_sql_generator() -> SqlGenerator:
    return LLMSqlGenerator()
