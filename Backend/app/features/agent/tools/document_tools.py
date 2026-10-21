import json
import uuid
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.features.agent.schemas import SourceCitation, ToolExecutionResult
from app.features.agent.scope import resolve_retrieval_scope
from app.features.agent.tools.base import BaseTool
from app.features.documents import service as documents_service
from app.features.retrieval.service import get_retriever
from app.providers.embedding_provider import get_embedding_provider

settings = get_settings()


def _parse_document_id(value: Any) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise BadRequestError("'document_id' must be a valid UUID")


_DOCUMENT_ID_PROPERTY = {"document_id": {"type": "string", "description": "The document's UUID"}}


class GetDocumentInfoTool(BaseTool):
    name = "get_document_info"
    description = (
        "Get a document's basic facts without reading it: file name, type, page count "
        "(slides / sheets for pptx / xlsx), estimated size in tokens, whether it is short enough for "
        "read_entire_document, and upload time. Use it to learn a document's size or to pick page numbers - "
        "NOT as a step before every question: to find content, use search_knowledge_base."
    )
    parameters = {
        "type": "object",
        "properties": _DOCUMENT_ID_PROPERTY,
        "required": ["document_id"],
    }

    async def execute(self, *, db, context, conversation, document_id: str, **_: Any) -> ToolExecutionResult:
        info = await documents_service.get_document_info(
            db,
            _parse_document_id(document_id),
            project_id=resolve_retrieval_scope(context, conversation),
            conversation_id=conversation.id,
        )
        return ToolExecutionResult(text=json.dumps(info, ensure_ascii=False))


class ReadDocumentPagesTool(BaseTool):
    name = "read_document_pages"
    description = (
        "Read a specific page range of a document (1-indexed, inclusive). Use it for the few pages that "
        "search_knowledge_base pointed you to (e.g. the neighbours of a hit), not to scan a document: read "
        "only the pages you need."
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
        text = await documents_service.get_document_page_range(
            db,
            _parse_document_id(document_id),
            int(start_page),
            int(end_page),
            project_id=resolve_retrieval_scope(context, conversation),
            conversation_id=conversation.id,
        )
        return ToolExecutionResult(text=text)


class ReadEntireDocumentTool(BaseTool):
    name = "read_entire_document"
    description = (
        "Read a document's full content - only for a SHORT document, or when the user explicitly asks for a summary or "
        "overview of the whole file. For specific questions use search_knowledge_base instead. Guarded by a size "
        "limit - if the document is too large, this returns a DOCUMENT_TOO_LARGE error; then use "
        "search_knowledge_base / read_document_pages."
    )
    parameters = {
        "type": "object",
        "properties": _DOCUMENT_ID_PROPERTY,
        "required": ["document_id"],
    }

    async def execute(self, *, db, context, conversation, document_id: str, **_: Any) -> ToolExecutionResult:
        result = await documents_service.get_full_document_content(
            db,
            _parse_document_id(document_id),
            project_id=resolve_retrieval_scope(context, conversation),
            conversation_id=conversation.id,
        )
        if isinstance(result, dict):
            return ToolExecutionResult(text=json.dumps(result, ensure_ascii=False))
        return ToolExecutionResult(text=result)


class SearchKnowledgeBaseTool(BaseTool):
    name = "search_knowledge_base"
    description = (
        "PRIMARY tool for any question about the content of documents - use it FIRST, before reading anything. "
        "Hybrid search (meaning + exact words) across every document visible in this conversation (the project's "
        "knowledge base and this chat's uploads). It returns the best-matching passages, each widened to its FULL page "
        "(page text with surrounding tables/columns) when the page is available, so you normally do not need to read "
        "pages yourself afterwards. Keep exact terms such as clause numbers, codes and names in the query - they are "
        "matched literally. If the first results do not answer the question, search again with a reworded or more "
        "specific query. Always scoped to what this conversation can already see."
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
        },
        "required": ["query"],
    }

    async def execute(
        self, *, db, context, conversation, query: str, expand: str = "page", **_: Any
    ) -> ToolExecutionResult:
        embedding_provider = get_embedding_provider()
        [query_embedding] = await embedding_provider.embed([query])

        project_id = resolve_retrieval_scope(context, conversation)
        retriever = get_retriever()
        chunks = await retriever.retrieve(
            db,
            project_id,
            conversation.id,
            query_embedding,
            top_k=settings.retrieval_top_k,
            query_text=query,
            min_similarity=settings.retrieval_score_threshold,
        )

        if not chunks:
            return ToolExecutionResult(text="No relevant results found in the knowledge base.")

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
            label = f"{chunk.document_filename} (صفحه {page})" if page else chunk.document_filename
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
