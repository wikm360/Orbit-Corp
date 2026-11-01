import uuid

from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.features.volume_report import pipeline
from app.features.volume_report.models import Decision, Item
from tests.features.volume_report.test_api import (  # noqa: F401 - _env is an autouse fixture
    API, _classify_all, _company, _document, _env, _groups, _new_report, _register, _world,
)


async def _setup(client, tmp_path, tag):
    admin, leader, leader_id, project_id, _ = await _world(client, tag)
    company = await _company(client, leader)
    rid = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id), company)
    await _classify_all(client, leader, rid)
    return leader, leader_id, project_id, company, rid


async def test_confirmed_decision_gets_embedding_and_is_found_by_similarity(client, tmp_path):
    leader, _, _, _, _ = await _setup(client, tmp_path, "s")
    async with async_session_factory() as db:
        decisions = (await db.execute(select(Decision))).scalars().all()
        assert decisions and all(d.embedding is not None and d.hits == 0 for d in decisions)
    found = (await client.get(f"{API}/settings/decisions/similar", params={"text": "اجرای اساس لایه"}, headers=leader)).json()
    assert found and found[0]["description"] == "اجرای اساس" and found[0]["item_key"] == "base" and found[0]["role"] == "execute"
    filtered = (await client.get(f"{API}/settings/decisions/similar", params={"text": "اجرای اساس", "unit": "kg"}, headers=leader)).json()
    assert all(f["unit"] == "kg" for f in filtered)


async def test_exact_match_counts_hits_and_second_run_needs_nothing(client, tmp_path):
    leader, leader_id, project_id, company, _ = await _setup(client, tmp_path, "h")
    second = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, name="b.xlsx"), company)
    assert (await client.get(f"{API}/{second}/progress", headers=leader)).json()["status"] in ("awaiting_user", "needs_review", "ready")
    g = await _groups(client, leader, second)
    assert all(x["confirmed"] for x in g.values())
    decisions = (await client.get(f"{API}/settings/decisions", headers=leader)).json()
    assert next(d for d in decisions if d["description"] == "اجرای اساس")["hits"] == 1


async def test_revoked_decision_is_no_longer_applied_or_suggested(client, tmp_path):
    leader, leader_id, project_id, company, _ = await _setup(client, tmp_path, "r")
    decisions = (await client.get(f"{API}/settings/decisions", headers=leader)).json()
    target = next(d for d in decisions if d["description"] == "اجرای اساس")
    assert (await client.post(f"{API}/settings/decisions/{target['id']}/revoke", headers=leader)).status_code == 200
    assert all(d["id"] != target["id"] for d in (await client.get(f"{API}/settings/decisions", headers=leader)).json())
    assert any(d["id"] == target["id"] and d["revoked_at"] for d in (await client.get(f"{API}/settings/decisions?include_revoked=true", headers=leader)).json())
    found = (await client.get(f"{API}/settings/decisions/similar", params={"text": "اجرای اساس"}, headers=leader)).json()
    assert all(f["decision_id"] != target["id"] for f in found)
    second = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, name="b.xlsx"), company)
    g = await _groups(client, leader, second)
    assert g["اجرای اساس"]["disposition"] == "needs_input" and g["اجرای زیراساس"]["source"] == "memory"


async def test_decision_pointing_to_inactive_item_is_not_applied(client, tmp_path):
    leader, leader_id, project_id, company, _ = await _setup(client, tmp_path, "i")
    async with async_session_factory() as db:
        await db.execute(update(Item).where(Item.key == "base").values(is_active=False))
        await db.commit()
    second = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, name="b.xlsx"), company)
    g = await _groups(client, leader, second)
    assert g["اجرای اساس"]["disposition"] == "needs_input" and g["اجرای اساس"]["reason"] == "memory_item_inactive"


async def test_catalog_version_grows_with_decision_changes(client, tmp_path):
    leader, _, _, _, rid = await _setup(client, tmp_path, "v")
    async with async_session_factory() as db:
        from app.features.volume_report.seed import current_catalog_version
        before = await current_catalog_version(db)
    target = (await client.get(f"{API}/settings/decisions", headers=leader)).json()[0]
    await client.post(f"{API}/settings/decisions/{target['id']}/revoke", headers=leader)
    async with async_session_factory() as db:
        assert await current_catalog_version(db) == before + 1


async def test_decisions_endpoints_require_leader_or_admin(client, tmp_path):
    await _setup(client, tmp_path, "a")
    outsider, _ = await _register(client, "nobody@example.com")
    assert (await client.get(f"{API}/settings/decisions", headers=outsider)).status_code == 403
    assert (await client.get(f"{API}/settings/decisions/similar", params={"text": "x"}, headers=outsider)).status_code == 403
    assert (await client.post(f"{API}/settings/decisions/{uuid.uuid4()}/revoke", headers=outsider)).status_code == 403
