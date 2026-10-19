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
        "(slides / sheets for pptx / xlsx), estimated size in tokens, whether the whole thing "
        "fits read_entire_document, and upload time. Call this first on an unfamiliar document "
        "to decide between read_entire_document and read_document_pages."
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
    description = "Read a specific page range of a document (1-indexed, inclusive)."
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
        "Read a document's full content. Guarded by a size limit - if the "
        "document is too large, this returns a DOCUMENT_TOO_LARGE error instead; "
        "fall back to read_document_pages in that case (get_document_info tells you the size up front)."
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
        "Hybrid search (meaning + exact words) across every document visible in this "
        "conversation - the project's knowledge base and the files uploaded to this chat - "
        "for content relevant to a query. Exact terms such as clause numbers, codes and names "
        "in the query are matched literally, so keep them in the query. Always scoped to what "
        "this conversation can already see."
    )
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What to search for"}},
        "required": ["query"],
    }

    async def execute(self, *, db, context, conversation, query: str, **_: Any) -> ToolExecutionResult:
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

        context_parts = []
        citations = []
        for i, chunk in enumerate(chunks):
            page_num = getattr(chunk, "page_number", None)
            page_info = f" (صفحه {page_num})" if page_num else ""
            context_parts.append(f"[Source {i + 1}: {chunk.document_filename}{page_info}]\n{chunk.content}")
            citations.append(
                SourceCitation(
                    document_id=chunk.document_id,
                    document_filename=chunk.document_filename,
                    chunk_index=chunk.chunk_index,
                    snippet=chunk.content[:300],
                    score=round(chunk.score, 4),
                    page=page_num,
                )
            )
        return ToolExecutionResult(text="\n\n".join(context_parts), citations=citations)
