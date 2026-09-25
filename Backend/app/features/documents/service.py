import hashlib
import logging
import uuid
from pathlib import Path

from redis import Redis
from rq import Queue
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.features.documents.ingestion.parser import SUPPORTED_EXTENSIONS
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
    """Total page count (chunk count is the practical stand-in for "page"
    until the ingestion pipeline tracks real page boundaries) plus whatever
    heading/section metadata a chunk carries, if any - lets the agent decide
    which page range is worth reading instead of pulling the whole document."""
    document = await _get_accessible_document(
        db, document_id, project_id=project_id, conversation_id=conversation_id
    )

    total_pages = (
        await db.scalar(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document.id)
        )
    ) or 0

    sections: list[dict] = []
    if total_pages:
        result = await db.execute(
            select(DocumentChunk.chunk_index, DocumentChunk.chunk_metadata)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
        )
        for chunk_index, metadata in result.all():
            heading = (metadata or {}).get("heading") or (metadata or {}).get("section")
            if heading:
                sections.append({"page": chunk_index + 1, "heading": heading})

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
    """Continuous text for pages `start_page..end_page` (1-indexed,
    inclusive; a "page" is one chunk)."""
    if start_page < 1 or end_page < start_page:
        raise BadRequestError("start_page must be >= 1 and end_page must be >= start_page")

    document = await _get_accessible_document(
        db, document_id, project_id=project_id, conversation_id=conversation_id
    )

    result = await db.execute(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document.id,
            DocumentChunk.chunk_index.between(start_page - 1, end_page - 1),
        )
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = list(result.scalars().all())
    if not chunks:
        return f"[سند: {document.filename}] این بازه صفحه‌ای برای سند یافت نشد."

    parts = [f"=== مستند: {document.filename} ==="]
    for chunk in chunks:
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

