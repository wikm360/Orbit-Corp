import hashlib
import uuid
from pathlib import Path

from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.features.documents.ingestion.parser import SUPPORTED_EXTENSIONS
from app.features.documents.models import Document, DocumentChunk, DocumentStatus

settings = get_settings()
_redis_conn = Redis.from_url(settings.redis_url)
_queue = Queue(settings.ingestion_queue_name, connection=_redis_conn)


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
