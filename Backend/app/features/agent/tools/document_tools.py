import base64
import json
import logging
import uuid
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.features.agent.schemas import SourceCitation, ToolExecutionResult
from app.features.agent.scope import resolve_retrieval_scope
from app.features.agent.tools.base import BaseTool
from app.features.documents import folder_service, service as documents_service
from app.features.documents.ingestion.ocr import prepare_image_for_ocr
from app.features.retrieval.service import get_retriever
from app.providers.embedding_provider import get_embedding_provider

settings = get_settings()
logger = logging.getLogger(__name__)


def _parse_document_id(value: Any) -> uuid.UUID:
    try:
        return uuid.UUID(str(value).strip())
    except (ValueError, AttributeError, TypeError):
        raise BadRequestError("'document_id' must be a valid UUID")


async def _resolve_document_id(
    db,
    identifier: str,
    *,
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID,
) -> uuid.UUID:
    """If identifier is a valid UUID, returns it directly.
    Otherwise looks up the document by filename in the accessible scope."""
    raw = str(identifier).strip().lstrip("@")
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        doc = await documents_service.get_accessible_document_by_name(
            db, raw, project_id=project_id, conversation_id=conversation_id
        )
        return doc.id


_DOCUMENT_ID_PROPERTY = {"document_id": {"type": "string", "description": "The document's UUID or filename"}}


class GetDocumentInfoTool(BaseTool):
    name = "get_document_info"
    description = (
        "Get a document's basic facts without reading it: file name, type, page count "
        "(slides / sheets for pptx / xlsx), estimated size in tokens, whether it is short enough for "
        "read_entire_document, and upload time. Accepts either document_id (UUID) or filename (e.g. 'ضابطه773.pdf'). "
        "Use it to learn a document's size or to pick page numbers - "
        "NOT as a step before every question: to find content, use search_knowledge_base."
    )
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "string", "description": "The document's UUID or filename"},
            "filename": {"type": "string", "description": "The document's filename if UUID is not known"},
        },
    }

    async def execute(
        self,
        *,
        db,
        context,
        conversation,
        document_id: str | None = None,
        filename: str | None = None,
        **_: Any,
    ) -> ToolExecutionResult:
        identifier = document_id or filename
        if not identifier:
            raise BadRequestError("Either 'document_id' or 'filename' must be provided")
        project_id = resolve_retrieval_scope(context, conversation)
        resolved_id = await _resolve_document_id(
            db, identifier, project_id=project_id, conversation_id=conversation.id
        )
        info = await documents_service.get_document_info(
            db,
            resolved_id,
            project_id=project_id,
            conversation_id=conversation.id,
        )
        return ToolExecutionResult(text=json.dumps(info, ensure_ascii=False))


class ReadDocumentPagesTool(BaseTool):
    name = "read_document_pages"
    description = (
        "Read the extracted text/OCR for a specific page range of a document (1-indexed, inclusive). "
        "Accepts either document_id (UUID) or filename. "
        "Use it to read specific pages that the user asked for or that search_knowledge_base pointed you to."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_DOCUMENT_ID_PROPERTY,
            "start_page": {"type": "integer", "description": "First page to read (1-indexed)"},
            "end_page": {"type": "integer", "description": "Last page to read (1-indexed, inclusive)"},
        },
        "required": ["document_id", "start_page", "end_page"],
    }

    async def execute(
        self,
        *,
        db,
        context,
        conversation,
        document_id: str,
        start_page: int,
        end_page: int,
        **_: Any,
    ) -> ToolExecutionResult:
        project_id = resolve_retrieval_scope(context, conversation)
        resolved_id = await _resolve_document_id(
            db, document_id, project_id=project_id, conversation_id=conversation.id
        )
        document = await documents_service.get_accessible_document(
            db,
            resolved_id,
            project_id=project_id,
            conversation_id=conversation.id,
        )
        text = await documents_service.get_document_page_range(
            db,
            resolved_id,
            int(start_page),
            int(end_page),
            project_id=project_id,
            conversation_id=conversation.id,
        )
        citations = [
            SourceCitation(
                document_id=str(document.id),
                document_filename=document.filename,
                chunk_index=0,
                snippet=text[:300],
                score=1.0,
                page=int(start_page),
            )
        ]
        return ToolExecutionResult(text=text, citations=citations)


