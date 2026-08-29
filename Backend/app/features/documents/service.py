import uuid
from pathlib import Path

from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError, NotFoundError
from app.features.documents.ingestion.parser import SUPPORTED_EXTENSIONS
from app.features.documents.models import Document, DocumentStatus

settings = get_settings()
_redis_conn = Redis.from_url(settings.redis_url)
_queue = Queue(settings.ingestion_queue_name, connection=_redis_conn)


async def list_documents(db: AsyncSession, context: UserContext) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.team_id.in_(context.team_ids))
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    return document


async def upload_document(
    db: AsyncSession,
    context: UserContext,
    team_id: uuid.UUID,
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> Document:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise BadRequestError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    if team_id not in context.team_ids:
        raise BadRequestError("You can only upload documents to a team you belong to")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{suffix}"
    file_path = upload_dir / stored_name
    file_path.write_bytes(file_bytes)

    document = Document(
        filename=filename,
        file_path=str(file_path),
        content_type=content_type,
        status=DocumentStatus.PROCESSING,
        team_id=team_id,
        uploaded_by=context.id,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    _queue.enqueue(
        "app.features.documents.ingestion.pipeline.run_ingestion_pipeline_sync",
        document.id,
        document.file_path,
        job_timeout=600,
    )

    return document


async def delete_document(db: AsyncSession, document_id: uuid.UUID) -> None:
    document = await get_document(db, document_id)
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()
    await db.delete(document)
    await db.commit()
