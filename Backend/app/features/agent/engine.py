import json
import logging
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.features.agent.schemas import AgentTurnResult, SourceCitation
from app.features.agent.tools.registry import ToolRegistry, build_default_registry
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.providers.llm_provider import ChatMessage, get_llm_provider

logger = logging.getLogger(__name__)
settings = get_settings()

# Hard cap on tool-call round-trips per turn: on the final step, tools are
# omitted from the request entirely, so the model is forced to answer with
# whatever it has learned so far rather than looping forever.
MAX_STEPS = 4

SYSTEM_PROMPT = (
    "You are the internal AI assistant for this organization. Answer clearly and "
    "concisely. You have tools to search the knowledge base, read documents, list "
    "projects and attachments, and recall or save project memory - use them "
    "whenever they would give a better-grounded answer than your own knowledge, "
    "rather than guessing or asking the user to look something up themselves."
)

# Tools whose `agent_activity` status should read "reading_documents" rather
# than the default "searching", purely for a more accurate client-side label.
_DOCUMENT_READ_TOOLS = {
    "get_document_outline",
    "read_document_pages",
    "read_entire_document",
    "get_current_chat_attachments",
    "list_project_documents",
}

AgentCallback = Callable[[str, dict], Awaitable[None]]


class AgentEngine:
    """Runs one assistant turn: builds the prompt from conversation history,
    lets the model call tools (via native tool-calling, up to `MAX_STEPS`
    round-trips), and streams the final answer out through `callback`.

    `callback(event, data)` is transport-agnostic - the caller wires it to
    SSE frames for personal chat or a websocket broadcast for group chat
    (see `chat/service.py`). Events: `agent_activity` (status updates while
    a tool runs or the final answer starts generating) and `delta` (a
    content token of the final answer).
    """

    def __init__(self, registry: ToolRegistry | None = None):
        self._registry = registry or build_default_registry()

    async def run_agent_loop(
        self,
        db: AsyncSession,
        conversation: Conversation,
        context: UserContext,
        callback: AgentCallback,
    ) -> AgentTurnResult:
        """Assumes the current turn's user message has already been
        persisted to the `messages` table by the caller, so it's picked up
        here as the last row of history rather than passed separately."""
        messages = await self._build_messages(db, conversation)
        tools = self._registry.to_openai_tools()
        llm_provider = get_llm_provider()

        all_citations: list[SourceCitation] = []
        full_response = ""

        for step in range(MAX_STEPS):
            is_last_step = step == MAX_STEPS - 1
            step_tools = None if is_last_step else tools

            content_buffer = ""
            tool_calls: list = []
            generating_emitted = False

            async for event in llm_provider.stream_chat(messages, tools=step_tools):
                if event["type"] == "content":
                    if not generating_emitted:
                        await callback("agent_activity", {"status": "generating"})
                        generating_emitted = True
                    content_buffer += event["delta"]
                    await callback("delta", {"content": event["delta"]})
                else:
                    tool_calls = event["calls"]

            if not tool_calls:
                full_response = content_buffer
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": content_buffer or None,
                    "tool_calls": [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {"name": call["name"], "arguments": call["arguments"]},
                        }
                        for call in tool_calls
                    ],
                }
            )

            for call in tool_calls:
                status = "reading_documents" if call["name"] in _DOCUMENT_READ_TOOLS else "searching"
                await callback(
                    "agent_activity",
                    {"status": status, "tool": call["name"], "args": _safe_parse_args(call["arguments"])},
                )
                result = await self._registry.dispatch(
                    call["name"], call["arguments"], db=db, context=context, conversation=conversation
                )
                all_citations.extend(result.citations)
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": result.text})

        return AgentTurnResult(content=full_response, citations=all_citations)

    async def _build_messages(self, db: AsyncSession, conversation: Conversation) -> list[ChatMessage]:
        history = await _load_history(db, conversation.id)

        system_content = SYSTEM_PROMPT
        group = conversation.type == ConversationType.PROJECT_GROUP
        if group:
            system_content += (
                f"\n\nYou are participating in a team group chat with multiple human "
                f"participants. You only get invoked when a message starts with "
                f"'{settings.ai_trigger_token}'. Each human message below is prefixed "
                f"with the sender's name so you can tell participants apart."
            )

        sender_names: dict[uuid.UUID, str] = {}
        if group:
            sender_ids = {msg.sender_id for msg in history if msg.sender_id is not None}
            if sender_ids:
                result = await db.execute(select(User).where(User.id.in_(sender_ids)))
                sender_names = {user.id: (user.full_name or user.email) for user in result.scalars().all()}

        messages: list[ChatMessage] = [{"role": "system", "content": system_content}]
        for msg in history:
            role = "assistant" if msg.sender_type == SenderType.ASSISTANT else "user"
            content = msg.content
            if group and role == "user" and msg.sender_id is not None:
                content = f"{sender_names.get(msg.sender_id, 'User')}: {content}"
            messages.append({"role": role, "content": content})
        return messages


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID, limit: int = 30) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


def _safe_parse_args(arguments_json: str) -> dict:
    try:
        return json.loads(arguments_json) if arguments_json else {}
    except (json.JSONDecodeError, TypeError):
        return {}
