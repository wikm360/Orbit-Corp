import uuid

import pytest

from app.core.dependencies import UserContext
from app.features.agent.engine import AgentEngine
from app.features.auth.models import User
from app.features.chat.financial import FINANCIAL_PLACEHOLDER
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.features.chat.service import _serialize_message

SECRET = "حقوق مدیرعامل ۹۹٬۹۹۹٬۹۹۹"


async def _register(client, email):
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret"})
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, uuid.UUID(body["user"]["id"])


async def _make_admin(client, super_headers, user_id):
    r = await client.patch(f"/api/v1/admin/users/{user_id}/role", json={"role": "admin"}, headers=super_headers)
    assert r.status_code == 200


def _grant(client, headers, user_id, enabled=True):
    return client.put(f"/api/v1/admin/users/{user_id}/accounting-access", json={"enabled": enabled}, headers=headers)


async def _me(client, headers):
    return (await client.get("/api/v1/auth/me", headers=headers)).json()


@pytest.mark.asyncio
async def test_super_admin_grants_and_revokes_for_any_user(client):
    root, root_id = await _register(client, "root@example.com")  # first user = super admin
    plain, plain_id = await _register(client, "plain@example.com")
    boss, boss_id = await _register(client, "boss@example.com")
    await _make_admin(client, root, boss_id)

    assert (await _me(client, root))["accounting_access"] is True  # super admins always
    assert (await _me(client, plain))["accounting_access"] is False
    assert (await _me(client, boss))["accounting_access"] is False  # an admin does not get it from the role any more

    granted = await _grant(client, root, plain_id)
    assert granted.status_code == 200 and granted.json()["accounting_access_granted_at"] is not None
    assert (await _me(client, plain))["accounting_access"] is True  # immediately, no new token needed
    assert (await _grant(client, root, boss_id)).status_code == 200
    assert (await _me(client, boss))["accounting_access"] is True

    assert (await _grant(client, root, plain_id, enabled=False)).status_code == 200
    assert (await _me(client, plain))["accounting_access"] is False
    users = {u["id"]: u for u in (await client.get("/api/v1/admin/users", headers=root)).json()}
    assert users[str(plain_id)]["accounting_access"] is False and users[str(boss_id)]["accounting_access"] is True


@pytest.mark.asyncio
async def test_only_super_admin_can_delegate_and_super_admin_cannot_be_changed(client):
    root, root_id = await _register(client, "root@example.com")
    boss, boss_id = await _register(client, "boss@example.com")
    plain, plain_id = await _register(client, "plain@example.com")
    await _make_admin(client, root, boss_id)
    await _grant(client, root, boss_id)

    assert (await _grant(client, boss, plain_id)).status_code == 403  # even an admin who holds access cannot delegate it
    assert (await _grant(client, plain, plain_id)).status_code == 403
    assert (await _grant(client, root, root_id, enabled=False)).status_code == 400  # no lock-out
    assert (await _grant(client, root, uuid.uuid4())).status_code == 404
    assert (await _me(client, root))["accounting_access"] is True


@pytest.mark.asyncio
async def test_create_user_with_access_and_the_old_500_on_admin_creation(client):
    root, _ = await _register(client, "root@example.com")
    boss, boss_id = await _register(client, "boss@example.com")
    await _make_admin(client, root, boss_id)

    created = await client.post(
        "/api/v1/admin/users",
        json={"email": "cfo@example.com", "password": "supersecret", "full_name": "CFO", "role": "admin", "accounting_access": True},
        headers=root,
    )
    assert created.status_code == 201 and created.json()["accounting_access"] is True and created.json()["role"] == "admin"

    denied = await client.post(
        "/api/v1/admin/users",
        json={"email": "x@example.com", "password": "supersecret", "full_name": "X", "accounting_access": True},
        headers=boss,
    )
    assert denied.status_code == 403
    plain_ok = await client.post(
        "/api/v1/admin/users", json={"email": "y@example.com", "password": "supersecret", "full_name": "Y"}, headers=boss
    )
    assert plain_ok.status_code == 201 and plain_ok.json()["accounting_access"] is False


