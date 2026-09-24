import asyncio
import json
import re
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError, ForbiddenError
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.features.chat.schemas import ConversationCreate, MessageRead, SourceCitation
from app.features.chat.ws import manager as ws_manager
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.features.projects.service import get_project
from app.features.retrieval.access_filter import accessible_documents_filter
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
    """A capability the chat orchestrator can call before asking the LLM to respond."""

    name: str

    @abstractmethod
    async def run(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        conversation_id: uuid.UUID,
        query: str,
        on_status: Callable[[str], Awaitable[None]] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ToolResult:
        ...


class DocumentInspectorTool(Tool):
    """Inspects and reads specific documents referenced directly by mentions (@filename),
    explicit file names, or conversational references (e.g. 'in this file').
    
    Provides structured inspection (chunk counting, section navigation) to prevent
    context overflow on large files while ensuring immediate targeted retrieval.
    """
    name = "document_inspector"

    async def run(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        conversation_id: uuid.UUID,
        query: str,
        on_status: Callable[[str], Awaitable[None]] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ToolResult:
        # 1. Fetch all documents accessible in current conversation scope (including user personal docs)
        stmt = (
            select(Document)
            .where(accessible_documents_filter(project_id, conversation_id, user_id=user_id))
            .order_by(Document.created_at.desc())
        )
        res = await db.execute(stmt)
        accessible_docs = list(res.scalars().all())
        if not accessible_docs:
            return ToolResult(used=False)

        # 2. Extract potential mentions (@filename)
        mentions = re.findall(r"@([^\s@]+)", query)
        bot_tokens = {"bot", settings.ai_trigger_token.lstrip("@").lower()}
        file_mentions = [m.lower() for m in mentions if m.lower() not in bot_tokens]

        # 3. Match against accessible documents
        matched_docs: list[Document] = []
        lowered_query = query.lower()

        # Check explicit @mentions
        for doc in accessible_docs:
            doc_lower = doc.filename.lower()
            if any(doc_lower == fm or fm in doc_lower or doc_lower.startswith(fm) for fm in file_mentions):
                if doc not in matched_docs:
                    matched_docs.append(doc)

        # Check explicit filename mentioned in query text (without @)
        if not matched_docs:
            for doc in accessible_docs:
                doc_lower = doc.filename.lower()
                # Check either exact filename or stem if at least 4 characters
                stem = doc_lower.rsplit(".", 1)[0] if "." in doc_lower else doc_lower
                if doc_lower in lowered_query or (len(stem) >= 4 and stem in lowered_query):
                    if doc not in matched_docs:
                        matched_docs.append(doc)

        # Check general conversational reference if files were uploaded in this conversation
        # (e.g. "توی فایل", "محتوای فایل", "این سند چی میگه", "فایل پیوست")
        if not matched_docs:
            file_referential_terms = [
                "فایل", "سند", "پیوست", "ضمیمه", "محتوای", "توی فایل", "توی این فایل",
                "file", "document", "attachment", "what is inside", "summary of the file"
            ]
            has_doc_reference = any(term in lowered_query for term in file_referential_terms)
            if has_doc_reference:
                # Pick the latest document in this conversation
                conv_docs = [d for d in accessible_docs if d.conversation_id == conversation_id]
                if conv_docs:
                    matched_docs.append(conv_docs[0])

        if not matched_docs:
            return ToolResult(used=False)

        # 4. Inspect and read matched documents smartly
        all_context_blocks: list[str] = []
        all_sources: list[SourceCitation] = []

        # Target section / page regex (e.g. "صفحه ۲", "بخش ۳", "section 2", "page 5")
        section_match = re.search(r"(?:صفحه|بخش|قسمت|part|page|section)\s*(\d+)", lowered_query)
        requested_page_or_section = int(section_match.group(1)) if section_match else None

        for doc in matched_docs[:2]:  # inspect up to 2 targeted documents
            if on_status:
                await on_status(f"در حال بازرسی ساختار و تحلیل سند «{doc.filename}»...")

            # Inspect chunk count
            count_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc.id)
            total_chunks = (await db.scalar(count_stmt)) or 0

            if total_chunks == 0:
                all_context_blocks.append(f"[سند: {doc.filename}]\nاین سند ثبت شده اما هنوز قطعه متنی برای آن ایجاد نشده است.")
                continue

            chunks: list[DocumentChunk] = []

            if requested_page_or_section is not None:
                # Target the requested section and its neighboring chunk
                target_idx = max(0, requested_page_or_section - 1)
                chunk_stmt = (
                    select(DocumentChunk)
                    .where(
                        DocumentChunk.document_id == doc.id,
                        DocumentChunk.chunk_index.between(max(0, target_idx - 1), target_idx + 2),
                    )
                    .order_by(DocumentChunk.chunk_index)
                )
                chunk_res = await db.execute(chunk_stmt)
                chunks = list(chunk_res.scalars().all())

            # If small document, read entirely to preserve full context
            elif total_chunks <= 5:
                chunk_stmt = (
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == doc.id)
                    .order_by(DocumentChunk.chunk_index)
                )
                chunk_res = await db.execute(chunk_stmt)
                chunks = list(chunk_res.scalars().all())

            else:
                # If large document:
                # Check if user asked a specific topical question to perform focused semantic search within this document
                clean_query = query
                for fm in file_mentions:
                    clean_query = clean_query.replace(f"@{fm}", "")
                clean_query = clean_query.replace(doc.filename, "").strip()

                is_generic_inquiry = any(clean_query.startswith(g) or clean_query == g for g in [
                    "توی این فایل چی نوشته", "توی فایل چی نوشته", "توی فایل چیه", "خلاصه کن",
                    "چی نوشته", "محتواش چیه", "محتوای فایل رو بگو", "بررسی کن", ""
                ]) or len(clean_query) < 10

                if not is_generic_inquiry:
                    # Semantic search constrained to this specific document
                    if on_status:
                        await on_status(f"در حال جستجوی بخش‌های مرتبط در سند «{doc.filename}»...")
                    try:
                        embedding_provider = get_embedding_provider()
                        [query_embedding] = await embedding_provider.embed([clean_query])
                        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
                        top_stmt = (
                            select(DocumentChunk)
                            .where(DocumentChunk.document_id == doc.id)
                            .order_by(distance)
                            .limit(min(5, settings.retrieval_top_k))
                        )
                        chunk_res = await db.execute(top_stmt)
                        chunks = list(chunk_res.scalars().all())
                    except Exception:
                        chunks = []

                if not chunks:
                    # Fallback to the opening chunks with inspection note
                    chunk_stmt = (
                        select(DocumentChunk)
                        .where(DocumentChunk.document_id == doc.id)
                        .order_by(DocumentChunk.chunk_index)
                        .limit(5)
                    )
                    chunk_res = await db.execute(chunk_stmt)
                    chunks = list(chunk_res.scalars().all())

            doc_text_parts = [f"=== مستند: {doc.filename} (مجموع کل بخش‌ها: {total_chunks}) ==="]
            for c in chunks:
                doc_text_parts.append(f"[بخش {c.chunk_index + 1} از سند {doc.filename}]\n{c.content}")
                all_sources.append(
                    SourceCitation(
                        document_id=str(doc.id),
                        document_filename=doc.filename,
                        chunk_index=c.chunk_index,
                        snippet=c.content[:300],
                        score=1.0,
                    )
                )

            if total_chunks > len(chunks):
                doc_text_parts.append(
                    f"\n[نکته ساختاری: این سند شامل مجموعاً {total_chunks} بخش است. در حال حاضر {len(chunks)} بخش منتخب بارگذاری شده‌اند.]"
                )

            all_context_blocks.append("\n\n".join(doc_text_parts))

        if not all_context_blocks:
            return ToolResult(used=False)

        return ToolResult(
            used=True,
            context_text="\n\n" + ("\n\n---\n\n".join(all_context_blocks)),
            sources=all_sources,
        )


