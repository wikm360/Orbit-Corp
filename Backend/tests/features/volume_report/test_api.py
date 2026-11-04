"""End-to-end volume report flow on synthetic workbooks. Requires Postgres (like the rest of the suite)."""
import uuid
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.features.documents.models import Document, DocumentStatus
from app.features.volume_report import pipeline, service
from app.features.volume_report.models import Company
from app.features.volume_report.router import router as vr_router
from app.main import app
from tests.features.volume_report.extraction.builders import add_income_sheet, save

API = "/api/v1/volume-reports"


class _DownProvider:
    async def complete(self, *a, **kw):
        raise RuntimeError("LLM unavailable")

ROWS = [
    (None, "تهیه و حمل زیراساس", "متر مکعب", 794.17),
    (None, "اجرای زیراساس", "متر مکعب", 1949.36),
    (None, "تهیه و حمل مصالح اساس", "متر مکعب", 986),
    (None, "اجرای اساس", "متر مکعب", 563),
    (None, "آرماتور بندی", "کیلوگرم", 10490.18),
    (None, "آرماتور بندی شمع", "کیلوگرم", 32676.75),
    (None, "قالب بندی", "متر مربع", 700),
    (None, "اضافه بهای قالب بندی انحنا", "متر مربع", 5),
    (None, "آسفالت بیندر", "مترمربع سانتی متر", 109483.9),
    (None, "بتن ریزی پی", "متر مکعب", 25),
    (None, "بتن ریزی شمع", "متر مکعب", 29.48),
    (None, "حمل مصالح بتن ریزی شمع", "متر مکعب", 29.48),
    (None, "اجاره ماشین آلات", "مقطوع", 1),
]
TITLE = "گزارش درآمد پروژه سیرجان قطروئیه در ماه شهریور 1405"


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    queued = []
    monkeypatch.setattr(service, "_enqueue", lambda report_id, mode="full", user_id=None: queued.append(report_id))
    from app.features.volume_report import memory
    from tests.conftest import _StubEmbeddingProvider
    monkeypatch.setattr(memory, "get_embedding_provider", lambda: _StubEmbeddingProvider())
    # No test may reach a real LLM: by default the agent is "down", so groups stay needs_input (reason agent_failed).
    monkeypatch.setattr(pipeline, "get_vr_llm_provider", lambda: _DownProvider())
    if not any(getattr(r, "path", "").startswith(f"{get_settings().api_prefix}/volume-reports") for r in app.routes):
        app.include_router(vr_router, prefix=get_settings().api_prefix)
    return queued