@pytest.mark.asyncio
async def test_accounting_oversight_endpoints_need_admin_and_access(client):
    root, _ = await _register(client, "root@example.com")
    boss, boss_id = await _register(client, "boss@example.com")
    plain, plain_id = await _register(client, "plain@example.com")
    await _make_admin(client, root, boss_id)

    assert (await client.get("/api/v1/accounting-db/queries", headers=boss)).status_code == 403  # admin without access
    assert (await client.get("/api/v1/accounting-db/queries", headers=plain)).status_code == 403
    await _grant(client, root, plain_id)
    assert (await client.get("/api/v1/accounting-db/queries", headers=plain)).status_code == 403  # access but not an admin
    await _grant(client, root, boss_id)
    assert (await client.get("/api/v1/accounting-db/queries", headers=boss)).status_code == 200
    assert (await client.get("/api/v1/accounting-db/queries/stats", headers=root)).status_code == 200


async def _financial_chat(db_session, owner_id):
    conv = Conversation(id=uuid.uuid4(), type=ConversationType.PERSONAL, created_by=owner_id, title="مالی")
    db_session.add(conv)
    await db_session.flush()
    db_session.add_all(
        [
            Message(conversation_id=conv.id, sender_type=SenderType.USER, sender_id=owner_id, content="حقوق؟", sources=[]),
            Message(
                conversation_id=conv.id,
                sender_type=SenderType.ASSISTANT,
                content=SECRET,
                sources=[{"document_id": "d", "document_filename": "f", "chunk_index": 0, "snippet": SECRET, "score": 1.0}],
                artifacts=[{"type": "sql_result", "rows": [[SECRET]]}],
                contains_financial=True,
            ),
        ]
    )
    await db_session.commit()
    return conv


@pytest.mark.asyncio
async def test_financial_replies_are_withheld_from_readers_without_access(client, db_session):
    root, _ = await _register(client, "root@example.com")
    owner, owner_id = await _register(client, "owner@example.com")
    boss, boss_id = await _register(client, "boss@example.com")
    await _make_admin(client, root, boss_id)
    await _grant(client, root, owner_id)
    conv = await _financial_chat(db_session, owner_id)

    def assistant(messages):
        return [m for m in messages if m["sender_type"] == "assistant"][0]

    detail = (await client.get(f"/api/v1/chat/conversations/{conv.id}", headers=owner)).json()
    assert assistant(detail["messages"])["content"] == SECRET and assistant(detail["messages"])["artifacts"]

    # an admin who reads someone else's chat but holds no accounting access sees a placeholder, on both read paths
    for messages in (
        (await client.get(f"/api/v1/chat/conversations/{conv.id}", headers=boss)).json()["messages"],
        (await client.get(f"/api/v1/chat/conversations/{conv.id}/messages", headers=boss)).json(),
    ):
        reply = assistant(messages)
        assert reply["content"] == FINANCIAL_PLACEHOLDER and reply["artifacts"] == [] and reply["sources"] == []
        assert reply["contains_financial"] is True
        assert SECRET not in str(messages)

    # revoking the owner's access hides their own history too
    await _grant(client, root, owner_id, enabled=False)
    assert assistant((await client.get(f"/api/v1/chat/conversations/{conv.id}/messages", headers=owner)).json())["content"] == FINANCIAL_PLACEHOLDER
    # a super admin always sees it
    assert assistant((await client.get(f"/api/v1/chat/conversations/{conv.id}/messages", headers=root)).json())["content"] == SECRET


@pytest.mark.asyncio
async def test_model_history_and_group_broadcast_never_carry_financial_content(client, db_session):
    root, _ = await _register(client, "root@example.com")
    owner, owner_id = await _register(client, "owner@example.com")
    conv = await _financial_chat(db_session, owner_id)
    owner_user = await db_session.get(User, owner_id)

    engine = AgentEngine()
    without = await engine._build_messages(db_session, conv, UserContext(user=owner_user))
    assert SECRET not in str(without) and FINANCIAL_PLACEHOLDER in str(without)

    owner_user.accounting_access = True
    await db_session.commit()
    with_access = await engine._build_messages(db_session, conv, UserContext(user=owner_user))
    assert SECRET in str(with_access)

    message = (await db_session.execute(__import__("sqlalchemy").select(Message).where(Message.contains_financial.is_(True)))).scalars().first()
    assert SECRET not in str(_serialize_message(message))  # a websocket broadcast reaches everyone in the chat
