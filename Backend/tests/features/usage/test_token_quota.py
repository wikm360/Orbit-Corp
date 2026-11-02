"""Per-user token quota: metering, admin operations, and where the limit is enforced."""

import uuid

from sqlalchemy import select

from app.core.database import async_session_factory
from app.features.agent import engine as engine_module
from app.features.agent.engine import AgentEngine
from app.features.auth.models import User
from app.features.usage.models import LlmUsage
from app.features.usage.service import record_usage, usage_purpose, usage_scope
from tests.features.agent.test_engine import _context_for, _seed_user_and_conversation

API = "/api/v1"


async def _register(client, email: str) -> tuple[dict, str]:
    body = (await client.post(f"{API}/auth/register", json={"email": email, "password": "supersecret"})).json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


async def _world(client):
    superadmin, super_id = await _register(client, "quota-super@example.com")  # first user = super admin
    admin, admin_id = await _register(client, "quota-admin@example.com")
    user, user_id = await _register(client, "quota-user@example.com")
    other, other_id = await _register(client, "quota-other@example.com")
    assert (await client.patch(f"{API}/admin/users/{admin_id}/role", json={"role": "admin"}, headers=superadmin)).status_code == 200
    return superadmin, super_id, admin, admin_id, user, user_id, other, other_id


async def _state(user_id: str) -> User:
    async with async_session_factory() as db:
        return await db.get(User, uuid.UUID(user_id), populate_existing=True)


async def test_usage_is_recorded_per_user_and_unmetered_purposes_do_not_count(client):
    _, _, _, _, _, user_id, _, other_id = await _world(client)
    uid, oid = uuid.UUID(user_id), uuid.UUID(other_id)
    await record_usage("m", 10, 5)  # no scope: ignored
    with usage_scope(uid, "chat"):
        await record_usage("m", 100, 50, 20)
        with usage_purpose("sql"):
            await record_usage("m", 30, 10)
        await record_usage("emb", 40, purpose="embedding")  # recorded, never limited
        await record_usage("m", 0, 0)  # empty usage: nothing to record
    with usage_scope(oid, "chat"):
        await record_usage("m", 7, 3)

    assert (await _state(user_id)).tokens_used == 190
    assert (await _state(other_id)).tokens_used == 10
    async with async_session_factory() as db:
        rows = (await db.execute(select(LlmUsage).where(LlmUsage.user_id == uid).order_by(LlmUsage.id))).scalars().all()
    assert [(r.purpose, r.counts_toward_quota, r.cached_tokens) for r in rows] == [("chat", True, 20), ("sql", True, 0), ("embedding", False, 0)]


async def test_admin_sets_extends_resets_and_removes_a_limit(client):
    superadmin, _, admin, _, user, user_id, _, _ = await _world(client)
    url = f"{API}/admin/users/{user_id}/token-limit"
    assert (await client.put(url, json={"limit": 1000}, headers=admin)).json()["token_limit"] == 1000
    with usage_scope(uuid.UUID(user_id), "chat"):
        await record_usage("m", 600, 100)

    listed = {u["id"]: u for u in (await client.get(f"{API}/admin/users", headers=admin)).json()}[user_id]
    assert (listed["token_limit"], listed["tokens_used"]) == (1000, 700)
    me = (await client.get(f"{API}/auth/me", headers=user)).json()
    assert (me["token_limit"], me["tokens_used"]) == (1000, 700)

    extended = (await client.post(f"{url}/extend", json={"add": 500}, headers=admin)).json()
    assert (extended["token_limit"], extended["tokens_used"]) == (1500, 700)  # usage untouched
    reset = (await client.post(f"{url}/reset", headers=admin)).json()
    assert (reset["token_limit"], reset["tokens_used"]) == (1500, 0)

    report = (await client.get(f"{API}/admin/users/{user_id}/token-usage", headers=admin)).json()
    assert report["used"] == 0 and report["by_purpose"] == []  # the period restarted...
    assert report["daily"] and report["daily"][0]["tokens"] == 700  # ...but the history is kept

    removed = (await client.put(url, json={"limit": None}, headers=admin)).json()
    assert removed["token_limit"] is None


