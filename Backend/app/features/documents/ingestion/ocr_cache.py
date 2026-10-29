"""Persistent cache of vision-OCR text, keyed by image bytes + OCR model + OCR prompt (see `OcrCache`)."""

import hashlib
import logging
import uuid
from pathlib import Path

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.features.documents.ingestion.ocr import SYSTEM_OCR_PROMPT, preprocess_signature
from app.features.documents.models import Document, OcrCache

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


async def put_cached_ocr(
    db: AsyncSession,
    key: str,
    text: str,
    rotation: int | None = None,
    document_id: uuid.UUID | None = None,
    source_filename: str | None = None,
    page_number: int | None = None,
) -> None:
    if not text:
        return
    try:
        values = {
            "cache_key": key,
            "text": text,
            "vision_model": vision_model_name(),
            "rotation": rotation,
            "document_id": document_id,
            "source_filename": source_filename,
            "page_number": page_number,
        }
        stmt = (
            insert(OcrCache)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["cache_key"],
                set_={
                    "document_id": document_id,
                    "source_filename": source_filename,
                    "page_number": page_number,
                    "rotation": rotation,
                    "text": text,
                },
            )
        )
        await db.execute(stmt)
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR cache write failed (%s).", exc)
        await db.rollback()


async def purge_document_ocr_cache(db: AsyncSession, document_id: uuid.UUID) -> int:
    """Deletes all OcrCache rows associated with a document.

    Matches by `document_id` and also computes cache keys from the document's rendered pages
    on disk so even legacy or unlinked entries are reliably wiped.
    """
    keys_to_delete: set[str] = set()
    doc = await db.get(Document, document_id)
    if doc and doc.file_path and Path(doc.file_path).exists():
        suffix = Path(doc.file_path).suffix.lower()
        if suffix == ".pdf":
            try:
                import pypdf
                from app.features.documents.ingestion.parser import render_pdf_page

                reader = pypdf.PdfReader(doc.file_path)
                for p_idx in range(len(reader.pages)):
                    rendered = render_pdf_page(doc.file_path, p_idx + 1)
                    if rendered and rendered.data:
                        keys_to_delete.add(ocr_cache_key(rendered.data))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not precompute PDF page cache keys: %s", exc)
        elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                data = Path(doc.file_path).read_bytes()
                keys_to_delete.add(ocr_cache_key(data))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not precompute image cache key: %s", exc)

    conditions = [OcrCache.document_id == document_id]
    if keys_to_delete:
        conditions.append(OcrCache.cache_key.in_(list(keys_to_delete)))

    stmt = delete(OcrCache).where(or_(*conditions))
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0


async def purge_all_ocr_cache(db: AsyncSession) -> int:
    """Deletes all entries from the OCR cache."""
    stmt = delete(OcrCache)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0

