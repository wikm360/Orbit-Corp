"""Chat tool, settings API (catalog/lexicon) and hardening."""
import uuid
from decimal import Decimal

from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.database import async_session_factory, engine
from app.core.dependencies import UserContext
from app.features.agent.tools.registry import build_default_registry
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType
from app.features.volume_report import pipeline
from app.features.volume_report.agent.playbook import build_system_prompt
from app.features.volume_report.chat_tool import GetVolumeReportTool
from tests.features.volume_report.test_api import (  # noqa: F401 - _env is an autouse fixture
    API, ROWS, _classify_all, _company, _document, _env, _holding, _new_report, _register, _world,
)


async def _published(client, tmp_path, tag, monkeypatch, label="شهریور 1405"):
    monkeypatch.setattr(get_settings(), "vr_publish_gate", "warn")
    admin, leader, leader_id, project_id, team_id = await _world(client, tag)
    company = await _company(client, leader, f"شرکت {tag}")
    rid = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id), company)
    await _classify_all(client, leader, rid)
    assert (await client.post(f"{API}/{rid}/publish", headers=leader)).status_code == 200
    return leader, leader_id, project_id, company, rid


async def _run_tool(user_id, project_id, **args):
    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(User.id == uuid.UUID(user_id)))).scalar_one()
        context = UserContext(user=user, project_ids=[uuid.UUID(project_id)])
        conv = Conversation(id=uuid.uuid4(), type=ConversationType.PERSONAL, created_by=user.id, title="t",
                            linked_project_id=uuid.UUID(project_id))
        return await GetVolumeReportTool().execute(db=db, context=context, conversation=conv, **args)


async def test_chat_tool_reads_only_published_snapshot_and_builds_artifact(client, tmp_path, monkeypatch):
    leader, leader_id, project_id, company, rid = await _published(client, tmp_path, "c", monkeypatch)
    result = await _run_tool(leader_id, project_id)
    assert "اساس" in result.text and "563" in result.text and "1,949.36" in result.text
    art = result.artifacts[0]
    assert art["type"] == "volume_table" and art["version"] == 1 and art["report_id"] == rid
    assert art["columns"] == ["آیتم", "مقدار"]
    assert len(art["rows"]) == len(art["unit_by_row"]) and "t" in art["unit_by_row"]
    by_item = await _run_tool(leader_id, project_id, group_by="site", item="base")
    assert by_item.artifacts[0]["columns"] == ["شرکت", "کارگاه", "آیتم", "مقدار"] and len(by_item.artifacts[0]["rows"]) == 1
    assert "563" in by_item.text and "1,949" not in by_item.text
    assert "No published" not in (await _run_tool(leader_id, project_id, period="شهریور")).text
    assert "No published volume report for that period" in (await _run_tool(leader_id, project_id, period="2020-01-01..2020-01-31")).text
    assert "has no rows" in (await _run_tool(leader_id, project_id, company="ناموجود")).text


async def test_chat_tool_scope_and_drafts(client, tmp_path, monkeypatch):
    admin, leader, leader_id, project_id, _ = await _world(client, "d")
    company = await _company(client, leader)
    await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id), company)
    drafts = await _run_tool(leader_id, project_id)
    assert drafts.text.startswith("No published volume report") and "awaiting_user" in drafts.text
    for number in ("1949", "563", "794"):
        assert number not in drafts.text  # draft figures never leak
    # a conversation without a linked project, or one whose project the user left, gets nothing
    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(User.id == uuid.UUID(leader_id)))).scalar_one()
        plain = Conversation(id=uuid.uuid4(), type=ConversationType.PERSONAL, created_by=user.id, title="t")
        context = UserContext(user=user, project_ids=[])
        assert (await GetVolumeReportTool().execute(db=db, context=context, conversation=plain)).text == "This conversation isn't linked to any project."
        linked = Conversation(id=uuid.uuid4(), type=ConversationType.PERSONAL, created_by=user.id, title="t", linked_project_id=uuid.UUID(project_id))
        assert (await GetVolumeReportTool().execute(db=db, context=context, conversation=linked)).text == "This conversation isn't linked to any project."


async def test_reopened_version_hides_the_superseded_one_until_republished(client, tmp_path, monkeypatch):
    leader, leader_id, project_id, company, rid = await _published(client, tmp_path, "r", monkeypatch)
    new = (await client.post(f"{API}/{rid}/reopen", headers=leader)).json()
    assert "563" in (await _run_tool(leader_id, project_id)).text  # v1 still the published truth while v2 is a draft
    await client.put(f"{API}/{new['id']}/files", json={"files": []}, headers=leader)
    assert (await client.post(f"{API}/{new['id']}/publish", headers=leader)).status_code == 409  # never run


