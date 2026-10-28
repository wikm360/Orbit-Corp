"""Cooperative cancellation of a document's ingestion.

Cancelling sets `Document.status = CANCELLED` (what the UI shows) and a short-lived Redis flag. The worker checks the
status between pipeline steps and the flag before every paid OCR call, so a cancelled scan stops spending money within
one in-flight request instead of finishing a 200-page document.
"""
import asyncio
import uuid

from redis import Redis

from app.core.config import get_settings

_redis = Redis.from_url(get_settings().redis_url)
_FLAG_TTL_SECONDS = 24 * 3600


class IngestionCancelled(Exception):
    """Raised inside the pipeline when the document was cancelled or deleted while it was being processed."""


def _key(document_id: uuid.UUID) -> str:
    return f"ingestion:cancel:{document_id}"


async def request_cancel(document_id: uuid.UUID) -> None:
    await asyncio.to_thread(_redis.set, _key(document_id), "1", ex=_FLAG_TTL_SECONDS)


async def clear_cancel(document_id: uuid.UUID) -> None:
    await asyncio.to_thread(_redis.delete, _key(document_id))


async def is_cancel_requested(document_id: uuid.UUID) -> bool:
    try:
        return bool(await asyncio.to_thread(_redis.exists, _key(document_id)))
    except Exception:  # noqa: BLE001 - a Redis hiccup must not fail ingestion; the status check still applies
        return False
