"""Accounting data inside chat messages: how it is recognised and what readers without accounting access see instead."""

from app.features.chat.schemas import MessageRead

FINANCIAL_PLACEHOLDER = "[محتوای مالی - برای مشاهده نیاز به مجوز دسترسی مالی دارید]"

_FINANCIAL_ARTIFACT_TYPES = {"sql_result"}


def has_financial_artifacts(artifacts: list[dict]) -> bool:
    return any(isinstance(a, dict) and a.get("type") in _FINANCIAL_ARTIFACT_TYPES for a in artifacts or [])


def messages_for_reader(messages, can_use_accounting: bool) -> list[MessageRead]:
    """Messages as the reader may see them: accounting replies become a placeholder (text, sources and artifacts)."""
    result = []
    for message in messages:
        read = MessageRead.model_validate(message)
        if read.contains_financial and not can_use_accounting:
            read = read.model_copy(update={"content": FINANCIAL_PLACEHOLDER, "sources": [], "artifacts": []})
        result.append(read)
    return result
