import json
import logging
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.features.agent.schemas import AgentTurnResult, SourceCitation, ToolExecutionResult
from app.features.agent.tools.registry import ToolRegistry, build_default_registry
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.features.documents import service as documents_service
from app.providers.llm_provider import ChatMessage, get_llm_provider

logger = logging.getLogger(__name__)
settings = get_settings()

# Hard cap on tool-call round-trips per turn: on the final step, tools are
# omitted from the request entirely, so the model is forced to answer with
# whatever it has learned so far rather than looping forever.
# search -> (reworded search | read the exact pages) -> answer needs room; the last step has no tools, which caps the cost.
MAX_STEPS = 6

# Caps the attachment metadata injected into the prompt each turn.
_MAX_LISTED_ATTACHMENTS = 50

SYSTEM_PROMPT = (
    "You are the internal AI assistant for this organization. Answer clearly and "
    "concisely. You have tools to search the knowledge base, read documents, list "
    "projects and attachments, and recall or save project memory - use them "
    "whenever they would give a better-grounded answer than your own knowledge, "
    "rather than guessing or asking the user to look something up themselves. "
    "You can only see two kinds of files: this chat's own uploads and the "
    "project's knowledge base. Never claim to have read a file you did not open "
    "with a tool, and never describe a file that a tool did not return.\n\n"
    "How to answer questions about documents: ALWAYS start with search_knowledge_base (specific query; keep exact "
    "numbers, codes and names). Its results already contain the full text of the best-matching pages, so answer from "
    "them when they suffice. If they do not, search again with a reworded or narrower query; only if a hit is clearly "
    "the right place but you need more around it, read just those pages with read_document_pages (a few pages, never a "
    "whole large document). Use read_entire_document only for a short document or when the user explicitly asks for a "
    "summary/overview of the whole file. Do not read pages 'to be safe' - every page you read costs context.\n\n"
    "Pictures: some pages are engineering drawings, maps or scans whose text comes out as loose numbers with no labels "
    "(a page note may say so). If the answer is a dimension/level/label read off a drawing, or the page text cannot say "
    "what a number measures, do NOT guess from the loose numbers or from other pages: find the page with "
    "search_knowledge_base, then call view_document_page with that document_id and page number - the page image is "
    "attached to your next message and you read it yourself. Say where on the drawing you read a number; if you cannot "
    "tie it to the drawing, say you are not sure."
)

# Tools whose `agent_activity` status should read "reading_documents" rather
# than the default "searching", purely for a more accurate client-side label.
_DOCUMENT_READ_TOOLS = {
    "get_document_info",
    "read_document_pages",
    "view_document_page",
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
        tools = self._registry.to_openai_tools(context, conversation)
        llm_provider = get_llm_provider()

        all_citations: list[SourceCitation] = []
        all_artifacts: list[dict] = []
        # Identical tool calls (same name + arguments) within one turn run once: the model sometimes issues the same call twice
        # (in parallel or in consecutive steps); repeating a database question costs two LLM calls and two queries for nothing.
        executed_calls: dict[tuple[str, str], ToolExecutionResult] = {}
        full_response = ""
        page_images_sent = 0

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

            step_images: list[str] = []
            for call in tool_calls:
                call_key = (call["name"], _canonical_args(call["arguments"]))
                if call_key in executed_calls:
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": executed_calls[call_key].text})
                    continue
                if call["name"] in _DOCUMENT_READ_TOOLS:
                    status = "reading_documents"
                elif call["name"] == "ask_accounting_db":
                    status = "querying_database"
                else:
                    status = "searching"
                await callback(
                    "agent_activity",
                    {"status": status, "tool": call["name"], "args": _safe_parse_args(call["arguments"])},
                )
                result = await self._registry.dispatch(
                    call["name"], call["arguments"], db=db, context=context, conversation=conversation
                )
                executed_calls[call_key] = result
                all_citations.extend(result.citations)
                all_artifacts.extend(result.artifacts)
                # Delivered immediately (not only with the final message) so the client can show e.g. the database result
                # even if the model's closing summary fails to stream.
                for artifact in result.artifacts:
                    await callback("artifact", {"artifact": artifact})
                tool_text = result.text
                if result.images:
                    room = max(0, settings.agent_max_page_views_per_turn - page_images_sent)
                    kept = result.images[:room]
                    page_images_sent += len(kept)
                    step_images.extend(kept)
                    if len(kept) < len(result.images):
                        tool_text += (
                            f"\n(Page-image limit reached for this turn ({settings.agent_max_page_views_per_turn}): "
                            "this page was NOT attached. Answer from what you have and say so.)"
                        )
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": tool_text})

            if step_images:
                # Tool messages are text-only, and they must directly follow the assistant's tool calls: the page images go
                # in one user message after all of them. They are not saved to the conversation, only used for this turn.
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "[System message, not from the user: the page image(s) you asked to see are attached "
                                    "below, in the order you requested them. Look at them yourself to answer the user's "
                                    "last question; quote numbers exactly as drawn and say where on the page you read them.]"
                                ),
                            },
                            *({"type": "image_url", "image_url": {"url": url, "detail": "high"}} for url in step_images),
                        ],
                    }
                )

        return AgentTurnResult(content=full_response, citations=all_citations, artifacts=all_artifacts)

    async def _build_messages(self, db: AsyncSession, conversation: Conversation) -> list[ChatMessage]:
        history = await _load_history(db, conversation.id)

        system_content = SYSTEM_PROMPT

        # Metadata only - never file content. The model decides which of
        # these to open, and in what order, using the document tools.
        attachments = await documents_service.list_conversation_documents(db, conversation.id)
        if attachments:
            listing = "\n".join(
                f"- {doc.filename} (document_id: {doc.id}, status: {doc.status.value})"
                for doc in attachments[:_MAX_LISTED_ATTACHMENTS]
            )
            system_content += (
                "\n\nFiles uploaded to this chat (metadata only; read one with your "
                "document tools when it is relevant to the question):\n" + listing
            )
        group = conversation.type == ConversationType.PROJECT_GROUP
        if group:
            system_content += (
                f"\n\nYou are participating in a team group chat with multiple human "
                f"participants. You only get invoked when a message starts with "
                f"'{settings.ai_trigger_token}'. Each human message below is prefixed "
                f"with the sender's name so you can tell participants apart."
            )

        if settings.rahkaran_db_enabled:
            system_content += (
                "\n\nYou have access to the company's official accounting database via the "
                "'ask_accounting_db' tool. When asked about financial reports, accounts, vouchers, contract costs, "
                "customer/vendor balances, payroll, employee counts, or company assets, query the database "
                "with ask_accounting_db. Call it ONCE per question (a self-contained Persian question that includes any "
                "name, period or contract mentioned earlier in the chat). The user's screen shows the exact SQL and the full result "
                "table under your reply, so keep your answer short, quote figures exactly as they appear in the returned table, "
                "state the unit (Rial / Toman) and mention if the data are provisional; never invent numbers. "
                "Never state how many rows the table has yourself: quote only the 'total rows' figure from the tool result. "
                "If the tool result says zero rows or that no query could be built, say that the query returned nothing / could not be built "
                "(and which filters were applied) - never claim that the data does not exist, and never invent a reason."
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


def _canonical_args(arguments_json: str) -> str:
    try:
        return json.dumps(json.loads(arguments_json) if arguments_json else {}, sort_keys=True, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return arguments_json or ""


def _safe_parse_args(arguments_json: str) -> dict:
    try:
        return json.loads(arguments_json) if arguments_json else {}
    except (json.JSONDecodeError, TypeError):
        return {}
