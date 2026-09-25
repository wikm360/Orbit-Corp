import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError, ForbiddenError
from app.features.agent.engine import AgentEngine, AgentTurnResult
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.features.chat.schemas import ConversationCreate, MessageRead
from app.features.chat.ws import manager as ws_manager
from app.features.projects.service import get_project

settings = get_settings()

_agent_engine = AgentEngine()


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
        # Deliberately not `project.name` - a group chat's title is its own
        # independent, editable field, not a stand-in for the project name.
        title = payload.title or "New group conversation"
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
    db: AsyncSession,
    context: UserContext,
    conversation: Conversation,
    *,
    title: str | None,
    linked_project_id: uuid.UUID | None,
) -> Conversation:
    """`title` applies to any conversation type (omit to leave it
    untouched). `linked_project_id` only applies to personal conversations -
    a group conversation must still send it as `null` (the field is
    required in the request schema), which is a harmless no-op here."""
    if conversation.type == ConversationType.PERSONAL:
        if linked_project_id is not None and not context.is_project_member(linked_project_id):
            raise ForbiddenError("You are not a member of the project you're trying to link")
        conversation.linked_project_id = linked_project_id
    elif linked_project_id is not None:
        raise BadRequestError("Only personal conversations can have a linked project")

    if title is not None:
        conversation.title = title

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


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(
    context: UserContext,
    conversation_id: uuid.UUID | None,
    user_message: str,
) -> AsyncIterator[str]:
    """Runs the agent loop, streams the LLM's answer as SSE, then persists
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

    # The engine runs as a background task (same pattern this used for tool
    # status before): only that task ever touches `db`, this loop just
    # drains the queue it fills and re-yields each event as an SSE frame,
    # so tokens keep streaming to the client in near-real-time.
    event_queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

    async def on_agent_event(event: str, data: dict) -> None:
        # Wire-compatible with the client's existing SSE event names.
        sse_event = "status" if event == "agent_activity" else event
        await event_queue.put((sse_event, data))

    async def run_engine() -> AgentTurnResult:
        return await _agent_engine.run_agent_loop(db, conversation, context, on_agent_event)

    engine_task = asyncio.create_task(run_engine())
    while not engine_task.done():
        try:
            event, data = await asyncio.wait_for(event_queue.get(), timeout=0.08)
            yield _sse_event(event, data)
        except asyncio.TimeoutError:
            pass

    while not event_queue.empty():
        event, data = event_queue.get_nowait()
        yield _sse_event(event, data)

    result = await engine_task

    assistant_message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.ASSISTANT,
        content=result.content,
        sources=[s.model_dump() for s in result.citations],
    )
    db.add(assistant_message)
    await db.commit()

    yield _sse_event(
        "done",
        {
            "sources": [s.model_dump() for s in result.citations],
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
        asyncio.create_task(_generate_group_ai_reply(conversation.id, context, message.id))

    return message


async def _generate_group_ai_reply(
    conversation_id: uuid.UUID, context: UserContext, trigger_message_id: uuid.UUID
) -> None:
    # Runs detached from the request that triggered it, so it needs its own
    # DB session rather than reusing the (by-then-closed) request session.
    # `context` was already built by that request though, and only exposes
    # already-loaded scalar fields (id, role, project/team id lists), so
    # reusing it here across the session boundary is safe.
    async with async_session_factory() as db:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            return

        await ws_manager.broadcast(
            conversation_id,
            {"event": "assistant_start", "reply_to_message_id": str(trigger_message_id)},
        )

        async def on_agent_event(event: str, data: dict) -> None:
            # Wire-compatible with the client's existing broadcast event names.
            if event == "agent_activity":
                await ws_manager.broadcast(
                    conversation_id,
                    {
                        "event": "assistant_status",
                        "reply_to_message_id": str(trigger_message_id),
                        **data,
                    },
                )
            else:  # "delta"
                await ws_manager.broadcast(
                    conversation_id,
                    {
                        "event": "assistant_delta",
                        "reply_to_message_id": str(trigger_message_id),
                        "delta": data["content"],
                    },
                )

        result = await _agent_engine.run_agent_loop(db, conversation, context, on_agent_event)

        assistant_message = Message(
            conversation_id=conversation_id,
            sender_type=SenderType.ASSISTANT,
            content=result.content,
            sources=[s.model_dump() for s in result.citations],
            reply_to_message_id=trigger_message_id,
        )
        db.add(assistant_message)
        await db.commit()
        await db.refresh(assistant_message)

        await ws_manager.broadcast(
            conversation_id, {"event": "message", "message": _serialize_message(assistant_message)}
        )