async def _register(client, email):
    body = (await client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret"})).json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


async def _world(client, tag="a"):
    admin, _ = await _register(client, f"owner-{tag}@example.com")
    leader, leader_id = await _register(client, f"leader-{tag}@example.com")
    team_id = (await client.post("/api/v1/teams", json={"name": f"t-{tag}"}, headers=admin)).json()["id"]
    await client.post(f"/api/v1/teams/{team_id}/members", json={"user_id": leader_id, "role": "leader"}, headers=admin)
    project_id = (await client.post(f"/api/v1/teams/{team_id}/projects", json={"name": f"p-{tag}"}, headers=leader)).json()["id"]
    return admin, leader, leader_id, project_id, team_id


async def _document(tmp_path, project_id, uploader_id, rows=ROWS, name="a.xlsx", status=DocumentStatus.READY, title=TITLE, qty_label="حجم"):
    wb = Workbook()
    add_income_sheet(wb, "درآمد", rows, title=title, qty_label=qty_label)
    path = save(wb, tmp_path, f"{uuid.uuid4().hex}.xlsx")
    async with async_session_factory() as db:
        doc = Document(filename=name, file_path=path, content_type="application/octet-stream", status=status,
                       content_hash=uuid.uuid4().hex + uuid.uuid4().hex, project_id=uuid.UUID(project_id), uploaded_by=uuid.UUID(uploader_id))
        db.add(doc)
        await db.commit()
        return str(doc.id)


async def _company(client, headers, name="محورگستر"):
    return (await client.post(f"{API}/settings/companies", json={"name": name}, headers=headers)).json()["id"]


async def _new_report(client, headers, project_id, doc_id, company_id):
    report = (await client.post(API, json={"project_id": project_id, "title": "r", "period_type": "month", "period_start": "2026-08-23",
                                           "period_end": "2026-09-22", "period_label": "شهریور 1405"}, headers=headers)).json()
    r = await client.put(f"{API}/{report['id']}/files", json={"files": [{"document_id": doc_id, "company_id": company_id}]}, headers=headers)
    assert r.status_code == 200, r.text
    assert (await client.post(f"{API}/{report['id']}/run", headers=headers)).status_code == 202
    await pipeline.run_report(uuid.UUID(report["id"]))
    return report["id"]


async def _groups(client, headers, rid):
    return {g["description"]: g for g in (await client.get(f"{API}/{rid}/review/groups?state=all", headers=headers)).json()}


def _confirm(g, item=None, role="execute", reason=None, scope="global"):
    body = {"group_key": g["group_key"], "role": role, "remember_scope": scope}
    body.update({"item_key": item} if item else {"exclude_reason": reason})
    return body


async def _classify_all(client, headers, rid):
    g = await _groups(client, headers, rid)
    items = [
        _confirm(g["تهیه و حمل زیراساس"], "subbase", "supply"), _confirm(g["اجرای زیراساس"], "subbase"),
        _confirm(g["تهیه و حمل مصالح اساس"], "base", "supply"), _confirm(g["اجرای اساس"], "base"),
        _confirm(g["آرماتور بندی"], "rebar"), _confirm(g["آرماتور بندی شمع"], "rebar"), _confirm(g["قالب بندی"], "formwork"),
        _confirm(g["آسفالت بیندر"], "asphalt_binder"), _confirm(g["بتن ریزی پی"], "concrete"), _confirm(g["بتن ریزی شمع"], "concrete"),
        _confirm(g["حمل مصالح بتن ریزی شمع"], reason="duplicate"),
    ]
    r = await client.post(f"{API}/{rid}/review/confirm", json={"items": items}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["issues"]


async def _holding(client, headers, rid):
    rows = (await client.get(f"{API}/{rid}/results?group_by=holding", headers=headers)).json()["rows"]
    return {r["item_key"]: Decimal(r["qty"]) for r in rows}


async def test_full_flow_reference_values_gate_publish_and_reopen(client, tmp_path):
    admin, leader, leader_id, project_id, _ = await _world(client)
    doc = await _document(tmp_path, project_id, leader_id)
    company = await _company(client, leader)
    rid = await _new_report(client, leader, project_id, doc, company)

    g = await _groups(client, leader, rid)
    assert g["اضافه بهای قالب بندی انحنا"]["disposition"] == "excluded" and g["اضافه بهای قالب بندی انحنا"]["confirmed"]
    assert g["اجاره ماشین آلات"]["disposition"] == "nonphysical"
    assert g["اجرای اساس"]["disposition"] == "needs_input" and not g["اجرای اساس"]["confirmed"]
    assert (await client.get(f"{API}/{rid}/progress", headers=leader)).json()["status"] == "awaiting_user"  # site-kind card
    assert await _holding(client, leader, rid) == {}

    issues = await _classify_all(client, leader, rid)
    assert {i["code"] for i in issues} == {"site_kind_unconfirmed", "open_questions"}
    h = await _holding(client, leader, rid)
    assert h["subbase"] == Decimal("1949.36") and h["base"] == Decimal("563") and h["formwork"] == Decimal("700")
    assert h["rebar"] == Decimal("43.1669") and h["concrete"] == Decimal("54.48")
    assert h["asphalt_binder"] == Decimal("2572.8717") == h["asphalt_total"]

    # strict gate: unconfirmed site kind blocks publishing
    r = await client.post(f"{API}/{rid}/publish", headers=leader)
    assert r.status_code == 409 and "site_kind_unconfirmed" in r.text and "open_questions" in r.text
    site = (await client.get(f"{API}/settings/sites", headers=leader)).json()[0]
    assert site["kind"] == "road"
    assert (await client.put(f"{API}/settings/sites/{site['id']}", json={"kind": "road"}, headers=leader)).status_code == 200
    await client.post(f"{API}/{rid}/recompute", headers=leader)
    assert (await client.get(f"{API}/{rid}/progress", headers=leader)).json()["status"] == "ready"

    trace = (await client.get(f"{API}/{rid}/trace?item_key=concrete", headers=leader)).json()
    assert {t["description"] for t in trace} == {"بتن ریزی پی", "بتن ریزی شمع"} and trace[0]["row_no"] and trace[0]["filename"] == "a.xlsx"
    assert (await client.get(f"{API}/{rid}/export?format=csv", headers=leader)).content.startswith(b"\xef\xbb\xbf")
    assert (await client.get(f"{API}/{rid}/export?format=xlsx", headers=leader)).status_code == 200

    published = await client.post(f"{API}/{rid}/publish", headers=leader)
    assert published.status_code == 200 and published.json()["status"] == "published"
    # immutable
    assert (await client.put(f"{API}/{rid}/files", json={"files": []}, headers=leader)).status_code == 409
    assert (await client.post(f"{API}/{rid}/run", headers=leader)).status_code == 409
    assert (await client.delete(f"{API}/{rid}", headers=leader)).status_code == 409
    again = await client.post(f"{API}/{rid}/reopen", headers=leader)
    assert again.status_code == 201 and again.json()["version"] == 2 and again.json()["supersedes_id"] == rid
    assert (await client.post(f"{API}/{rid}/reopen", headers=leader)).status_code == 409


async def test_memory_applies_on_a_second_report_without_questions(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "m")
    company = await _company(client, leader)
    first = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id), company)
    await _classify_all(client, leader, first)
    second = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, name="b.xlsx"), company)
    g = await _groups(client, leader, second)
    assert all(x["confirmed"] for x in g.values())
    assert g["اجرای اساس"]["source"] == "memory"
    assert (await _holding(client, leader, second))["base"] == Decimal("563")


