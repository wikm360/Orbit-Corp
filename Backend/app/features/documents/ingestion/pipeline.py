import asyncio
import hashlib
import inspect
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.features.chat.ws import publish_event
from app.features.documents.cancellation import IngestionCancelled, is_cancel_requested
from app.features.documents.ingestion.chunker import PageChunk, chunk_document_pages, chunk_text
from app.features.documents.ingestion.embedder import embed_chunks
from app.features.documents.ingestion.ocr import extract_text_from_image, ocr_client_session
from app.features.documents.ingestion.ocr_cache import get_cached_ocr, ocr_cache_key, put_cached_ocr, vision_model_name
from app.features.documents.ingestion.page_kind import mark_drawing_page
from app.features.documents.chunk_paths import PATH_KEY, chunk_search_text, path_for_new_chunks
from app.features.documents.ingestion.parser import IMAGE_EXTENSIONS, DocumentPage, parse_document_pages, render_pdf_page
from app.features.documents.ingestion.reconstructor import save_reconstructed_document
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.providers.embedding_provider import get_embedding_provider

logger = logging.getLogger(__name__)

# A page-level OCR result shorter than this is treated as a failed read and the existing text layer is kept.
_MIN_REPLACEMENT_OCR_CHARS = 20


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
        context.pages = await asyncio.to_thread(parse_document_pages, context.file_path)
        # Strip any NUL byte from initial text
        for page in context.pages:
            page.text = page.text.replace("\x00", "")


class OcrRead(NamedTuple):
    text: str
    rotation: int | None  # clockwise degrees the image was turned to be upright; None = not determined


def _supports_kwarg(fn, kwarg_name: str) -> bool:
    target = getattr(fn, "side_effect", None) or fn
    try:
        sig = inspect.signature(target)
        return kwarg_name in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
    except Exception:
        return False


class _OcrReader:
    """Reads images through two cheap layers before paying for a vision call, for one document:

    1. the same image (by bytes) already read/in flight in this document is read once and shared (repeated
       logos/stamps/headers, identical pages);
    2. the persistent `ocr_cache` (same image read earlier in any document, same OCR model + prompt).
    Only the API call itself is limited by `OCR_CONCURRENCY`; waiting for a shared result holds no slot. The DB session
    is shared with the rest of the pipeline, so cache reads/writes are serialized with a lock. A failed or empty
    read is never cached.
    """

    def __init__(self, db: AsyncSession | None, concurrency: int):
        self._db = db
        self._api_slots = asyncio.Semaphore(max(1, concurrency))
        self._db_lock = asyncio.Lock()
        self._reads: dict[str, asyncio.Future[str]] = {}
        self.api_calls = 0
        self.cache_hits = 0
        self.shared_in_document = 0

    async def read(self, data: bytes, fmt: str, debug_info: dict | None = None) -> OcrRead:
        key = ocr_cache_key(data)
        pending = self._reads.get(key)
        if pending is None:
            pending = self._reads[key] = asyncio.ensure_future(self._read_once(key, data, fmt, debug_info=debug_info))
        else:
            self.shared_in_document += 1
        return await pending

    async def _read_once(self, key: str, data: bytes, fmt: str, debug_info: dict | None = None) -> OcrRead:
        if self._db is not None:
            async with self._db_lock:
                cached = await get_cached_ocr(self._db, key)
            if cached is not None:
                self.cache_hits += 1
                return OcrRead(*cached)
        report: dict = {}
        async with self._api_slots:
            # Callers log-and-skip a failed read, so a cancelled document drains its remaining pages without paying
            # for them; `run_ingestion_pipeline` then notices the cancellation at the next step boundary.
            if debug_info and await is_cancel_requested(uuid.UUID(debug_info["document_id"])):
                raise IngestionCancelled()
            self.api_calls += 1
            kw = {"report": report}
            if debug_info and _supports_kwarg(extract_text_from_image, "debug_info"):
                kw["debug_info"] = debug_info
            raw_ocr = await extract_text_from_image(data, fmt, **kw)
            text = (raw_ocr or "").replace("\x00", "").strip()
        rotation = report.get("rotation")
        if text and self._db is not None:
            doc_uuid = None
            page_num = None
            filename = None
            if debug_info:
                if "document_id" in debug_info:
                    try:
                        doc_uuid = uuid.UUID(str(debug_info["document_id"]))
                    except Exception:  # noqa: BLE001
                        pass
                if "page_number" in debug_info:
                    try:
                        page_num = int(debug_info["page_number"])
                    except Exception:  # noqa: BLE001
                        pass
                filename = debug_info.get("filename")
            async with self._db_lock:
                await put_cached_ocr(
                    self._db,
                    key,
                    text,
                    rotation,
                    document_id=doc_uuid,
                    source_filename=filename,
                    page_number=page_num,
                )
        return OcrRead(text, rotation)