async def test_tool_registered_only_when_enabled(monkeypatch):
    names = lambda: {t["function"]["name"] for t in build_default_registry().to_openai_tools()}
    monkeypatch.setattr(get_settings(), "volume_report_enabled", False)
    assert "get_volume_report" not in names()
    monkeypatch.setattr(get_settings(), "volume_report_enabled", True)
    assert "get_volume_report" in names()


async def test_catalog_and_lexicon_editing(client, tmp_path):
    admin, leader, leader_id, project_id, _ = await _world(client, "e")
    outsider, _ = await _register(client, "e-out@example.com")
    item = {"key": "gabion", "title_fa": "گابیون", "description_fa": "سبد سنگی", "dimension": "volume", "output_unit": "m3", "decimals": 1}
    assert (await client.post(f"{API}/settings/items", json=item, headers=outsider)).status_code == 403
    assert (await client.post(f"{API}/settings/items", json={**item, "output_unit": "kg"}, headers=leader)).status_code == 400
    assert (await client.post(f"{API}/settings/items", json={**item, "key": "Bad Key"}, headers=leader)).status_code == 422
    assert (await client.post(f"{API}/settings/items", json=item, headers=leader)).status_code == 201
    assert (await client.post(f"{API}/settings/items", json=item, headers=leader)).status_code == 409
    assert (await client.post(f"{API}/settings/items", json={**item, "key": "roll", "is_rollup": True, "rollup_of": ["nope"]}, headers=leader)).status_code == 400
    assert (await client.put(f"{API}/settings/items/gabion", json={**item, "key": "other"}, headers=leader)).status_code == 400
    assert (await client.put(f"{API}/settings/items/gabion", json={**item, "title_fa": "گابیون ۲", "is_active": False}, headers=leader)).json()["is_active"] is False
    assert "gabion" not in {c["key"] for c in (await client.get(f"{API}/catalog", headers=leader)).json()}
    assert (await client.put(f"{API}/settings/items/gabion", json=item, headers=leader)).status_code == 200
    # a new item is in the agent playbook without a deploy
    async with async_session_factory() as db:
        assert "gabion | گابیون" in await build_system_prompt(db)

    lex = {"token": "CUTTING", "kind": "hard_exclusion", "phrases": ["کاترزنی"]}
    assert (await client.post(f"{API}/settings/lexicon", json=lex, headers=outsider)).status_code == 403
    assert (await client.post(f"{API}/settings/lexicon", json={**lex, "token": "lower"}, headers=leader)).status_code == 422
    assert (await client.post(f"{API}/settings/lexicon", json=lex, headers=leader)).status_code == 201
    assert (await client.post(f"{API}/settings/lexicon", json=lex, headers=leader)).status_code == 409
    assert any(e["token"] == "CUTTING" for e in (await client.get(f"{API}/settings/lexicon", headers=leader)).json())
    company = await _company(client, leader)
    rows = [(None, "کاترزنی", "متر", 150), (None, "اجرای اساس", "متر مکعب", 5)]
    rid = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, rows=rows), company)
    groups = {g["description"]: g for g in (await client.get(f"{API}/{rid}/review/groups?state=all", headers=leader)).json()}
    assert groups["کاترزنی"]["disposition"] == "excluded" and groups["کاترزنی"]["confirmed"]  # the edited lexicon applied
    assert (await client.get(f"{API}/settings/lexicon", headers=outsider)).status_code == 200


async def test_duplicate_job_is_skipped_while_another_holds_the_lock(client, tmp_path):
    admin, leader, leader_id, project_id, _ = await _world(client, "k")
    company = await _company(client, leader)
    doc = await _document(tmp_path, project_id, leader_id)
    report = (await client.post(API, json={"project_id": project_id, "title": "r", "period_type": "week", "period_start": "2026-01-01",
                                           "period_end": "2026-01-07", "period_label": "x"}, headers=leader)).json()
    await client.put(f"{API}/{report['id']}/files", json={"files": [{"document_id": doc, "company_id": company}]}, headers=leader)
    await client.post(f"{API}/{report['id']}/run", headers=leader)
    key = pipeline._lock_key(uuid.UUID(report["id"]))
    async with engine.connect() as holder:
        await holder.scalar(text(f"SELECT pg_advisory_lock({key})"))
        await pipeline.run_report(uuid.UUID(report["id"]))
        assert (await client.get(f"{API}/{report['id']}/progress", headers=leader)).json()["status"] == "processing"  # skipped
        await holder.scalar(text(f"SELECT pg_advisory_unlock({key})"))
    await pipeline.run_report(uuid.UUID(report["id"]))
    assert (await client.get(f"{API}/{report['id']}/progress", headers=leader)).json()["status"] != "processing"


