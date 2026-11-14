"""Setup pool (project-upload OCR/embedding charged to a shared budget), organisation monthly cap, Mistral per-page cost."""

import uuid

from sqlalchemy import select

from app.core.database import async_session_factory
from app.features.documents.ingestion import pipeline
from app.features.documents.models import Document, DocumentStatus
from app.features.usage import quota
from app.features.usage.models import LlmUsage
from app.features.usage.service import record_pages, record_usage, usage_scope
from tests.features.usage.test_quota import _chat_status, _setup, _spend
from tests.features.usage.test_token_quota import API, _world


async def _project(client, headers) -> str:
    team = await client.post(f"{API}/teams", json={"name": "T"}, headers=headers)
    project = await client.post(f"{API}/teams/{team.json()['id']}/projects", json={"name": "P"}, headers=headers)
    return project.json()["id"]


async def _pool(client, superadmin, enabled=True, budget=1.0):
    r = await client.put(f"{API}/admin/quota/setup-pool", json={"enabled": enabled, "budget_usd": budget}, headers=superadmin)
    assert r.status_code == 200
    quota.invalidate_cache()
    return r.json()


async def _upload(client, headers, project_id):
    return await client.post(f"{API}/projects/{project_id}/documents", files={"file": ("a.txt", b"hello", "text/plain")}, headers=headers)


async def test_only_super_admin_sets_pool_and_org_cap_and_overview_shows_them(client):
    superadmin, _, admin, _, user, *_ = await _world(client)
    for headers in (admin, user):
        assert (await client.put(f"{API}/admin/quota/setup-pool", json={"enabled": True}, headers=headers)).status_code == 403
        assert (await client.put(f"{API}/admin/quota/org-cap", json={"monthly_cap_usd": 10}, headers=headers)).status_code == 403
    assert (await client.put(f"{API}/admin/quota/setup-pool", json={"budget_usd": -1}, headers=superadmin)).status_code == 400
    body = await _pool(client, superadmin, True, 30)
    assert body["setup_pool"] == {"enabled": True, "budget_usd": 30.0, "used_usd": 0.0, "remaining_usd": 30.0}
    body = (await client.put(f"{API}/admin/quota/org-cap", json={"monthly_cap_usd": 135}, headers=superadmin)).json()
    assert body["org"]["monthly_cap_usd"] == 135.0
    overview = (await client.get(f"{API}/admin/quota", headers=admin)).json()
    assert overview["setup_pool"]["budget_usd"] == 30.0 and overview["org"]["monthly_cap_usd"] == 135.0
    assert (await client.put(f"{API}/admin/quota/org-cap", json={"monthly_cap_usd": None}, headers=superadmin)).json()["org"]["monthly_cap_usd"] is None


async def test_pool_pays_project_uploads_and_refuses_them_when_used_up(client):
    superadmin, _, admin, admin_id, user, user_id, *_ = await _world(client)
    await _setup(client, superadmin)
    project_id = await _project(client, admin)
    await _pool(client, superadmin, True, 1.0)
    await _spend(admin_id, 50.0)  # the uploader is far over their own quota...
    assert (await _upload(client, admin, project_id)).status_code == 200  # ...but the pool pays, so the upload is accepted

    await _spend(admin_id, 1.5, purpose="ocr", billed_to="org_setup")  # the pool (1.0) is now used up
    r = await _upload(client, admin, project_id)
    assert r.status_code == 429 and r.json()["detail"] == "setup_pool_exhausted"
    assert (await _upload(client, superadmin, project_id)).status_code == 200  # super admins pass

    await _pool(client, superadmin, True, 5.0)  # topped up
    assert (await _upload(client, admin, project_id)).status_code == 200
    await _pool(client, superadmin, False)  # pool off: the uploader's own quota applies again
    assert (await _upload(client, admin, project_id)).status_code == 429