def _remember_rotation(page, rotation: int | None) -> None:
    """Stores the clockwise rotation that makes the page upright in its metadata (-> chunk metadata and
    `.reconstructed.json`), so showing the page later does not have to find it again (1-4 model calls, ~20 s)."""
    if rotation in (0, 90, 180, 270):
        page.metadata["rotation"] = rotation


class OCRStep(IngestionStep):
    """Vision OCR for the parts of a document the text layer does not cover.

    - PDF pages flagged `needs_ocr` (unusable text layer: visual-order Persian or symbol garbage) are rendered and OCR'd;
      the OCR text *replaces* the layer (the deterministic repair done at parse time stays as the fallback).
    - Every other page gets its embedded/scanned images OCR'd and appended to its text.
    Pages are processed concurrently (`OCR_CONCURRENCY`); the images of one page stay sequential so their order is stable.
    Identical images are read once per document and cached across documents (`_OcrReader`).
    """

    async def run(self, context: IngestionContext) -> None:
        settings = get_settings()
        if not getattr(settings, "ocr_enabled", True):
            return

        concurrency = max(1, getattr(settings, "ocr_concurrency", 4))
        reader = _OcrReader(context.db, concurrency)
        render_slots = asyncio.Semaphore(concurrency)  # bounds simultaneous page renders (memory/CPU), not API calls
        image_budget = getattr(settings, "ocr_max_images_per_doc", 50)
        replace_budget = getattr(settings, "ocr_max_replaced_pages", 300)
        replace_enabled = getattr(settings, "ocr_replace_bad_text_layer", True)
        counted_images: set[str] = set()  # a repeated image costs no API call, so it does not use up the budget
        is_image_file = Path(context.file_path).suffix.lower() in IMAGE_EXTENSIONS and len(context.pages) == 1

        jobs = []
        for page in context.pages:
            if page.needs_ocr and replace_enabled and replace_budget > 0:
                replace_budget -= 1
                jobs.append(self._replace_with_page_ocr(context, page, reader, render_slots))
                continue
            if page.needs_ocr and replace_enabled:
                logger.warning(
                    "Reached ocr_max_replaced_pages for document %s; page %d keeps its text layer.",
                    context.document_id,
                    page.page_number,
                )
            selected = []
            for img in page.images:
                digest = hashlib.sha256(img.data).hexdigest()
                if digest not in counted_images:
                    if image_budget <= 0:
                        logger.warning(
                            "Reached ocr_max_images_per_doc (%d) for document %s, skipping remaining images.",
                            getattr(settings, "ocr_max_images_per_doc", 50),
                            context.document_id,
                        )
                        break
                    image_budget -= 1
                    counted_images.add(digest)
                selected.append(img)
            if selected:
                jobs.append(self._append_image_text(context, page, selected, reader, whole_page_image=is_image_file))

        if jobs:
            logger.info(
                "OCR for document %s: %d jobs, concurrency %d, model %s",
                context.document_id,
                len(jobs),
                concurrency,
                vision_model_name(),
            )
            started = time.monotonic()
            async with ocr_client_session():
                await asyncio.gather(*jobs)
            logger.info(
                "OCR for document %s done in %.1fs: %d vision calls, %d cache hits, %d shared within the document",
                context.document_id,
                time.monotonic() - started,
                reader.api_calls,
                reader.cache_hits,
                reader.shared_in_document,
            )

    async def _replace_with_page_ocr(
        self, context: IngestionContext, page, reader: _OcrReader, render_slots: asyncio.Semaphore
    ) -> None:
        try:
            async with render_slots:
                rendered = await asyncio.to_thread(render_pdf_page, context.file_path, page.page_number)
            if rendered is None:
                return
            debug_info = {
                "document_id": str(context.document_id),
                "page_number": page.page_number,
                "filename": Path(context.file_path).name,
            }
            ocr = await reader.read(rendered.data, rendered.format, debug_info=debug_info)
        except Exception as exc:
            logger.warning("Page OCR failed for page %d of %s: %s", page.page_number, context.document_id, exc)
            return
        if len(ocr.text) >= _MIN_REPLACEMENT_OCR_CHARS:
            page.text = ocr.text
            page.images = []
            page.metadata["text_layer"] = "ocr"
            # The OCR'd image is the whole rendered page, so its rotation is the page's: view_document_page reuses it.
            _remember_rotation(page, ocr.rotation)

    async def _append_image_text(
        self, context: IngestionContext, page, images, reader: _OcrReader, whole_page_image: bool = False
    ) -> None:
        for img in images:
            try:
                debug_info = {
                    "document_id": str(context.document_id),
                    "page_number": page.page_number,
                    "filename": Path(context.file_path).name,
                }
                ocr = await reader.read(img.data, img.format, debug_info=debug_info)
            except Exception as exc:
                logger.warning("OCR extraction failed for image %s on page %d: %s", img.name, page.page_number, exc)
                continue
            ocr_text = ocr.text
            if ocr_text and whole_page_image:
                _remember_rotation(page, ocr.rotation)  # an uploaded image file: the image is the page
            if ocr_text:
                section_label = (
                    f"\n\n[محتوای استخراج‌شده از تصویر / جدول]:\n{ocr_text}" if page.text else ocr_text
                )
                page.text += section_label