async def test_line_scope_decision_survives_rerun_but_is_not_remembered(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "l")
    company = await _company(client, leader)
    doc = await _document(tmp_path, project_id, leader_id)
    rid = await _new_report(client, leader, project_id, doc, company)
    g = await _groups(client, leader, rid)
    await client.post(f"{API}/{rid}/review/confirm", json={"items": [_confirm(g["اجرای اساس"], "base", scope="line")]}, headers=leader)
    await client.post(f"{API}/{rid}/run", headers=leader)
    await pipeline.run_report(uuid.UUID(rid))
    assert (await _groups(client, leader, rid))["اجرای اساس"]["source"] == "human"
    other = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, name="c.xlsx"), company)
    assert (await _groups(client, leader, other))["اجرای اساس"]["disposition"] == "needs_input"


async def test_access_rules(client, tmp_path):
    admin, leader, leader_id, project_id, team_id = await _world(client, "x")
    company = await _company(client, leader)
    doc = await _document(tmp_path, project_id, leader_id)
    rid = await _new_report(client, leader, project_id, doc, company)
    outsider, _ = await _register(client, "outsider@example.com")

    for method, path in [("get", f"{API}/{rid}"), ("get", f"{API}/{rid}/results"), ("get", f"{API}/{rid}/lines"), ("get", f"{API}/{rid}/sources"),
                         ("post", f"{API}/{rid}/run"), ("post", f"{API}/{rid}/publish"), ("get", f"{API}/{rid}/export")]:
        assert (await getattr(client, method)(path, headers=outsider)).status_code == 403, path
    assert (await client.get(f"{API}?project_id={project_id}", headers=outsider)).status_code == 403
    assert (await client.post(API, json={"project_id": project_id, "title": "x", "period_type": "week", "period_start": "2026-01-01",
                                         "period_end": "2026-01-07", "period_label": "x"}, headers=outsider)).status_code == 403
    assert (await client.get(f"{API}/{uuid.uuid4()}", headers=leader)).status_code == 404
    # settings: only admins / team leaders
    assert (await client.post(f"{API}/settings/companies", json={"name": "z"}, headers=outsider)).status_code == 403
    assert (await client.put(f"{API}/settings/conversions", json={"key": "density_t_per_m3", "value": 2.4, "unit": "t/m3"}, headers=outsider)).status_code == 403
    c_res = await client.put(f"{API}/settings/conversions", json={"key": "thickness_m", "value": 0.1, "unit": "m"}, headers=leader)
    assert c_res.status_code == 200
    conv_id = c_res.json()["id"]
    assert (await client.delete(f"{API}/settings/conversions/{conv_id}", headers=outsider)).status_code == 403
    assert (await client.delete(f"{API}/settings/conversions/{conv_id}", headers=leader)).status_code == 204
    assert (await client.delete(f"{API}/settings/conversions/{conv_id}", headers=leader)).status_code == 404
    assert (await client.get(f"{API}/catalog", headers=outsider)).status_code == 200

    # files: other project's document, non-READY, wrong extension, unknown company
    other_project = (await client.post(f"/api/v1/teams/{team_id}/projects", json={"name": "other"}, headers=leader)).json()["id"]
    foreign = await _document(tmp_path, other_project, leader_id)
    processing = await _document(tmp_path, project_id, leader_id, status=DocumentStatus.PROCESSING)
    docx = await _document(tmp_path, project_id, leader_id, name="a.docx")
    pdf = await _document(tmp_path, project_id, leader_id, name="a.pdf")
    base = f"{API}/{rid}/files"
    put = lambda d, c=company: client.put(base, json={"files": [{"document_id": d, "company_id": c}]}, headers=leader)
    assert (await put(foreign)).status_code == 404
    assert (await put(processing)).status_code == 400
    assert (await put(docx)).status_code == 400
    assert (await put(pdf)).status_code == 200
    assert (await put(doc, str(uuid.uuid4()))).status_code == 404
    # a report of another project is invisible to its members (403: not a member)
    other_report = (await client.post(API, json={"project_id": other_project, "title": "o", "period_type": "week", "period_start": "2026-01-01",
                                                 "period_end": "2026-01-07", "period_label": "x"}, headers=leader)).json()["id"]
    member2, member2_id = await _register(client, "member2@example.com")
    await client.post(f"/api/v1/teams/{team_id}/members", json={"user_id": member2_id, "role": "member"}, headers=admin)
    assert (await client.get(f"{API}/{other_report}", headers=member2)).status_code == 403


