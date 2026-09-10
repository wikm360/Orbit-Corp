import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError, ForbiddenError
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.features.chat.schemas import ConversationCreate, MessageRead, SourceCitation
from app.features.chat.ws import manager as ws_manager
from app.features.projects.service import get_project
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
    async def run(
        self, db: AsyncSession, project_id: uuid.UUID | None, conversation_id: uuid.UUID, query: str
    ) -> ToolResult:
        ...


class RetrievalTool(Tool):
    name = "document_retrieval"

    async def run(
        self, db: AsyncSession, project_id: uuid.UUID | None, conversation_id: uuid.UUID, query: str
    ) -> ToolResult:
        embedding_provider = get_embedding_provider()
        [query_embedding] = await embedding_provider.embed([query])

        retriever = get_retriever()
        chunks = await retriever.retrieve(
            db, project_id, conversation_id, query_embedding, top_k=settings.retrieval_top_k
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


def _resolve_retrieval_scope(context: UserContext, conversation: Conversation) -> uuid.UUID | None:
    """Which project's knowledge base (if any) this conversation may search,
    on top of its own ad hoc uploads."""
    if conversation.type == ConversationType.PROJECT_GROUP:
        return conversation.project_id
    if conversation.linked_project_id is not None and context.is_project_member(
        conversation.linked_project_id
    ):
        return conversation.linked_project_id
    return None


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------


async def create_conversation(
    db: AsyncSession, context: UserContext, payload: ConversationCreate
) -> Conversation:
    if payload.type == ConversationType.PROJECT_GROUP:
        project = await get_project(db, payload.project_id)
        if not (context.is_project_member(project.id) or context.leads_team(project.team_id)):
            raise ForbiddenError("You are not a member of this project")
        title = payload.title or project.name
        linked_project_id = None
    else:
        if payload.linked_project_id is not None and not context.is_project_member(
            payload.linked_project_id
        ):
            raise ForbiddenError("You are not a member of the project you're trying to link")
        title = payload.title or "New conversation"
        linked_project_id = payload.linked_project_id

    conversation = Conversation(
        type=payload.type,
        project_id=payload.project_id,
        linked_project_id=linked_project_id,
        created_by=context.id,
        title=title,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def update_conversation(
    db: AsyncSession, context: UserContext, conversation: Conversation, linked_project_id: uuid.UUID | None
) -> Conversation:
    if conversation.type != ConversationType.PERSONAL:
        raise BadRequestError("Only personal conversations can have a linked project")
    if linked_project_id is not None and not context.is_project_member(linked_project_id):
        raise ForbiddenError("You are not a member of the project you're trying to link")
    conversation.linked_project_id = linked_project_id
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_user_conversations(db: AsyncSession, context: UserContext) -> list[Conversation]:
    conditions = [Conversation.created_by == context.id]
    if context.project_ids:
        conditions.append(Conversation.project_id.in_(context.project_ids))
    result = await db.execute(
        select(Conversation).where(or_(*conditions)).order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def list_messages_after(
    db: AsyncSession, conversation_id: uuid.UUID, after: uuid.UUID | None
) -> list[Message]:
    """Catch-up fetch used after a websocket reconnect: everything strictly
    newer than `after`, or the full history if `after` is None."""
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    if after is not None:
        anchor = await db.get(Message, after)
        if anchor is not None:
            stmt = stmt.where(Message.created_at > anchor.created_at)
    result = await db.execute(stmt.order_by(Message.created_at))
    return list(result.scalars().all())


def _serialize_message(message: Message) -> dict:
    return MessageRead.model_validate(message).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Personal chat (1:1 with the AI, request/response streamed over SSE)
# ---------------------------------------------------------------------------


async def get_or_create_personal_conversation(
    db: AsyncSession, context: UserContext, conversation_id: uuid.UUID | None, first_message: str
) -> Conversation:
    if conversation_id is not None:
        conversation = await db.get(Conversation, conversation_id)
        if (
            conversation is not None
            and conversation.type == ConversationType.PERSONAL
            and conversation.created_by == context.id
        ):
            return conversation

    conversation = Conversation(
        type=ConversationType.PERSONAL,
        created_by=context.id,
        title=first_message[:80],
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID, limit: int = 30) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def _build_llm_messages(
    db: AsyncSession, conversation: Conversation, context_text: str, *, group: bool
) -> list[ChatMessage]:
    """Builds the message list from persisted history.

    Assumes the current turn's user message has already been committed to the
    `messages` table by the caller, so it's picked up here as the last
    history row rather than being appended separately (which would
    duplicate it in the prompt).
    """
    history = await _load_history(db, conversation.id)

    system_content = SYSTEM_PROMPT
    if group:
        system_content += (
            f"\n\nYou are participating in a team group chat with multiple human "
            f"participants. You only get invoked when a message starts with "
            f"'{settings.ai_trigger_token}'. Each human message below is prefixed "
            f"with the sender's name so you can tell participants apart."
        )
    if context_text:
        system_content += f"\n\nRelevant internal document context:\n{context_text}"

    sender_names: dict[uuid.UUID, str] = {}
    if group:
        sender_ids = {m.sender_id for m in history if m.sender_id is not None}
        if sender_ids:
            result = await db.execute(select(User).where(User.id.in_(sender_ids)))
            sender_names = {u.id: (u.full_name or u.email) for u in result.scalars().all()}

    messages: list[ChatMessage] = [{"role": "system", "content": system_content}]
    for msg in history:
        role = "assistant" if msg.sender_type == SenderType.ASSISTANT else "user"
        content = msg.content
        if group and role == "user" and msg.sender_id is not None:
            content = f"{sender_names.get(msg.sender_id, 'User')}: {content}"
        messages.append({"role": role, "content": content})
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
    conversation = await get_or_create_personal_conversation(db, context, conversation_id, user_message)

    db.add(
        Message(
            conversation_id=conversation.id,
            sender_type=SenderType.USER,
            sender_id=context.id,
            content=user_message,
        )
    )
    await db.commit()

    project_id = _resolve_retrieval_scope(context, conversation)

    tool_result = ToolResult(used=False)
    for tool in TOOLS:
        tool_result = await tool.run(db, project_id, conversation.id, user_message)
        if tool_result.used:
            break

    yield _sse_event("start", {"conversation_id": str(conversation.id)})

    llm_messages = await _build_llm_messages(db, conversation, tool_result.context_text, group=False)
    llm_provider = get_llm_provider()

    full_response = ""
    async for delta in llm_provider.stream_chat(llm_messages):
        full_response += delta
        yield _sse_event("delta", {"content": delta})

    assistant_message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.ASSISTANT,
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


# ---------------------------------------------------------------------------
# Project group chat (multi-user, delivered over the conversation's websocket)
# ---------------------------------------------------------------------------


async def post_group_message(
    db: AsyncSession, context: UserContext, conversation: Conversation, content: str
) -> Message:
    """Persists then broadcasts a human message. If it starts with the AI
    trigger token, schedules the assistant's reply as a background task that
    streams and broadcasts on its own (not part of this response)."""
    message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.USER,
        sender_id=context.id,
        content=content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    await ws_manager.broadcast(
        conversation.id, {"event": "message", "message": _serialize_message(message)}
    )

    stripped = content.strip()
    if stripped.lower().startswith(settings.ai_trigger_token.lower()):
        query = stripped[len(settings.ai_trigger_token):].strip() or stripped
        project_id = _resolve_retrieval_scope(context, conversation)
        asyncio.create_task(
            _generate_group_ai_reply(conversation.id, project_id, message.id, query)
        )

    return message


async def _generate_group_ai_reply(
    conversation_id: uuid.UUID, project_id: uuid.UUID | None, trigger_message_id: uuid.UUID, query: str
) -> None:
    # Runs detached from the request that triggered it, so it needs its own
    # DB session rather than reusing the (by-then-closed) request session.
    from app.core.database import async_session_factory

    async with async_session_factory() as db:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            return

        tool_result = ToolResult(used=False)
        for tool in TOOLS:
            tool_result = await tool.run(db, project_id, conversation_id, query)
            if tool_result.used:
                break

        await ws_manager.broadcast(
            conversation_id,
            {"event": "assistant_start", "reply_to_message_id": str(trigger_message_id)},
        )

        llm_messages = await _build_llm_messages(db, conversation, tool_result.context_text, group=True)
        llm_provider = get_llm_provider()

        full_response = ""
        async for delta in llm_provider.stream_chat(llm_messages):
            full_response += delta
            await ws_manager.broadcast(
                conversation_id,
                {
                    "event": "assistant_delta",
                    "reply_to_message_id": str(trigger_message_id),
                    "delta": delta,
                },
            )

        assistant_message = Message(
            conversation_id=conversation_id,
            sender_type=SenderType.ASSISTANT,
            content=full_response,
            sources=[s.model_dump() for s in tool_result.sources],
            reply_to_message_id=trigger_message_id,
        )
        db.add(assistant_message)
        await db.commit()
        await db.refresh(assistant_message)

        await ws_manager.broadcast(
            conversation_id, {"event": "message", "message": _serialize_message(assistant_message)}
        )