class ReadEntireDocumentTool(BaseTool):
    name = "read_entire_document"
    description = (
        "Read the full extracted text of a document (including clean OCR text for uploaded images/scans). "
        "Accepts either document_id (UUID) or filename. "
        "Use this whenever the user asks for the full text, transcription, content, or summary of an uploaded file or image. "
        "Guarded by a size limit - if the document is too large, this returns a DOCUMENT_TOO_LARGE error; then use "
        "read_document_pages."
    )
    parameters = {
        "type": "object",
        "properties": _DOCUMENT_ID_PROPERTY,
        "required": ["document_id"],
    }

    async def execute(self, *, db, context, conversation, document_id: str, **_: Any) -> ToolExecutionResult:
        project_id = resolve_retrieval_scope(context, conversation)
        resolved_id = await _resolve_document_id(
            db, document_id, project_id=project_id, conversation_id=conversation.id
        )
        document = await documents_service.get_accessible_document(
            db,
            resolved_id,
            project_id=project_id,
            conversation_id=conversation.id,
        )
        result = await documents_service.get_full_document_content(
            db,
            resolved_id,
            project_id=project_id,
            conversation_id=conversation.id,
        )
        if isinstance(result, dict):
            return ToolExecutionResult(text=json.dumps(result, ensure_ascii=False))
        citations = [
            SourceCitation(
                document_id=str(document.id),
                document_filename=document.filename,
                chunk_index=0,
                snippet=result[:300],
                score=1.0,
                page=1,
            )
        ]
        return ToolExecutionResult(text=result, citations=citations)