class PageKindStep(IngestionStep):
    """Flags drawing/chart pages (loose numbers, no labels) so the agent knows to look at the page image, see `page_kind`."""

    async def run(self, context: IngestionContext) -> None:
        if not getattr(get_settings(), "ocr_mark_drawing_pages", True):
            return
        marked = [page.page_number for page in context.pages if mark_drawing_page(page)]
        if marked:
            logger.info("Document %s: pages flagged as drawings/charts: %s", context.document_id, marked)


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
            raise ValueError(
                "No text could be extracted from the document, so nothing was indexed "
                "(empty file, unreadable scan, or OCR disabled/failed)."
            )

        path = await path_for_new_chunks(context.db, context.document_id)
        for index, (chunk_obj, embedding) in enumerate(
            zip(context.page_chunks, context.embeddings, strict=True)
        ):
            context.db.add(
                DocumentChunk(
                    document_id=context.document_id,
                    content=chunk_obj.content,
                    chunk_index=index,
                    embedding=embedding,
                    chunk_metadata={**chunk_obj.metadata, PATH_KEY: path} if path else chunk_obj.metadata,
                    search_text=chunk_search_text(path, chunk_obj.content),
                )
            )
        await context.db.commit()


DEFAULT_PIPELINE: list[IngestionStep] = [
    ParseStep(),
    OCRStep(),
    PageKindStep(),
    ReconstructStep(),
    ChunkStep(),
    EmbedStep(),
    PersistStep(),
]


async def _assert_still_processing(db: AsyncSession, document_id: uuid.UUID) -> None:
    """Stops the pipeline if the document was cancelled or deleted meanwhile (the status is read fresh from the DB)."""
    status = (await db.execute(select(Document.status).where(Document.id == document_id))).scalar_one_or_none()
    if status != DocumentStatus.PROCESSING:
        raise IngestionCancelled()


async def run_ingestion_pipeline(document_id: uuid.UUID, file_path: str) -> None:
    """Entry point called by the RQ worker for a single uploaded document."""
    async with async_session_factory() as db:
        document = await db.get(Document, document_id)
        if document is None:
            # Deleted while still waiting in the queue: nothing to process, and no paid OCR/embedding calls.
            logger.info("Ingestion %s skipped: document no longer exists", document_id)
            return
        if document.status != DocumentStatus.PROCESSING:
            # Cancelled while still waiting in the queue (or already finished by an earlier job).
            logger.info("Ingestion %s skipped: document is %s", document_id, document.status.value)
            return
        filename = document.filename
        context = IngestionContext(
            document_id=document_id, file_path=file_path, db=db, filename=filename
        )
        try:
            for step in DEFAULT_PIPELINE:
                started = time.monotonic()
                await step.run(context)
                logger.info(
                    "Ingestion %s: %s took %.1fs",
                    document_id,
                    type(step).__name__,
                    time.monotonic() - started,
                )
                await _assert_still_processing(db, document_id)
            # Conditional: a cancel that lands after the last check must not be overwritten with READY.
            finished = await db.execute(
                update(Document)
                .where(Document.id == document_id, Document.status == DocumentStatus.PROCESSING)
                .values(status=DocumentStatus.READY, embedding_model=get_settings().embedding_model)
                .returning(Document.id)
            )
            if finished.scalar_one_or_none() is None:
                raise IngestionCancelled()
            await db.commit()
            document = await db.get(Document, document_id)
            if document is not None:
                await db.refresh(document)
                await _notify_conversation(document)
        except IngestionCancelled:
            await db.rollback()
            # Chunks persisted by a run that was cancelled right at the end must not stay behind (a deleted document's
            # chunks are already gone through the FK cascade).
            await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
            await db.commit()
            logger.info("Ingestion %s stopped: document was cancelled or deleted", document_id)
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.exception("Ingestion failed for document %s", document_id)
            document = await db.get(Document, document_id)
            if document is not None and document.status == DocumentStatus.PROCESSING:
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
