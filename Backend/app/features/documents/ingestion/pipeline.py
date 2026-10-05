import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.features.chat.ws import publish_event
from app.features.documents.ingestion.chunker import PageChunk, chunk_document_pages, chunk_text
from app.features.documents.ingestion.embedder import embed_chunks
from app.features.documents.ingestion.ocr import extract_text_from_image
from app.features.documents.ingestion.parser import DocumentPage, parse_document_pages
from app.features.documents.ingestion.reconstructor import save_reconstructed_document
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.providers.embedding_provider import get_embedding_provider

logger = logging.getLogger(__name__)


@dataclass
class IngestionContext:
    """Shared state threaded through every step of the pipeline for one document."""

    document_id: uuid.UUID
    file_path: str
    db: AsyncSession
    filename: str = ""
    pages: list[DocumentPage] = field(default_factory=list)
    raw_text: str = ""
    page_chunks: list[PageChunk] = field(default_factory=list)
    chunks: list[str] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)


class IngestionStep(ABC):
    """One stage of the ingestion pipeline."""

    @abstractmethod
    async def run(self, context: IngestionContext) -> None:
        ...


class ParseStep(IngestionStep):
    """Extracts structured pages, text, and embedded/scanned images."""

    async def run(self, context: IngestionContext) -> None:
        context.pages = parse_document_pages(context.file_path)
        # Strip any NUL byte from initial text
        for page in context.pages:
            page.text = page.text.replace("\x00", "")


class OCRStep(IngestionStep):
    """Performs Vision OCR on embedded or scanned images on each page."""

    async def run(self, context: IngestionContext) -> None:
        settings = get_settings()
        if not getattr(settings, "ocr_enabled", True):
            return

        max_images = getattr(settings, "ocr_max_images_per_doc", 50)
        processed_count = 0

        for page in context.pages:
            if not page.images:
                continue

            for img in page.images:
                if processed_count >= max_images:
                    logger.warning(
                        "Reached ocr_max_images_per_doc (%d) for document %s, skipping remaining images.",
                        max_images,
                        context.document_id,
                    )
                    break

                try:
                    ocr_text = await extract_text_from_image(img.data, img.format)
                    ocr_text = ocr_text.replace("\x00", "").strip()
                    if ocr_text:
                        section_label = (
                            f"\n\n[محتوای استخراج‌شده از تصویر / جدول]:\n{ocr_text}"
                            if page.text
                            else ocr_text
                        )
                        page.text += section_label
                except Exception as exc:
                    logger.warning(
                        "OCR extraction failed for image %s on page %d: %s",
                        img.name,
                        page.page_number,
                        exc,
                    )
                processed_count += 1


class ReconstructStep(IngestionStep):
    """Reconstructs the full document with integrated digital + OCR text,
    persisting clean page-by-page files (.reconstructed.txt and .reconstructed.json)."""

    async def run(self, context: IngestionContext) -> None:
        full_txt, _ = save_reconstructed_document(
            context.file_path, context.filename, context.pages
        )
        context.raw_text = full_txt


class ChunkStep(IngestionStep):
    """Chunks text page by page while tracking real page numbers."""

    async def run(self, context: IngestionContext) -> None:
        settings = get_settings()
        if context.pages:
            context.page_chunks = chunk_document_pages(
                context.pages,
                chunk_size_tokens=settings.chunk_size_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
            )
            context.chunks = [pc.content for pc in context.page_chunks]
        else:
            # Fallback if no pages were extracted
            raw = chunk_text(
                context.raw_text,
                chunk_size_tokens=settings.chunk_size_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
            )
            context.chunks = raw
            context.page_chunks = [
                PageChunk(content=c, page_number=1, chunk_index_in_page=i, metadata={"page": 1})
                for i, c in enumerate(raw)
            ]


class EmbedStep(IngestionStep):
    """Embeds all chunk contents using the configured embedding provider."""

    async def run(self, context: IngestionContext) -> None:
        if not context.chunks:
            context.embeddings = []
            return
        provider = get_embedding_provider()
        context.embeddings = await embed_chunks(provider, context.chunks)


class PersistStep(IngestionStep):
    """Persists chunks and embeddings in pgvector, carrying real page metadata."""

    async def run(self, context: IngestionContext) -> None:
        if not context.page_chunks or not context.embeddings:
            return

        for index, (chunk_obj, embedding) in enumerate(
            zip(context.page_chunks, context.embeddings, strict=True)
        ):
            context.db.add(
                DocumentChunk(
                    document_id=context.document_id,
                    content=chunk_obj.content,
                    chunk_index=index,
                    embedding=embedding,
                    chunk_metadata=chunk_obj.metadata,
                )
            )
        await context.db.commit()


DEFAULT_PIPELINE: list[IngestionStep] = [
    ParseStep(),
    OCRStep(),
    ReconstructStep(),
    ChunkStep(),
    EmbedStep(),
    PersistStep(),
]


async def run_ingestion_pipeline(document_id: uuid.UUID, file_path: str) -> None:
    """Entry point called by the RQ worker for a single uploaded document."""
    async with async_session_factory() as db:
        document = await db.get(Document, document_id)
        filename = document.filename if document is not None else ""
        context = IngestionContext(
            document_id=document_id, file_path=file_path, db=db, filename=filename
        )
        try:
            for step in DEFAULT_PIPELINE:
                await step.run(context)
            document = await db.get(Document, document_id)
            if document is not None:
                document.status = DocumentStatus.READY
                document.embedding_model = get_settings().embedding_model
                await db.commit()
                await _notify_conversation(document)
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.exception("Ingestion failed for document %s", document_id)
            document = await db.get(Document, document_id)
            if document is not None:
                document.status = DocumentStatus.FAILED
                document.error_message = str(exc)[:2000]
                await db.commit()
                await _notify_conversation(document)
            raise


async def _notify_conversation(document: Document) -> None:
    """Pushes a `document_status` event on the uploading conversation's websocket."""
    if document.conversation_id is None:
        return
    await publish_event(
        document.conversation_id,
        {
            "event": "document_status",
            "document_id": str(document.id),
            "status": document.status.value,
            "filename": document.filename,
        },
    )


def run_ingestion_pipeline_sync(document_id: uuid.UUID, file_path: str) -> None:
    """Sync entry point for the RQ worker."""
    asyncio.run(run_ingestion_pipeline(document_id, file_path))