async def test_path_outside_upload_dir_is_refused(client, tmp_path, monkeypatch):
    _, leader, leader_id, project_id, _ = await _world(client, "p")
    doc = await _document(tmp_path, project_id, leader_id)
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path / "elsewhere"))
    company = await _company(client, leader)
    r = await client.put(f"{API}/{(await client.post(API, json={'project_id': project_id, 'title': 't', 'period_type': 'week', 'period_start': '2026-01-01', 'period_end': '2026-01-07', 'period_label': 'x'}, headers=leader)).json()['id']}/files",
                         json={"files": [{"document_id": doc, "company_id": company}]}, headers=leader)
    assert r.status_code == 200  # suggestion failures are swallowed...
    # ...but the run records the file as failed instead of reading outside UPLOAD_DIR
    rid = (await client.get(f"{API}?project_id={project_id}", headers=leader)).json()[0]["id"]
    await client.post(f"{API}/{rid}/run", headers=leader)
    await pipeline.run_report(uuid.UUID(rid))
    detail = (await client.get(f"{API}/{rid}", headers=leader)).json()
    assert detail["status"] == "failed" and detail["files"][0]["status"] == "failed"


async def test_publish_warn_mode_records_causes(client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "vr_publish_gate", "warn")
    _, leader, leader_id, project_id, _ = await _world(client, "w")
    rid = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id), await _company(client, leader))
    r = await client.post(f"{API}/{rid}/publish", headers=leader)
    assert r.status_code == 200, r.text
    async with async_session_factory() as db:
        from sqlalchemy import select
        from app.features.volume_report.models import Snapshot
        snap = (await db.execute(select(Snapshot))).scalar_one()
        assert {c["code"] for c in snap.payload["warnings"]["gate"]} >= {"needs_input", "site_kind_unconfirmed"}


async def test_volume_report_disabled_means_no_routes_in_a_fresh_import():
    assert get_settings().volume_report_enabled is False  # default: nothing is mounted unless switched on


async def test_second_run_request_while_processing_is_rejected(client, tmp_path, _env):
    _, leader, leader_id, project_id, _ = await _world(client, "c")
    company = await _company(client, leader)
    doc = await _document(tmp_path, project_id, leader_id)
    report = (await client.post(API, json={"project_id": project_id, "title": "r", "period_type": "week", "period_start": "2026-01-01",
                                           "period_end": "2026-01-07", "period_label": "x"}, headers=leader)).json()
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 400  # no files yet
    await client.put(f"{API}/{report['id']}/files", json={"files": [{"document_id": doc, "company_id": company}]}, headers=leader)
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 202
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 409
    assert _env == [uuid.UUID(report["id"])]  # queued exactly once


async def test_run_and_continue_are_refused_with_429_when_the_users_token_quota_is_used(client, tmp_path):
    admin, leader, leader_id, project_id, _ = await _world(client, "quota")
    doc = await _document(tmp_path, project_id, leader_id)
    company = await _company(client, leader)
    report = (await client.post(API, json={"project_id": project_id, "title": "r", "period_type": "month", "period_start": "2026-08-23",
                                           "period_end": "2026-09-22", "period_label": "شهریور 1405"}, headers=leader)).json()
    await client.put(f"{API}/{report['id']}/files", json={"files": [{"document_id": doc, "company_id": company}]}, headers=leader)
    await client.put(f"/api/v1/admin/users/{leader_id}/token-limit", json={"limit": 50}, headers=admin)
    from app.features.usage.service import record_usage, usage_scope

    with usage_scope(uuid.UUID(leader_id), "chat"):
        await record_usage("m", 50, 0)
    for path in ("run", "continue"):
        refused = await client.post(f"{API}/{report['id']}/{path}", headers=leader)
        assert refused.status_code == 429 and refused.json()["detail"] == "token_quota_exceeded"
    assert (await client.get(f"{API}/{report['id']}/progress", headers=leader)).json()["status"] == "draft"  # not claimed

    await client.post(f"/api/v1/admin/users/{leader_id}/token-limit/reset", headers=admin)
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 202
