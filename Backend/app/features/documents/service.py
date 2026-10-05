import hashlib
import logging
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from redis import Redis
from rq import Queue
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.features.documents.ingestion.parser import SUPPORTED_EXTENSIONS
from app.features.documents.ingestion.reconstructor import (
    cleanup_reconstructed_files,
    get_reconstructed_txt_path,
    load_reconstructed_document,
)
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.features.retrieval.access_filter import accessible_documents_filter

settings = get_settings()
_redis_conn = Redis.from_url(settings.redis_url)
_queue = Queue(settings.ingestion_queue_name, connection=_redis_conn)

logger = logging.getLogger(__name__)

try:
    import tiktoken

    _token_encoding = tiktoken.get_encoding("cl100k_base")
except Exception as exc:  # pragma: no cover - offline environments
    logger.warning("Tiktoken encoding cl100k_base not available offline (%s). Using word-count estimate.", exc)
    _token_encoding = None


def _count_tokens(text: str) -> int:
    if not text:
        return 0
    if _token_encoding is not None:
        try:
            return len(_token_encoding.encode(text))
        except Exception:
            pass
    # Same 0.75 words/token estimate used by the ingestion chunker's offline fallback.
    return int(len(text.split()) / 0.75)


async def list_project_documents(db: AsyncSession, project_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def list_conversation_documents(db: AsyncSession, conversation_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.conversation_id == conversation_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    return document


def _validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise BadRequestError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return suffix


def _hash_bytes(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _store_file(suffix: str, file_bytes: bytes) -> str:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{suffix}"
    file_path = upload_dir / stored_name
    file_path.write_bytes(file_bytes)
    return str(file_path)


def _enqueue_ingestion(document: Document) -> None:
    _queue.enqueue(
        "app.features.documents.ingestion.pipeline.run_ingestion_pipeline_sync",
        document.id,
        document.file_path,
        job_timeout=600,
    )


async def _find_reusable_document(db: AsyncSession, content_hash: str) -> Document | None:
    """A previously ingested document with byte-identical content, if any.

    Its stored file is reused (never rewritten to disk) regardless of which
    project/conversation it originally belonged to — content addressing by
    hash doesn't leak anything, since each Document row still has its own
    independently access-controlled scope and chunks.
    """
    result = await db.execute(
        select(Document)
        .where(Document.content_hash == content_hash, Document.status == DocumentStatus.READY)
        .order_by(Document.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _copy_chunks(db: AsyncSession, source: Document, target: Document) -> None:
    result = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == source.id))
    for chunk in result.scalars().all():
        db.add(
            DocumentChunk(
                document_id=target.id,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                embedding=chunk.embedding,
                chunk_metadata=chunk.chunk_metadata,
            )
        )
    await db.commit()


async def _create_document(
    db: AsyncSession,
    *,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    uploaded_by: uuid.UUID,
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID | None,
) -> Document:
    suffix = _validate_extension(filename)
    content_hash = _hash_bytes(file_bytes)
    reusable = await _find_reusable_document(db, content_hash)

    # Identical bytes already on disk somewhere: point at that file instead
    # of writing (and permanently storing) a duplicate copy.
    file_path = reusable.file_path if reusable is not None else _store_file(suffix, file_bytes)

    document = Document(
        filename=filename,
        file_path=file_path,
        content_type=content_type,
        status=DocumentStatus.PROCESSING,
        content_hash=content_hash,
        project_id=project_id,
        conversation_id=conversation_id,
        uploaded_by=uploaded_by,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    if reusable is not None and reusable.embedding_model == settings.embedding_model:
        # Same content, already embedded with the model we currently use:
        # reuse its chunks instead of re-running parse/chunk/embed.
        document.embedding_model = reusable.embedding_model
        document.status = DocumentStatus.READY
        await _copy_chunks(db, reusable, document)
        await db.commit()
    else:
        _enqueue_ingestion(document)

    return document


async def upload_project_document(
    db: AsyncSession,
    project_id: uuid.UUID,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    uploaded_by: uuid.UUID,
) -> Document:
    return await _create_document(
        db,
        filename=filename,
        content_type=content_type,
        file_bytes=file_bytes,
        uploaded_by=uploaded_by,
        project_id=project_id,
        conversation_id=None,
    )


async def upload_conversation_document(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    uploaded_by: uuid.UUID,
) -> Document:
    return await _create_document(
        db,
        filename=filename,
        content_type=content_type,
        file_bytes=file_bytes,
        uploaded_by=uploaded_by,
        project_id=None,
        conversation_id=conversation_id,
    )


class UploadedFileLike(Protocol):
    """The slice of FastAPI's `UploadFile` the batch uploader needs."""

    filename: str | None
    content_type: str | None

    async def read(self) -> bytes: ...


_MAX_FILENAME_LENGTH = 500


async def upload_documents_batch(
    db: AsyncSession,
    files: Sequence[UploadedFileLike],
    *,
    uploaded_by: uuid.UUID,
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID | None,
) -> list[tuple[str, Document | None, str | None]]:
    """Ingests many files into one scope, returning `(filename, document,
    error)` per file in input order.

    A file that fails validation (unsupported type, too large, empty, name
    too long) is reported as rejected without affecting the others. Files are
    read and stored one at a time, so peak memory is one file, not the whole
    batch. Each accepted file becomes its own queue job, so the worker pool
    drains the batch in parallel.
    """
    if len(files) > settings.max_batch_upload_files:
        raise BadRequestError(
            f"At most {settings.max_batch_upload_files} files per request; send the rest in another request"
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    results: list[tuple[str, Document | None, str | None]] = []
    for upload in files:
        filename = upload.filename or "untitled"
        if len(filename) > _MAX_FILENAME_LENGTH:
            results.append((filename[:80] + "…", None, "File name is too long"))
            continue

        file_bytes = await upload.read()
        if not file_bytes:
            results.append((filename, None, "File is empty"))
            continue
        if len(file_bytes) > max_bytes:
            results.append((filename, None, "File exceeds the maximum allowed upload size"))
            continue

        try:
            document = await _create_document(
                db,
                filename=filename,
                content_type=upload.content_type or "application/octet-stream",
                file_bytes=file_bytes,
                uploaded_by=uploaded_by,
                project_id=project_id,
                conversation_id=conversation_id,
            )
        except BadRequestError as exc:  # raised by validation, before any DB write
            results.append((filename, None, str(exc.detail)))
            continue
        results.append((filename, document, None))
    return results


async def retry_failed_document(db: AsyncSession, document: Document) -> Document:
    """Re-queues a document whose ingestion failed (e.g. an embedding API
    rate limit during a big batch) without re-uploading it."""
    if document.status != DocumentStatus.FAILED:
        raise BadRequestError("Only a failed document can be retried")

    # A failure after chunks were persisted would otherwise leave duplicates.
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    document.status = DocumentStatus.PROCESSING
    document.error_message = None
    await db.commit()
    await db.refresh(document)
    _enqueue_ingestion(document)
    return document


async def delete_document(db: AsyncSession, document_id: uuid.UUID) -> None:
    document = await get_document(db, document_id)
    file_path = document.file_path
    await db.delete(document)
    await db.commit()

    # Other documents may point at the same physical file (dedup); only
    # remove it from disk once nothing references it anymore.
    still_referenced = await db.execute(
        select(Document.id).where(Document.file_path == file_path).limit(1)
    )
    if still_referenced.scalar_one_or_none() is None:
        path = Path(file_path)
        if path.exists():
            path.unlink()
        cleanup_reconstructed_files(file_path)


# ---------------------------------------------------------------------------
# Structured reads for the chat agent (outline / page range / full content)
# ---------------------------------------------------------------------------


async def _get_accessible_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID,
) -> Document:
    """Fetches a document scoped to exactly what's visible from the calling
    conversation - the same rule `accessible_documents_filter` applies to
    list queries, applied here to a single lookup so an agent tool can't be
    pointed at a document outside its current project or conversation.

    `conversation_id` is the *calling* conversation's own id, not the
    document's - it's required (not Optional) because
    `accessible_documents_filter` matches it with `==`, which SQLAlchemy
    turns into `IS NULL` for a bare `None`; passing `None` here would match
    any document with no conversation_id at all and silently defeat project
    scoping."""
    stmt = select(Document).where(
        Document.id == document_id,
        accessible_documents_filter(project_id, conversation_id),
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found or not accessible")
    return document


async def get_document_outline(
    db: AsyncSession,
    document_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID,
) -> dict:
    """Total page count and any section headings - lets the agent decide
    which page range is worth reading instead of pulling the whole document."""
    document = await _get_accessible_document(
        db, document_id, project_id=project_id, conversation_id=conversation_id
    )

    recon = load_reconstructed_document(document.file_path)
    total_pages = recon.get("total_pages") if recon else None

    result = await db.execute(
        select(DocumentChunk.chunk_index, DocumentChunk.chunk_metadata)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunk_rows = result.all()

    sections: list[dict] = []
    max_meta_page = 0
    has_page_metadata = False

    for chunk_index, metadata in chunk_rows:
        meta = metadata or {}
        p_num = meta.get("page")
        if p_num is not None:
            has_page_metadata = True
            max_meta_page = max(max_meta_page, int(p_num))
        heading = meta.get("heading") or meta.get("section")
        if heading:
            display_page = p_num if p_num is not None else (chunk_index + 1)
            sections.append({"page": display_page, "heading": heading})

    if total_pages is None:
        total_pages = max_meta_page if has_page_metadata and max_meta_page > 0 else len(chunk_rows)

    return {
        "document_id": str(document.id),
        "filename": document.filename,
        "status": document.status.value,
        "total_pages": total_pages,
        "sections": sections,
    }


async def get_document_page_range(
    db: AsyncSession,
    document_id: uuid.UUID,
    start_page: int,
    end_page: int,
    *,
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID,
) -> str:
    """Continuous text for pages `start_page..end_page` (1-indexed, inclusive)."""
    if start_page < 1 or end_page < start_page:
        raise BadRequestError("start_page must be >= 1 and end_page must be >= start_page")

    document = await _get_accessible_document(
        db, document_id, project_id=project_id, conversation_id=conversation_id
    )

    # 1. Try reading directly from the reconstructed JSON file if available
    recon = load_reconstructed_document(document.file_path)
    if recon and "pages" in recon:
        matching_pages = [
            p for p in recon["pages"] if start_page <= p.get("page", 0) <= end_page
        ]
        if matching_pages:
            parts = [f"=== مستند: {document.filename} ==="]
            for p in matching_pages:
                parts.append(f"[صفحه {p['page']}]\n{p['text']}")
            return "\n\n".join(parts)

    # 2. Query chunks from DB
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
    )
    all_chunks = list(result.scalars().all())
    if not all_chunks:
        return f"[سند: {document.filename}] این بازه صفحه‌ای برای سند یافت نشد."

    # Check if chunks have real page metadata
    has_page_meta = any((c.chunk_metadata or {}).get("page") is not None for c in all_chunks)
    if has_page_meta:
        pages_content: dict[int, list[str]] = {}
        for c in all_chunks:
            p_num = (c.chunk_metadata or {}).get("page")
            if p_num is not None and start_page <= int(p_num) <= end_page:
                pages_content.setdefault(int(p_num), []).append(c.content)

        if not pages_content:
            return f"[سند: {document.filename}] این بازه صفحه‌ای برای سند یافت نشد."

        parts = [f"=== مستند: {document.filename} ==="]
        for p_num in sorted(pages_content.keys()):
            parts.append(f"[صفحه {p_num}]\n" + "\n\n".join(pages_content[p_num]))
        return "\n\n".join(parts)

    # 3. Fallback for legacy documents without page metadata (chunk_index as stand-in)
    legacy_chunks = [c for c in all_chunks if (start_page - 1) <= c.chunk_index <= (end_page - 1)]
    if not legacy_chunks:
        return f"[سند: {document.filename}] این بازه صفحه‌ای برای سند یافت نشد."

    parts = [f"=== مستند: {document.filename} ==="]
    for chunk in legacy_chunks:
        parts.append(f"[صفحه {chunk.chunk_index + 1}]\n{chunk.content}")
    return "\n\n".join(parts)


async def get_full_document_content(
    db: AsyncSession,
    document_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID,
    max_tokens: int = 30_000,
) -> str | dict:
    """Every page of the document, in order. Guards against blowing the
    model's context: past `max_tokens`, returns a structured error instead of
    the text so the agent falls back to `get_document_outline` +
    `get_document_page_range` for a targeted read."""
    document = await _get_accessible_document(
        db, document_id, project_id=project_id, conversation_id=conversation_id
    )

    recon_txt_path = get_reconstructed_txt_path(document.file_path)
    if recon_txt_path.exists():
        try:
            full_text = recon_txt_path.read_text(encoding="utf-8")
            if _count_tokens(full_text) > max_tokens:
                recon_json = load_reconstructed_document(document.file_path)
                total_pages = recon_json.get("total_pages", 1) if recon_json else 1
                return {
                    "error": "DOCUMENT_TOO_LARGE",
                    "total_pages": total_pages,
                    "message": (
                        "سند بیش از حد مجاز طولانی است. لطفاً ابتدا فهرست را بررسی کرده و "
                        "بازه صفحات را با read_document_pages بخوانید."
                    ),
                }
            return full_text
        except Exception:
            pass

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = list(result.scalars().all())
    if not chunks:
        return f"[سند: {document.filename}] این سند هنوز پردازش نشده یا متنی ندارد."

    full_text = "\n\n".join(chunk.content for chunk in chunks)
    if _count_tokens(full_text) > max_tokens:
        return {
            "error": "DOCUMENT_TOO_LARGE",
            "total_pages": len(chunks),
            "message": (
                "سند بیش از حد مجاز طولانی است. لطفاً ابتدا فهرست را بررسی کرده و "
                "بازه صفحات را با read_document_pages بخوانید."
            ),
        }

    return full_text


