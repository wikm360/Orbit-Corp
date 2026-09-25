import uuid

from app.core.dependencies import UserContext
from app.core.security import hash_password
from app.features.agent import engine as engine_module
from app.features.agent.engine import MAX_STEPS, AgentEngine
from app.features.auth.models import User, UserRole
from app.features.chat.models import Conversation, ConversationType, Message, SenderType


class _ScriptedLLMProvider:
    """Replays a fixed sequence of `StreamEvent` lists, one list per
    `stream_chat` call, so a test can script exactly how a multi-step tool
    round-trip unfolds without a real model."""

    def __init__(self, steps: list[list[dict]]):
        self._steps = steps
        self.calls: list[list[dict] | None] = []
        self.calls_messages: list[list[dict]] = []

    def stream_chat(self, messages, tools=None):
        self.calls.append(tools)
        self.calls_messages.append(messages)
        events = self._steps[len(self.calls) - 1]
        return self._stream(events)

    async def _stream(self, events):
        for event in events:
            yield event


class _AlwaysToolCallLLMProvider:
    """Simulates a model that keeps wanting to call a tool - answers with
    plain content only when it isn't offered any tools at all, which is
    exactly what the engine's last step (MAX_STEPS - 1) does to force a
    final answer."""

    def __init__(self):
        self.calls: list[list[dict] | None] = []

    def stream_chat(self, messages, tools=None):
        self.calls.append(tools)
        return self._stream(tools)

    async def _stream(self, tools):
        if tools is None:
            yield {"type": "content", "delta": "final answer"}
        else:
            yield {
                "type": "tool_calls",
                "calls": [{"id": f"call_{len(self.calls)}", "name": "list_user_projects", "arguments": "{}"}],
            }


async def _seed_user_and_conversation(db_session) -> tuple[User, Conversation]:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        hashed_password=hash_password("supersecret"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(type=ConversationType.PERSONAL, created_by=user.id, title="Test")
    db_session.add(conversation)
    await db_session.flush()

    db_session.add(
        Message(
            conversation_id=conversation.id,
            sender_type=SenderType.USER,
            sender_id=user.id,
            content="Which projects am I in?",
        )
    )
    await db_session.commit()
    await db_session.refresh(conversation)
    return user, conversation


def _context_for(user: User) -> UserContext:
    return UserContext(user=user, team_ids=[], led_team_ids=[], project_ids=[])


async def test_run_agent_loop_executes_a_tool_then_streams_the_final_answer(db_session, monkeypatch):
    user, conversation = await _seed_user_and_conversation(db_session)
    context = _context_for(user)

    provider = _ScriptedLLMProvider(
        [
            [
                {
                    "type": "tool_calls",
                    "calls": [{"id": "call_1", "name": "list_user_projects", "arguments": "{}"}],
                }
            ],
            [{"type": "content", "delta": "Here"}, {"type": "content", "delta": " you go."}],
        ]
    )
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)

    events: list[tuple[str, dict]] = []

    async def callback(event: str, data: dict) -> None:
        events.append((event, data))

    result = await AgentEngine().run_agent_loop(db_session, conversation, context, callback)

    assert result.content == "Here you go."
    assert len(provider.calls) == 2

    assert ("agent_activity", {"status": "searching", "tool": "list_user_projects", "args": {}}) in events
    assert ("agent_activity", {"status": "generating"}) in events
    assert ("delta", {"content": "Here"}) in events
    assert ("delta", {"content": " you go."}) in events


async def test_run_agent_loop_stops_at_max_steps_and_forces_a_final_answer(db_session, monkeypatch):
    user, conversation = await _seed_user_and_conversation(db_session)
    context = _context_for(user)

    provider = _AlwaysToolCallLLMProvider()
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)

    events: list[tuple[str, dict]] = []

    async def callback(event: str, data: dict) -> None:
        events.append((event, data))

    result = await AgentEngine().run_agent_loop(db_session, conversation, context, callback)

    assert len(provider.calls) == MAX_STEPS
    # Every step but the last offered tools; the last step forced an answer
    # by omitting them entirely.
    assert all(tools is not None for tools in provider.calls[:-1])
    assert provider.calls[-1] is None
    assert result.content == "final answer"


async def test_a_failing_tool_call_does_not_abort_the_turn(db_session, monkeypatch):
    """A tool that raises (here: NotFoundError, since the document doesn't
    exist) must turn into a plain-text `tool` message the model can react
    to, not propagate and kill the loop or the connection."""
    user, conversation = await _seed_user_and_conversation(db_session)
    context = _context_for(user)

    missing_document_id = str(uuid.uuid4())
    provider = _ScriptedLLMProvider(
        [
            [
                {
                    "type": "tool_calls",
                    "calls": [
                        {
                            "id": "call_1",
                            "name": "get_document_outline",
                            "arguments": f'{{"document_id": "{missing_document_id}"}}',
                        }
                    ],
                }
            ],
            [{"type": "content", "delta": "I couldn't find that document."}],
        ]
    )
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)

    events: list[tuple[str, dict]] = []

    async def callback(event: str, data: dict) -> None:
        events.append((event, data))

    result = await AgentEngine().run_agent_loop(db_session, conversation, context, callback)

    assert result.content == "I couldn't find that document."
    assert len(provider.calls) == 2

    tool_result_messages = [msg for msg in provider.calls_messages[-1] if msg.get("role") == "tool"]
    assert tool_result_messages
    assert "not accessible" in tool_result_messages[0]["content"].lower() or "not found" in tool_result_messages[
        0
    ]["content"].lower()