async def test_validation_and_who_may_manage_whom(client):
    superadmin, super_id, admin, admin_id, user, user_id, other, other_id = await _world(client)
    url = lambda uid: f"{API}/admin/users/{uid}/token-limit"  # noqa: E731
    assert (await client.put(url(user_id), json={"limit": 0}, headers=admin)).status_code == 400
    assert (await client.put(url(user_id), json={"limit": -5}, headers=admin)).status_code == 400
    assert (await client.post(f"{url(user_id)}/extend", json={"add": 10}, headers=admin)).status_code == 400  # no limit to extend
    assert (await client.put(url(uuid.uuid4()), json={"limit": 10}, headers=admin)).status_code == 404

    assert (await client.put(url(user_id), json={"limit": 10}, headers=user)).status_code == 403  # a plain user cannot
    assert (await client.put(url(super_id), json={"limit": 10}, headers=superadmin)).status_code == 400  # never a super admin
    assert (await client.put(url(admin_id), json={"limit": 10}, headers=admin)).status_code == 403  # an admin cannot limit an admin
    assert (await client.put(url(admin_id), json={"limit": 10}, headers=superadmin)).status_code == 200
    assert (await client.get(f"{API}/admin/users/{user_id}/token-usage", headers=user)).status_code == 403


async def test_personal_chat_is_refused_with_429_once_the_quota_is_used(client):
    superadmin, _, admin, _, user, user_id, _, _ = await _world(client)
    await client.put(f"{API}/admin/users/{user_id}/token-limit", json={"limit": 100}, headers=admin)
    with usage_scope(uuid.UUID(user_id), "chat"):
        await record_usage("m", 100, 0)

    refused = await client.post(f"{API}/chat", json={"message": "hi"}, headers=user)
    assert refused.status_code == 429 and refused.json()["detail"] == "token_quota_exceeded"
    async with async_session_factory() as db:
        from app.features.chat.models import Message

        assert (await db.execute(select(Message).where(Message.sender_id == uuid.UUID(user_id)))).first() is None  # nothing was saved

    await client.post(f"{API}/admin/users/{user_id}/token-limit/reset", headers=admin)  # renewed: allowed again
    from app.features.usage.service import is_exhausted

    assert not is_exhausted(await _state(user_id))


async def test_a_turn_stops_between_steps_when_the_quota_runs_out_mid_turn(db_session, monkeypatch):
    user, conversation = await _seed_user_and_conversation(db_session)
    user.token_limit = 1000
    await db_session.commit()

    class _Provider:
        def __init__(self):
            self.calls = 0

        def stream_chat(self, messages, tools=None, tool_choice="auto"):
            self.calls += 1
            return self._stream()

        async def _stream(self):
            await record_usage("m", 600, 500)  # what the real provider reports after the call: 1100 > 1000
            yield {"type": "tool_calls", "calls": [{"id": f"c{self.calls}", "name": "list_user_projects", "arguments": "{}"}]}

    provider = _Provider()
    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: provider)
    deltas: list[str] = []

    async def callback(event, data):
        if event == "delta":
            deltas.append(data["content"])

    result = await AgentEngine().run_agent_loop(db_session, conversation, _context_for(user), callback)
    assert provider.calls == 1  # no second model call after the limit was crossed
    assert "سقف مصرف توکن" in result.content and deltas == [result.content]


async def test_super_admin_is_never_limited(client):
    superadmin, super_id, *_ = await _world(client)
    async with async_session_factory() as db:
        user = await db.get(User, uuid.UUID(super_id))
        user.token_limit, user.tokens_used = 1, 999
        await db.commit()
    from app.features.usage.service import is_exhausted

    assert not is_exhausted(await _state(super_id))
