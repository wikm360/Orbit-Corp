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

    def stream_chat(self, messages, tools=None, tool_choice="auto"):
        self.calls.append(tools)
        self.calls_messages.append(messages)
        events = self._steps[len(self.calls) - 1]
        return self._stream(events)

    async def _stream(self, events):
        for event in events:
            yield event


class _AlwaysToolCallLLMProvider:
    """Simulates a model that keeps wanting to call a tool - answers with
    plain content only when it is forbidden to call tools (`tool_choice="none"`),
    which is exactly what the engine's last step (MAX_STEPS - 1) does to force a
    final answer."""

    def __init__(self):
        self.calls: list[list[dict] | None] = []
        self.choices: list[str] = []

    def stream_chat(self, messages, tools=None, tool_choice="auto"):
        self.calls.append(tools)
        self.choices.append(tool_choice)
        return self._stream(tool_choice)

    async def _stream(self, tool_choice):
        if tool_choice == "none":
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
    # Every step offers the same tool list (so the provider's prefix cache survives); the last one forbids calling them.
    assert all(tools is not None for tools in provider.calls)
    assert provider.choices[:-1] == ["auto"] * (MAX_STEPS - 1)
    assert provider.choices[-1] == "none"
    assert result.content == "final answer"


class _IgnoresToolChoiceProvider:
    """A gateway that ignores `tool_choice="none"`: always calls a tool while tools are offered; answers only when
    `tools=None` (the engine's forced-answer retry). `answer` is what it then says."""

    def __init__(self, answer: str):
        self.answer = answer
        self.calls: list[list[dict] | None] = []
        self.messages: list[list] = []

    def stream_chat(self, messages, tools=None, tool_choice="auto"):
        self.calls.append(tools)
        self.messages.append(list(messages))
        return self._stream(tools)

    async def _stream(self, tools):
        if tools:
            yield {
                "type": "tool_calls",
                "calls": [{"id": f"call_{len(self.calls)}", "name": "list_user_projects", "arguments": "{}"}],
            }
        elif self.answer:
            yield {"type": "content", "delta": self.answer}


async def test_model_ignoring_tool_choice_on_last_step_still_gets_an_answer(db_session, monkeypatch):
    user, conversation = await _seed_user_and_conversation(db_session)
    provider = _IgnoresToolChoiceProvider("forced answer")
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)

    events: list[tuple[str, dict]] = []

    async def callback(event: str, data: dict) -> None:
        events.append((event, data))

    result = await AgentEngine().run_agent_loop(db_session, conversation, _context_for(user), callback)

    assert len(provider.calls) == MAX_STEPS + 1
    assert provider.calls[-1] is None  # the retry offers no tools
    tool_notes = [m["content"] for m in provider.messages[-1] if m.get("role") == "tool"]
    assert f"[Step 1/{MAX_STEPS}:" in tool_notes[0]
    assert "no tool steps remain" in tool_notes[-1]
    assert result.content == "forced answer"
    assert ("delta", {"content": "forced answer"}) in events


async def test_empty_turn_falls_back_to_a_fixed_message(db_session, monkeypatch):
    user, conversation = await _seed_user_and_conversation(db_session)
    provider = _IgnoresToolChoiceProvider("")
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)

    events: list[tuple[str, dict]] = []

    async def callback(event: str, data: dict) -> None:
        events.append((event, data))

    result = await AgentEngine().run_agent_loop(db_session, conversation, _context_for(user), callback)

    assert result.content == engine_module._NO_ANSWER_TEXT
    assert ("delta", {"content": engine_module._NO_ANSWER_TEXT}) in events


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
                            "name": "read_entire_document",
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


class _ImageTool:
    """Stands in for `view_document_page`: returns text plus an image the engine must hand to the model."""

    name = "view_document_page"

    def __init__(self, images_per_call: int = 1):
        self.images_per_call = images_per_call

    async def execute(self, **kwargs):
        from app.features.agent.schemas import ToolExecutionResult

        n = int(kwargs.get("page_number", 1))
        return ToolExecutionResult(text=f"page {n} attached", images=[f"data:image/jpeg;base64,PAGE{n}"] * self.images_per_call)