class RetrievalTool(Tool):
    name = "document_retrieval"

    async def run(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        conversation_id: uuid.UUID,
        query: str,
        on_status: Callable[[str], Awaitable[None]] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ToolResult:
        if on_status:
            await on_status("در حال جستجو در پایگاه دانش...")
        embedding_provider = get_embedding_provider()
        [query_embedding] = await embedding_provider.embed([query])

        retriever = get_retriever()
        chunks = await retriever.retrieve(
            db, project_id, conversation_id, query_embedding, top_k=settings.retrieval_top_k, user_id=user_id
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


TOOLS: list[Tool] = [DocumentInspectorTool(), RetrievalTool()]



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
            # (created_at, id) is a total order: messages sharing a timestamp
            # are neither skipped nor repeated across catch-up fetches.
            stmt = stmt.where(
                tuple_(Message.created_at, Message.id) > tuple_(anchor.created_at, anchor.id)
            )
    result = await db.execute(stmt.order_by(Message.created_at, Message.id))
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
    context: UserContext,
    conversation_id: uuid.UUID | None,
    user_message: str,
) -> AsyncIterator[str]:
    """Runs the retrieval tool, streams the LLM's answer as SSE, then persists
    the user + assistant messages once the stream completes.

    Owns its DB session: FastAPI (< 0.118) closes request-scoped `yield`
    dependencies before a StreamingResponse body starts iterating, so a
    session injected into the endpoint would already be closed here.
    """
    async with async_session_factory() as db:
        async for event in _stream_chat_events(db, context, conversation_id, user_message):
            yield event


async def _stream_chat_events(
    db: AsyncSession,
    context: UserContext,
    conversation_id: uuid.UUID | None,
    user_message: str,
) -> AsyncIterator[str]:
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

    yield _sse_event("start", {"conversation_id": str(conversation.id)})

    project_id = _resolve_retrieval_scope(context, conversation)

    status_queue: asyncio.Queue[str] = asyncio.Queue()

    async def on_status(status_msg: str) -> None:
        await status_queue.put(status_msg)

    async def run_tools() -> ToolResult:
        res = ToolResult(used=False)
        for tool in TOOLS:
            res = await tool.run(db, project_id, conversation.id, user_message, on_status=on_status, user_id=context.id)
            if res.used:
                break
        return res

    tools_task = asyncio.create_task(run_tools())
    while not tools_task.done():
        try:
            status_msg = await asyncio.wait_for(status_queue.get(), timeout=0.08)
            yield _sse_event("status", {"status": status_msg})
        except asyncio.TimeoutError:
            pass

    while not status_queue.empty():
        status_msg = status_queue.get_nowait()
        yield _sse_event("status", {"status": status_msg})

    tool_result = await tools_task

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
    async with async_session_factory() as db:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            return

        await ws_manager.broadcast(
            conversation_id,
            {"event": "assistant_start", "reply_to_message_id": str(trigger_message_id)},
        )

        async def on_group_status(status_msg: str) -> None:
            await ws_manager.broadcast(
                conversation_id,
                {
                    "event": "assistant_status",
                    "reply_to_message_id": str(trigger_message_id),
                    "status": status_msg,
                },
            )

        trigger_message = await db.get(Message, trigger_message_id)
        trigger_user_id = trigger_message.sender_id if trigger_message else None

        tool_result = ToolResult(used=False)
        for tool in TOOLS:
            tool_result = await tool.run(db, project_id, conversation_id, query, on_status=on_group_status, user_id=trigger_user_id)
            if tool_result.used:
                break

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
