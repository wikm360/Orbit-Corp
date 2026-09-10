import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.features.documents.ingestion.chunker import chunk_text
from app.features.documents.ingestion.embedder import embed_chunks
from app.features.documents.ingestion.parser import parse_document
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.providers.embedding_provider import get_embedding_provider

logger = logging.getLogger(__name__)


@dataclass
class IngestionContext:
    """Shared state threaded through every step of the pipeline for one document."""

    document_id: uuid.UUID
    file_path: str
    db: AsyncSession
    raw_text: str = ""
    chunks: list[str] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)


class IngestionStep(ABC):
    """One stage of the ingestion pipeline.

    Adding a new stage (e.g. OCR for scanned PDFs in phase 2) means writing a
    new IngestionStep and inserting it into the pipeline list below — no
    existing step needs to change.
    """

    @abstractmethod
    async def run(self, context: IngestionContext) -> None:
        ...


class ParseStep(IngestionStep):
    async def run(self, context: IngestionContext) -> None:
        context.raw_text = parse_document(context.file_path)


class ChunkStep(IngestionStep):
    async def run(self, context: IngestionContext) -> None:
        settings = get_settings()
        context.chunks = chunk_text(
            context.raw_text,
            chunk_size_tokens=settings.chunk_size_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )


class EmbedStep(IngestionStep):
    async def run(self, context: IngestionContext) -> None:
        provider = get_embedding_provider()
        context.embeddings = await embed_chunks(provider, context.chunks)


class PersistStep(IngestionStep):
    async def run(self, context: IngestionContext) -> None:
        for index, (chunk, embedding) in enumerate(
            zip(context.chunks, context.embeddings, strict=True)
        ):
            context.db.add(
                DocumentChunk(
                    document_id=context.document_id,
                    content=chunk,
                    chunk_index=index,
                    embedding=embedding,
                    chunk_metadata={},
                )
            )
        await context.db.commit()


DEFAULT_PIPELINE: list[IngestionStep] = [ParseStep(), ChunkStep(), EmbedStep(), PersistStep()]


async def run_ingestion_pipeline(document_id: uuid.UUID, file_path: str) -> None:
    """Entry point called by the RQ worker for a single uploaded document."""
    async with async_session_factory() as db:
        context = IngestionContext(document_id=document_id, file_path=file_path, db=db)
        try:
            for step in DEFAULT_PIPELINE:
                await step.run(context)
            document = await db.get(Document, document_id)
            document.status = DocumentStatus.READY
            document.embedding_model = get_settings().embedding_model
            await db.commit()
        except Exception as exc:  # noqa: BLE001 - persisted as failure state, then re-raised for RQ/logs
            await db.rollback()
            logger.exception("Ingestion failed for document %s", document_id)
            document = await db.get(Document, document_id)
            if document is not None:
                document.status = DocumentStatus.FAILED
                document.error_message = str(exc)[:2000]
                await db.commit()
            raise


def run_ingestion_pipeline_sync(document_id: uuid.UUID, file_path: str) -> None:
    """Sync entry point for the RQ worker, which calls jobs synchronously."""
    asyncio.run(run_ingestion_pipeline(document_id, file_path))