def _engine_with_image_tool(monkeypatch):
    from app.features.agent.tools.registry import ToolRegistry

    tool = _ImageTool()
    registry = ToolRegistry([])
    monkeypatch.setattr(registry, "to_openai_tools", lambda *a, **k: [{"type": "function", "function": {"name": tool.name}}])

    async def dispatch(name, arguments, **kwargs):
        import json

        return await tool.execute(**json.loads(arguments))

    monkeypatch.setattr(registry, "dispatch", dispatch)
    return AgentEngine(registry)


async def test_page_images_reach_the_model_in_a_user_message_after_the_tool_results(db_session, monkeypatch):
    user, conversation = await _seed_user_and_conversation(db_session)
    provider = _ScriptedLLMProvider(
        [
            [{"type": "tool_calls", "calls": [
                {"id": "c1", "name": "view_document_page", "arguments": '{"page_number": 1}'},
                {"id": "c2", "name": "view_document_page", "arguments": '{"page_number": 2}'},
            ]}],
            [{"type": "content", "delta": "3 m"}],
        ]
    )
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)

    async def callback(event, data):
        pass

    result = await _engine_with_image_tool(monkeypatch).run_agent_loop(db_session, conversation, _context_for(user), callback)
    assert result.content == "3 m"

    second_call = provider.calls_messages[1]
    roles = [m["role"] for m in second_call]
    # assistant(tool_calls), tool, tool, then ONE user message with both images: tool messages stay adjacent to the call
    tail = roles[-4:]
    assert tail == ["assistant", "tool", "tool", "user"]
    images = second_call[-1]["content"]
    assert images[0]["type"] == "text" and "not from the user" in images[0]["text"]
    assert [p["image_url"]["url"] for p in images[1:]] == ["data:image/jpeg;base64,PAGE1", "data:image/jpeg;base64,PAGE2"]
    assert all(isinstance(m["content"], str) for m in second_call[-3:-1])  # tool messages are text only


async def test_page_images_are_capped_per_turn(db_session, monkeypatch):
    user, conversation = await _seed_user_and_conversation(db_session)
    monkeypatch.setattr(engine_module.settings, "agent_max_page_views_per_turn", 1)
    provider = _ScriptedLLMProvider(
        [
            [{"type": "tool_calls", "calls": [
                {"id": "c1", "name": "view_document_page", "arguments": '{"page_number": 1}'},
                {"id": "c2", "name": "view_document_page", "arguments": '{"page_number": 2}'},
            ]}],
            [{"type": "content", "delta": "ok"}],
        ]
    )
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)

    async def callback(event, data):
        pass

    await _engine_with_image_tool(monkeypatch).run_agent_loop(db_session, conversation, _context_for(user), callback)
    second_call = provider.calls_messages[1]
    assert [p["image_url"]["url"] for p in second_call[-1]["content"][1:]] == ["data:image/jpeg;base64,PAGE1"]
    assert "limit reached" in second_call[-2]["content"] and "limit reached" not in second_call[-3]["content"]


async def test_sources_block_is_hidden_validated_and_replayed_in_history(db_session, monkeypatch):
    from app.features.agent.schemas import SourceCitation, ToolExecutionResult

    user, conversation = await _seed_user_and_conversation(db_session)
    real = SourceCitation(document_id="d1", document_filename="a.pdf", chunk_index=0, snippet="s", score=0.7, page=12)
    other = SourceCitation(document_id="d2", document_filename="b.pdf", chunk_index=0, snippet="s", score=0.9, page=3)

    class _Registry(engine_module.ToolRegistry if hasattr(engine_module, "ToolRegistry") else object):
        def __init__(self):
            pass

        def to_openai_tools(self, context, conversation):
            return [{"type": "function", "function": {"name": "t", "parameters": {}}}]

        async def dispatch(self, name, arguments, **_):
            return ToolExecutionResult(text="found", citations=[real, other])

    provider = _ScriptedLLMProvider(
        [
            [{"type": "tool_calls", "calls": [{"id": "c1", "name": "t", "arguments": "{}"}]}],
            [
                {"type": "content", "delta": "جواب.\n<sou"},
                {"type": "content", "delta": "rces>a.pdf|12; ghost.pdf|1</sources>"},
            ],
        ]
    )
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)
    events = []

    async def callback(event, data):
        events.append((event, data))

    result = await AgentEngine(_Registry()).run_agent_loop(db_session, conversation, _context_for(user), callback)

    assert result.content == "جواب."
    assert [(c.document_filename, c.page) for c in result.citations] == [("a.pdf", 12)]
    assert "".join(d["content"] for e, d in events if e == "delta") == "جواب.\n"
