import json
import uuid
import pytest

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.features.agent.engine import AgentEngine
from app.features.agent.tools.accounting_tools import AskAccountingDbTool
from app.features.agent.tools.registry import build_default_registry
from app.features.auth.models import User, UserRole
from app.features.chat.models import Conversation, ConversationType, Message, SenderType


class _ScriptedLLMProvider:
    def __init__(self, steps: list[list[dict]]):
        self._steps = steps
        self.calls: list[list[dict] | None] = []

    def stream_chat(self, messages, tools=None, tool_choice="auto"):
        self.calls.append(tools)
        events = self._steps[len(self.calls) - 1]
        return self._stream(events)

    async def _stream(self, events):
        for event in events:
            yield event


@pytest.mark.asyncio
async def test_ask_accounting_db_tool_in_registry(monkeypatch):
    settings = get_settings()

    # Enabled
    monkeypatch.setattr(settings, "rahkaran_db_enabled", True)
    reg_enabled = build_default_registry()
    tool_names_enabled = [t.name for t in reg_enabled._tools.values()]
    assert "ask_accounting_db" in tool_names_enabled

    # Disabled
    monkeypatch.setattr(settings, "rahkaran_db_enabled", False)
    reg_disabled = build_default_registry()
    tool_names_disabled = [t.name for t in reg_disabled._tools.values()]
    assert "ask_accounting_db" not in tool_names_disabled


@pytest.mark.asyncio
async def test_agent_engine_dispatches_accounting_tool(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rahkaran_db_enabled", True)

    # Mock the service entry point used by the tool
    from app.features.db_connector.service import AccountingAnswer

    async def mock_query(db, *, question, user_id, conversation_id, **kwargs):
        return AccountingAnswer(text=f"پاسخ شبیه‌سازی‌شده برای: {question}")

    monkeypatch.setattr("app.features.db_connector.service.run_accounting_query", mock_query)

    user = User(
        id=uuid.uuid4(),
        email="test-agent@example.com",
        hashed_password="pw",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()

    conv = Conversation(
        id=uuid.uuid4(),
        type=ConversationType.PERSONAL,
        created_by=user.id,
        title="تست ابزار حسابداری",
    )
    db_session.add(conv)
    await db_session.flush()

    db_session.add(
        Message(
            conversation_id=conv.id,
            sender_type=SenderType.USER,
            sender_id=user.id,
            content="مانده حساب چقدر است؟",
            sources=[],
        )
    )
    await db_session.commit()

    # Scripted LLM calls:
    # 1. Ask tool
    # 2. Final response
    scripted_steps = [
        [
            {
                "type": "tool_calls",
                "calls": [
                    {
                        "id": "call_1",
                        "name": "ask_accounting_db",
                        "arguments": json.dumps({"question": "مانده حساب چقدر است؟"}),
                    }
                ],
            }
        ],
        [
            {"type": "content", "delta": "بر اساس اطلاعات، مانده حساب مشخص است."},
        ],
    ]
    provider = _ScriptedLLMProvider(scripted_steps)
    monkeypatch.setattr("app.features.agent.engine.get_llm_provider", lambda: provider)

    activities = []

    async def callback(event_type: str, data: dict):
        if event_type == "agent_activity":
            activities.append(data)

    engine = AgentEngine()
    context = UserContext(user=user)
    turn_result = await engine.run_agent_loop(
        db=db_session,
        conversation=conv,
        context=context,
        callback=callback,
    )

    assert "مانده حساب مشخص است" in turn_result.content
    statuses = [a.get("status") for a in activities]
    assert "querying_database" in statuses


@pytest.mark.asyncio
async def test_accounting_tool_follows_the_delegated_permission_not_the_role(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "rahkaran_db_enabled", True)

    def user(role, access=False):
        return User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.com", hashed_password="pw", role=role, accounting_access=access)

    personal = Conversation(id=uuid.uuid4(), type=ConversationType.PERSONAL, created_by=uuid.uuid4(), title="t")
    group = Conversation(id=uuid.uuid4(), type=ConversationType.PROJECT_GROUP, project_id=uuid.uuid4(), title="g")
    reg = build_default_registry()

    def offered(u, conv):
        return "ask_accounting_db" in [t["function"]["name"] for t in reg.to_openai_tools(UserContext(user=u), conv)]

    assert not offered(user(UserRole.USER), personal)
    assert not offered(user(UserRole.ADMIN), personal)  # an admin without the grant has no access
    assert offered(user(UserRole.USER, access=True), personal)  # a plain user with the grant has
    assert offered(user(UserRole.ADMIN, access=True), personal)
    assert offered(user(UserRole.SUPER_ADMIN), personal)  # super admins always
    assert not offered(user(UserRole.SUPER_ADMIN), group)  # never in a group chat: everybody there would read the reply

    for denied, conv in ((user(UserRole.ADMIN), personal), (user(UserRole.SUPER_ADMIN), group)):
        result = await reg.dispatch(
            "ask_accounting_db",
            json.dumps({"question": "حقوق مدیران چقدر است؟"}),
            db=db_session,
            context=UserContext(user=denied),
            conversation=conv,
        )
        assert "Permission Denied" in result.text
