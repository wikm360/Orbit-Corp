import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.features.agent.schemas import AgentTurnResult, SourceCitation, ToolExecutionResult
from app.features.agent.scope import resolve_retrieval_scope
from app.features.agent.tools.folder_tools import project_tree_summary
from app.features.agent.tools.registry import ToolRegistry, build_default_registry
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.features.documents import service as documents_service
from app.providers.llm_provider import ChatMessage, get_llm_provider

logger = logging.getLogger(__name__)
settings = get_settings()

# Hard cap on tool-call round-trips per turn: on the final step the model may not call tools (`tool_choice="none"`), so
# it must answer with whatever it has learned so far rather than looping forever.
# browse folders -> search -> (reworded search | read the exact pages) -> answer needs room; the last step caps the cost.
MAX_STEPS = 8

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
    "Document and image processing: ALL documents and images uploaded to this system (PDFs, Word documents, "
    "scanned letters, and images like PNG/JPEG) are automatically pre-processed by a multi-stage layout OCR pipeline. "
    "Their full extracted text is already clean, indexed, and directly accessible via your document tools.\n\n"
    "How to read and answer questions about documents and images:\n"
    "1. When the user mentions a document by name or asks for the full text, content, transcription, or summary of a document or image "
    "(e.g., '@doc.pdf', 'متن این تصویر را بده', 'کل نامه را بنویس', 'فایل را بخوان'): Find its document_id from the chat uploaded files list or "
    "the project tree (or call browse_folder if it is in a folder), then immediately call 'read_entire_document' or 'read_document_pages'. "
    "You can also pass its filename or document_id to get_document_info to inspect its page count and facts. "
    "Never conclude a mentioned document is missing just because the chat uploaded files list is empty - always check the project tree or browse_folder!\n"
    "2. For specific topical or factual questions across documents (e.g., specific terms, numbers, clauses, dates): "
    "Use 'search_knowledge_base' with a targeted Persian query describing the fact/topic. Its results already include the "
    "full text of matching pages.\n"
    "3. Visual inspection ('view_document_page'): Use ONLY for non-text visual graphics such as architectural/engineering "
    "drawings (beams, dimensions drawn on blueprints), floor plans, maps, or graphical diagrams where visual layout inspection "
    "is strictly necessary. NEVER use view_document_page to read or transcribe textual letters, documents, or forms.\n"
    "4. Spreadsheets (xlsx / xls / csv): for any exact value, lookup of a person or row, filter, count, sum, average or ranking, call "
    "'describe_spreadsheet' once (to learn the real column names) and then 'query_spreadsheet' with SQL - do NOT read numbers out of "
    "search or page text, which loses the column alignment. Quote the values exactly as returned, and cite the sheet and the "
    "`_row` (and file column letter when given) from the result - never invent a sheet, row or column. If the name the user typed "
    "matches no row, say so plainly and offer the similar names the tool lists; never answer for a different person without asking."
)

_PROJECT_TREE_INTRO = (
    "\n\nProject knowledge base - top level (folders show their total file counts):\n"
    "Explore it like a file manager: when the question names a folder, a topic area, a document type or a file, call "
    "browse_folder on the matching folder (then its subfolders) to find the file and open it with read_document_pages / "
    "read_entire_document. search_knowledge_base also matches file and folder names and accepts path_prefix to search "
    "inside one folder. Do NOT conclude that something is missing from the knowledge base before you have browsed the "
    "relevant folder; a file whose status is not 'ready' (processing / failed / unsupported / cancelled) exists but cannot "
    "be read yet - tell the user that instead of saying it does not exist.\n"
)