async def test_ingestion_is_billed_to_the_pool_for_project_documents_and_to_the_user_otherwise(client, monkeypatch):
    superadmin, _, admin, admin_id, *_ = await _world(client)
    project_id = await _project(client, admin)
    doc = (await _upload(client, admin, project_id)).json()["document"]
    doc_id, path = uuid.UUID(doc["id"]), None
    async with async_session_factory() as db:
        path = (await db.get(Document, doc_id)).file_path

    async def fake_run(document_id, file_path):
        await record_usage("m", 100, 0, purpose="embedding")

    monkeypatch.setattr(pipeline, "_run_ingestion_pipeline", fake_run)
    await _pool(client, superadmin, True, 5.0)
    await pipeline.run_ingestion_pipeline(doc_id, path)
    await _pool(client, superadmin, False)
    await pipeline.run_ingestion_pipeline(doc_id, path)
    async with async_session_factory() as db:
        rows = (await db.execute(select(LlmUsage).where(LlmUsage.user_id == uuid.UUID(admin_id)).order_by(LlmUsage.id))).scalars().all()
    assert [r.billed_to for r in rows] == ["org_setup", "user"]


async def test_a_queued_document_fails_up_front_when_the_pool_is_exhausted(client, monkeypatch):
    superadmin, _, admin, admin_id, *_ = await _world(client)
    project_id = await _project(client, admin)
    doc = (await _upload(client, admin, project_id)).json()["document"]
    doc_id = uuid.UUID(doc["id"])
    async with async_session_factory() as db:
        path = (await db.get(Document, doc_id)).file_path
    ran = []

    async def fake_run(document_id, file_path):
        ran.append(document_id)

    monkeypatch.setattr(pipeline, "_run_ingestion_pipeline", fake_run)
    await _setup(client, superadmin)  # enforced
    await _pool(client, superadmin, True, 1.0)
    await _spend(admin_id, 2.0, purpose="ocr", billed_to="org_setup")
    await pipeline.run_ingestion_pipeline(doc_id, path)
    assert ran == []
    async with async_session_factory() as db:
        document = await db.get(Document, doc_id)
    assert document.status == DocumentStatus.FAILED and "اعتبار مشترک" in document.error_message


async def test_org_cap_blocks_everyone_but_super_admin_when_reached(client):
    superadmin, _, admin, admin_id, user, user_id, other, other_id = await _world(client)
    await _setup(client, superadmin)
    await client.put(f"{API}/admin/users/{other_id}/quota", json={"unlimited": True}, headers=superadmin)
    assert (await client.put(f"{API}/admin/quota/org-cap", json={"monthly_cap_usd": 2.0}, headers=superadmin)).status_code == 200
    quota.invalidate_cache()
    await _spend(user_id, 0.3)  # under the user's own caps, and under the org cap
    assert await _chat_status(client, other) != 429

    await _spend(user_id, 0.4, billed_to="org_setup")  # pool spend counts toward the org total too
    await _spend(admin_id, 1.4)  # org total 2.1 >= 2.0
    quota.invalidate_cache()
    r = await client.post(f"{API}/chat", json={"message": "hi"}, headers=other)  # even an unlimited user
    assert r.status_code == 429 and r.headers["X-Quota-Window"] == "org_monthly"
    assert await _chat_status(client, superadmin) != 429
    overview = (await client.get(f"{API}/admin/quota", headers=admin)).json()["org"]
    assert overview["month_used_usd"] >= 2.1 and overview["percent"] >= 100


async def test_mistral_page_cost_uses_the_per_page_price_and_is_zero_without_one(client):
    superadmin, _, _, _, _, user_id, *_ = await _world(client)
    uid = uuid.UUID(user_id)
    with usage_scope(uid, "ocr"):
        await record_pages("mistral-ocr-test", 3)  # no price yet: recorded, cost 0
    r = await client.put(f"{API}/admin/model-prices/mistral-ocr-test", json={"per_page_usd": 0.002}, headers=superadmin)
    assert r.status_code == 200 and r.json()["per_page_usd"] == 0.002
    with usage_scope(uid, "ocr"):
        await record_pages("mistral-ocr-test", 5)
    async with async_session_factory() as db:
        rows = (await db.execute(select(LlmUsage).where(LlmUsage.user_id == uid).order_by(LlmUsage.id))).scalars().all()
    assert [(r.pages, r.cost_micro_usd, r.counts_toward_quota, r.prompt_tokens) for r in rows] == [(3, 0, False, 0), (5, 10000, False, 0)]