async def test_stale_processing_report_can_be_claimed_again(client, tmp_path):
    admin, leader, leader_id, project_id, _ = await _world(client, "z")
    company = await _company(client, leader)
    doc = await _document(tmp_path, project_id, leader_id)
    report = (await client.post(API, json={"project_id": project_id, "title": "r", "period_type": "week", "period_start": "2026-01-01",
                                           "period_end": "2026-01-07", "period_label": "x"}, headers=leader)).json()
    await client.put(f"{API}/{report['id']}/files", json={"files": [{"document_id": doc, "company_id": company}]}, headers=leader)
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 202
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 409  # fresh: still running
    async with engine.begin() as conn:  # the worker died long ago
        await conn.execute(text("UPDATE vr_reports SET updated_at = now() - interval '5 hours' WHERE id = :i"), {"i": report["id"]})
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 202


# ---- pipe laying (لوله‌گذاری, metres) --------------------------------------------------------------------------

PIPE_ROWS = [
    (None, "لوله گذاری با لوله های جوشی 1600", "متر طول", 1080),
    (None, "لوله رانی در هر نوع زمین", "متر", 24),
    (None, "ریسه کردن لوله 1600 کنار کانال", "عدد", 61),
    (None, "نوار عایق بندی لوله انقباضی حرارتی", "متر مربع", 143),
    (None, "لوله کاروگیت با اجرا (به طول 66 متر)", "سری", 1),
]


async def test_pipe_laying_is_in_the_catalog_and_the_lexicon_hints_it():
    from app.features.volume_report.extraction.normalize import Lexicon, normalize_text

    tokens = Lexicon.from_seed().tokenize(normalize_text("لوله‌گذاری با لوله های جوشی 1600"))
    assert "PIPE" in tokens
    assert "PIPE" in Lexicon.from_seed().tokenize(normalize_text("لوله رانی در هر نوع زمین"))
    assert "PIPE" not in Lexicon.from_seed().tokenize(normalize_text("رنگ عایق داخلی لوله"))  # paint on a pipe is not laying


async def test_pipe_laying_counts_metres_and_leaves_non_length_rows_visible(client, tmp_path):
    admin, leader, leader_id, project_id, _ = await _world(client, "pl")
    company = await _company(client, leader)
    rid = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, rows=PIPE_ROWS), company)
    cat = {c["key"]: c for c in (await client.get(f"{API}/catalog", headers=leader)).json()}
    assert cat["pipe_laying"]["output_unit"] == "m" and cat["pipe_laying"]["dimension"] == "length" and len(cat) == 16
    groups = {g["description"]: g for g in (await client.get(f"{API}/{rid}/review/groups?state=all", headers=leader)).json()}
    # unit "عدد" / "سری" are non-physical by the system rule; the m2 insulation row stays open for a human
    assert groups["ریسه کردن لوله 1600 کنار کانال"]["disposition"] == "nonphysical"
    assert groups["لوله کاروگیت با اجرا (به طول 66 متر)"]["disposition"] == "nonphysical"
    assert groups["لوله گذاری با لوله های جوشی 1600"]["disposition"] == "needs_input"
    pick = lambda d, item, role="execute": {"group_key": groups[d]["group_key"], "item_key": item, "role": role}
    r = await client.post(f"{API}/{rid}/review/confirm", json={"items": [
        pick("لوله گذاری با لوله های جوشی 1600", "pipe_laying"), pick("لوله رانی در هر نوع زمین", "pipe_laying")]}, headers=leader)
    assert r.status_code == 200
    assert (await _holding(client, leader, rid))["pipe_laying"] == Decimal("1104")
    # metres into a metre item need no conversion parameter; square metres cannot become metres -> rejected with a reason
    from app.features.volume_report.convert import find_path
    assert find_path("m", "m") == [] and find_path("m2", "m") is None
    other = (await client.get(f"{API}/{rid}/results?include=other", headers=leader)).json()["other"]
    assert any(o["description"].startswith("نوار عایق") for o in other)


async def test_existing_database_gets_the_new_item_and_token_without_touching_edits(client):
    from sqlalchemy import delete

    from app.features.volume_report.models import Item, LexiconEntry
    from app.features.volume_report.seed import ensure_seeded

    async with async_session_factory() as db:
        await ensure_seeded(db)
        edited = (await db.execute(select(Item).where(Item.key == "base"))).scalar_one()
        edited.title_fa = "اساس (ویرایش‌شده)"
        await db.execute(delete(Item).where(Item.key == "pipe_laying"))
        await db.execute(delete(LexiconEntry).where(LexiconEntry.token == "PIPE"))
        await db.commit()
    async with async_session_factory() as db:
        await ensure_seeded(db)
        items = {i.key: i for i in (await db.execute(select(Item))).scalars()}
        assert "pipe_laying" in items and items["pipe_laying"].sort_order > items["mining_load"].sort_order
        assert items["base"].title_fa == "اساس (ویرایش‌شده)"  # the admin's edit survived
        assert (await db.execute(select(LexiconEntry).where(LexiconEntry.token == "PIPE"))).scalar_one().phrases
        await ensure_seeded(db)
        assert len((await db.execute(select(Item).where(Item.key == "pipe_laying"))).scalars().all()) == 1  # idempotent