class SearchKnowledgeBaseTool(BaseTool):
    name = "search_knowledge_base"
    description = (
        "Search the knowledge base for specific topics, questions, facts, or clauses across all visible documents. "
        "Hybrid search (semantic meaning + exact keywords). It returns the best-matching passages widened to their full page. "
        "Keep exact terms such as clause numbers, codes and names in the query. File and folder names are searched too "
        "(each passage is labelled with its folder path). To search inside one folder only, pass path_prefix. "
        "DO NOT use it just to open a file you already know (by document_id) - use read_entire_document or "
        "read_document_pages; to explore folders use browse_folder."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "expand": {
                "type": "string",
                "enum": ["page", "chunk"],
                "description": "'page' (default): return the full page of each hit. 'chunk': only the matching passages.",
            },
            "path_prefix": {
                "type": "string",
                "description": "Only search inside this folder (and its subfolders), e.g. 'امور مربوط به تعدیل/تعدیل شماره2'",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self, *, db, context, conversation, query: str, expand: str = "page", path_prefix: str = "", **_: Any
    ) -> ToolExecutionResult:
        embedding_provider = get_embedding_provider()
        [query_embedding] = await embedding_provider.embed([query])

        project_id = resolve_retrieval_scope(context, conversation)
        logger.info("[RAG:SEARCH] Query: %s | Scope: %s", repr(query), project_id or conversation.id)

        folder_ids = None
        if path_prefix and path_prefix.strip("/ \\"):
            if project_id is None:
                return ToolExecutionResult(text="path_prefix needs a project: this conversation isn't linked to one.")
            folders = await folder_service.load_folders(db, project_id)
            try:
                root = folder_service.resolve_path(folders, path_prefix)
            except NotFoundError as exc:
                top = sorted(f.name for f in folders.values() if f.parent_id is None)
                return ToolExecutionResult(text=f"{exc.detail}. Top-level folders: " + (", ".join(top) or "(none)"))
            folder_ids = folder_service.subtree_ids(folders, {root})

        retriever = get_retriever()
        chunks = await retriever.retrieve(
            db,
            project_id,
            conversation.id,
            query_embedding,
            top_k=settings.retrieval_top_k,
            query_text=query,
            min_similarity=settings.retrieval_score_threshold,
            **({"folder_ids": folder_ids} if folder_ids is not None else {}),
        )

        if not chunks:
            logger.info("[RAG:RESULTS] No chunks matched threshold (min_similarity=%.2f)", settings.retrieval_score_threshold)
            return ToolExecutionResult(text="No relevant results found in the knowledge base.")

        logger.info("[RAG:RESULTS] Found %d matching chunk(s):", len(chunks))
        for idx, chunk in enumerate(chunks, 1):
            snippet_preview = " ".join(chunk.content[:70].split())
            logger.info(
                "   %d. Doc: '%s' (p.%s) | Score: %.3f | Snippet: %s",
                idx,
                chunk.document_filename,
                getattr(chunk, "page_number", "?"),
                chunk.score,
                repr(snippet_preview),
            )

        citations = [
            SourceCitation(
                document_id=chunk.document_id,
                document_filename=chunk.document_filename,
                chunk_index=chunk.chunk_index,
                snippet=chunk.content[:300],
                score=round(chunk.score, 4),
                page=getattr(chunk, "page_number", None),
            )
            for chunk in chunks
        ]
        passages = await self._passages(db, chunks, expand, project_id, conversation.id)
        return ToolExecutionResult(
            text="\n\n".join(f"[Source {i + 1}: {label}]\n{text}" for i, (label, text) in enumerate(passages)),
            citations=citations,
        )

    @staticmethod
    async def _passages(db, chunks, expand: str, project_id, conversation_id) -> list[tuple[str, str]]:
        """`(label, text)` per result: the full page of each hit while the page-token budget lasts (best hit first, one entry
        per page), otherwise the matched chunk itself."""
        budget = settings.search_page_expansion_max_tokens if expand != "chunk" else 0
        page_texts: dict = {}
        if budget > 0:
            wanted = [
                (uuid.UUID(str(chunk.document_id)), chunk.page_number)
                for chunk in chunks
                if getattr(chunk, "page_number", None)
            ]
            page_texts = await documents_service.get_page_texts(
                db, wanted, project_id=project_id, conversation_id=conversation_id
            )

        passages: list[tuple[str, str]] = []
        seen_pages: set = set()
        for chunk in chunks:
            page = getattr(chunk, "page_number", None)
            name = getattr(chunk, "document_path", "") or chunk.document_filename
            label = f"{name} (صفحه {page})" if page else name
            key = (uuid.UUID(str(chunk.document_id)), page)
            if page and key in seen_pages:
                continue  # an earlier (better) hit already returned this whole page
            page_text = page_texts.get(key)
            if page_text and budget > 0:
                seen_pages.add(key)
                text = documents_service.truncate_to_tokens(page_text, budget)
                budget -= documents_service._count_tokens(text)
                passages.append((f"{label} - full page", text))
            else:
                passages.append((label, chunk.content))
        return passages


class ViewDocumentPageTool(BaseTool):
    name = "view_document_page"
    description = (
        "Look at the actual raw visual IMAGE of one page of a PDF or image file (costs several thousand image tokens). "
        "DO NOT use this to read or transcribe text from letters, documents, or forms - all text and OCR is already "
        "extracted with high precision and available via read_entire_document and read_document_pages! "
        "Use this ONLY when visual non-text inspection is strictly needed: architectural/engineering drawings (lines, "
        "dimensions on blueprints), maps, graphical diagrams, stamps, signatures, or when the user specifically asks "
        "to inspect the visual drawing/layout."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_DOCUMENT_ID_PROPERTY,
            "page_number": {"type": "integer", "description": "Page to look at (1-indexed; 1 for an image file)"},
        },
        "required": ["document_id", "page_number"],
    }

    async def execute(
        self, *, db, context, conversation, document_id: str, page_number: int, **_: Any
    ) -> ToolExecutionResult:
        project_id = resolve_retrieval_scope(context, conversation)
        resolved_id = await _resolve_document_id(
            db, document_id, project_id=project_id, conversation_id=conversation.id
        )
        document, image, rotation = await documents_service.get_document_page_image(
            db,
            resolved_id,
            int(page_number),
            project_id=project_id,
            conversation_id=conversation.id,
        )
        label = f"{document.filename} (صفحه {page_number})"
        logger.info("[AGENT:VIEW_PAGE] Reading raw page image directly: %s", label)
        try:
            # Same clean-up as OCR: blank check, upright rotation, downscale to <= OCR_MAX_IMAGE_DIMENSION, JPEG. The rotation
            # found at ingestion is reused (finding it again would cost 1-4 model calls and ~20 s inside the chat turn).
            prepared = await prepare_image_for_ocr(image, rotation=rotation)
        except Exception:  # noqa: BLE001
            logger.exception("view_document_page could not prepare %s", label)
            return ToolExecutionResult(text=f"The page image of {label} could not be prepared. Use read_document_pages for its text.")
        if prepared is None:
            return ToolExecutionResult(text=f"{label} looks blank: nothing to see.")
        data, mime = prepared
        return ToolExecutionResult(
            text=(
                f"The image of {label} is attached in the next message. Read it yourself to answer; say where on the page "
                "you read each number, and say so if you cannot tie a number to the drawing."
            ),
            images=[f"data:image/{mime};base64,{base64.b64encode(data).decode()}"],
            citations=[
                SourceCitation(
                    document_id=str(document.id),
                    document_filename=document.filename,
                    chunk_index=-1,  # not a text chunk: the page image itself
                    snippet=f"[page image] {label}",
                    score=1.0,
                    page=int(page_number),
                )
            ],
        )