# Tools whose `agent_activity` status should read "reading_documents" rather
# than the default "searching", purely for a more accurate client-side label.
_DOCUMENT_READ_TOOLS = {
    "get_document_info",
    "read_document_pages",
    "view_document_page",
    "read_entire_document",
    "get_current_chat_attachments",
    "browse_folder",
    "describe_spreadsheet",
    "query_spreadsheet",
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
        messages = await self._build_messages(db, conversation, context)
        tools = self._registry.to_openai_tools(context, conversation)
        llm_provider = get_llm_provider()

        turn_start = time.monotonic()
        user_msg = messages[-1].get("content", "") if messages else ""
        user_preview = " ".join(str(user_msg)[:120].split())
        logger.info("=" * 70)
        logger.info(
            "[AGENT:TURN_START] Conv: %s | User: %s",
            conversation.id,
            getattr(context, "email", "user"),
        )
        logger.info("[AGENT:USER_QUERY] %s", repr(user_preview))

        all_citations: list[SourceCitation] = []
        all_artifacts: list[dict] = []
        # Identical tool calls (same name + arguments) within one turn run once: the model sometimes issues the same call twice
        # (in parallel or in consecutive steps); repeating a database question costs two LLM calls and two queries for nothing.
        executed_calls: dict[tuple[str, str], ToolExecutionResult] = {}
        full_response = ""
        page_images_sent = 0

        for step in range(MAX_STEPS):
            is_last_step = step == MAX_STEPS - 1
            # The last step keeps the same tool list but forbids calling one: dropping `tools` would change the start of
            # the request and throw away the provider's prefix cache for the whole prompt.
            extra = {"tool_choice": "none"} if is_last_step and tools else {}
            step_tools = tools or None

            content_buffer = ""
            tool_calls: list = []
            generating_emitted = False

            async for event in llm_provider.stream_chat(messages, tools=step_tools, **extra):
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

                logger.info(
                    "[AGENT:TOOL_CALL] Step %d/%d -> Function '%s' | Args: %s",
                    step + 1,
                    MAX_STEPS,
                    call["name"],
                    call["arguments"],
                )
                tool_t0 = time.monotonic()
                result = await self._registry.dispatch(
                    call["name"], call["arguments"], db=db, context=context, conversation=conversation
                )
                tool_dur = time.monotonic() - tool_t0
                preview_text = " ".join(result.text[:90].split()) if result.text else ""
                logger.info(
                    "[AGENT:TOOL_RESULT] '%s' in %.2fs -> %d chars, %d citations, %d images | Preview: %s",
                    call["name"],
                    tool_dur,
                    len(result.text),
                    len(result.citations),
                    len(result.images),
                    repr(preview_text),
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

        turn_dur = time.monotonic() - turn_start
        logger.info(
            "[AGENT:TURN_COMPLETE] Turn finished in %.2fs | Response: %d chars | Citations: %d | Artifacts: %d",
            turn_dur,
            len(full_response),
            len(all_citations),
            len(all_artifacts),
        )
        logger.info("=" * 70)

        return AgentTurnResult(content=full_response, citations=all_citations, artifacts=all_artifacts)

    async def _build_messages(
        self, db: AsyncSession, conversation: Conversation, context: UserContext | None = None
    ) -> list[ChatMessage]:
        history = await _load_history(db, conversation.id)

        # Order matters for the provider's prefix cache: everything that is identical from turn to turn comes first, then
        # what changes rarely (the project tree), then what changes often (this chat's uploads).
        system_content = SYSTEM_PROMPT
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

        project_id = resolve_retrieval_scope(context, conversation) if context is not None else None
        if project_id is not None:
            tree = await project_tree_summary(db, project_id)
            system_content += _PROJECT_TREE_INTRO + (tree or "(the project has no files yet)")

        # Metadata only - never file content. The model decides which of
        # these to open, and in what order, using the document tools.
        attachments = await documents_service.list_conversation_documents(db, conversation.id)
        if attachments:
            listing = "\n".join(
                f"- {doc.filename} (document_id: {doc.id}, status: {doc.status.value})"
                for doc in attachments[:_MAX_LISTED_ATTACHMENTS]
            )
            system_content += (
                "\n\nFiles uploaded directly to this chat (all text and OCR processing is completed; "
                "to read the full text/transcription of an uploaded file or image, call read_entire_document with its document_id):\n"
                + listing
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
