"""Persistent cache of vision-OCR text, keyed by image bytes + OCR model + OCR prompt (see `OcrCache`)."""

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.features.documents.ingestion.ocr import SYSTEM_OCR_PROMPT, preprocess_signature
from app.features.documents.models import OcrCache

logger = logging.getLogger(__name__)


def vision_model_name() -> str:
    settings = get_settings()
    return getattr(settings, "llm_vision_model", None) or getattr(settings, "llm_model", "gpt-4o")


def ocr_cache_key(image_bytes: bytes) -> str:
    """sha256(image) + a short hash of (model, prompt, pre-processing): changing any of them must not serve stale text."""
    reader = hashlib.sha256(
        f"{vision_model_name()}\n{SYSTEM_OCR_PROMPT}\n{preprocess_signature()}".encode()
    ).hexdigest()[:16]
    return f"{hashlib.sha256(image_bytes).hexdigest()}:{reader}"


async def get_cached_ocr(db: AsyncSession, key: str) -> tuple[str, int | None] | None:
    """`(text, rotation)` of a cached read, or None."""
    try:
        row = (await db.execute(select(OcrCache.text, OcrCache.rotation).where(OcrCache.cache_key == key))).first()
        return None if row is None else (row[0], row[1])
    except Exception as exc:  # noqa: BLE001 - a cache problem must never fail ingestion
        logger.warning("OCR cache lookup failed (%s); reading the image instead.", exc)
        await db.rollback()
        return None


async def put_cached_ocr(db: AsyncSession, key: str, text: str, rotation: int | None = None) -> None:
    if not text:
        return
    try:
        await db.execute(
            insert(OcrCache)
            .values(cache_key=key, text=text, vision_model=vision_model_name(), rotation=rotation)
            .on_conflict_do_nothing(index_elements=["cache_key"])
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR cache write failed (%s).", exc)
        await db.rollback()
