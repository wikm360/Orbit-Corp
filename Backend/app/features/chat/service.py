import json
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.features.chat.models import Conversation, Message, MessageRole
from app.features.chat.schemas import SourceCitation
from app.features.retrieval.service import get_retriever
from app.providers.embedding_provider import get_embedding_provider
from app.providers.llm_provider import ChatMessage, get_llm_provider

settings = get_settings()

SYSTEM_PROMPT = (
    "You are the internal AI assistant for this organization. Answer clearly and "
    "concisely. When context from internal documents is provided below, base your "
    "answer on it and do not contradict it. If no context is provided, answer as a "
    "general-purpose assistant using your own knowledge."
)


@dataclass
class ToolResult:
    used: bool
    context_text: str = ""
    sources: list[SourceCitation] = field(default_factory=list)


class Tool(ABC):
    """A capability the chat orchestrator can call before asking the LLM to respond.

    Only `RetrievalTool` exists for the MVP, but the orchestrator loops over a
    list of tools rather than calling retrieval directly, so phase 2 can add
    e.g. a `WebSearchTool` here and switch to a real tool-calling loop without
    reshaping this service.
    """

    name: str

    @abstractmethod
    async def run(self, db: AsyncSession, context: UserContext, query: str) -> ToolResult:
        ...


class RetrievalTool(Tool):
    name = "document_retrieval"

    async def run(self, db: AsyncSession, context: UserContext, query: str) -> ToolResult:
        embedding_provider = get_embedding_provider()
        [query_embedding] = await embedding_provider.embed([query])

        retriever = get_retriever()
        chunks = await retriever.retrieve(
            db, context, query_embedding, top_k=settings.retrieval_top_k
        )

        if not chunks or chunks[0].score < settings.retrieval_score_threshold:
            return ToolResult(used=False)

        context_text = "\n\n".join(
            f"[Source {i + 1}: {chunk.document_filename}]\n{chunk.content}"
            for i, chunk in enumerate(chunks)
        )
        sources = [
            SourceCitation(
                document_id=chunk.document_id,
                document_filename=chunk.document_filename,
                chunk_index=chunk.chunk_index,
                snippet=chunk.content[:300],
                score=round(chunk.score, 4),
            )
            for chunk in chunks
        ]
        return ToolResult(used=True, context_text=context_text, sources=sources)


TOOLS: list[Tool] = [RetrievalTool()]


async def get_or_create_conversation(
    db: AsyncSession, context: UserContext, conversation_id: uuid.UUID | None, first_message: str
) -> Conversation:
    if conversation_id is not None:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is not None and conversation.user_id == context.id:
            return conversation

    conversation = Conversation(user_id=context.id, title=first_message[:80])
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(db: AsyncSession, context: UserContext) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == context.id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def _build_llm_messages(
    db: AsyncSession, conversation: Conversation, context_text: str
) -> list[ChatMessage]:
    """Builds the message list from persisted history.

    Assumes the current user message has already been committed to the
    `messages` table by the caller, so it's picked up here as the last
    history row rather than being appended separately (which would
    duplicate it in the prompt).
    """
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    system_content = SYSTEM_PROMPT
    if context_text:
        system_content += f"\n\nRelevant internal document context:\n{context_text}"

    messages: list[ChatMessage] = [{"role": "system", "content": system_content}]
    for msg in history:
        role = "assistant" if msg.role == MessageRole.ASSISTANT else "user"
        messages.append({"role": role, "content": msg.content})
    return messages


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(
    db: AsyncSession,
    context: UserContext,
    conversation_id: uuid.UUID | None,
    user_message: str,
) -> AsyncIterator[str]:
    """Runs the retrieval tool, streams the LLM's answer as SSE, then persists
    the user + assistant messages once the stream completes."""
    conversation = await get_or_create_conversation(db, context, conversation_id, user_message)

    db.add(Message(conversation_id=conversation.id, role=MessageRole.USER, content=user_message))
    await db.commit()

    tool_result = ToolResult(used=False)
    for tool in TOOLS:
        tool_result = await tool.run(db, context, user_message)
        if tool_result.used:
            break

    yield _sse_event("start", {"conversation_id": str(conversation.id)})

    llm_messages = await _build_llm_messages(db, conversation, tool_result.context_text)
    llm_provider = get_llm_provider()

    full_response = ""
    async for delta in llm_provider.stream_chat(llm_messages):
        full_response += delta
        yield _sse_event("delta", {"content": delta})

    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=full_response,
        sources=[s.model_dump() for s in tool_result.sources],
    )
    db.add(assistant_message)
    await db.commit()

    yield _sse_event(
        "done",
        {
            "sources": [s.model_dump() for s in tool_result.sources],
            "message_id": str(assistant_message.id),
        },
    )
