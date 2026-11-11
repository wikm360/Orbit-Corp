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
    again = await client.post(f"{API}/{rid}/reopen", headers=leader)
    assert again.status_code == 201 and again.json()["version"] == 2 and again.json()["supersedes_id"] == rid
    assert (await client.post(f"{API}/{rid}/reopen", headers=leader)).status_code == 409
    # a published report can be deleted entirely; the reopened version survives with supersedes_id cleared
    assert (await client.delete(f"{API}/{rid}", headers=leader)).status_code == 204
    assert (await client.get(f"{API}/{rid}", headers=leader)).status_code == 404
    assert (await client.get(f"{API}/{again.json()['id']}", headers=leader)).json()["supersedes_id"] is None


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
    rule = {"item_key": "concrete", "name": "آبرو دالی", "phrases": ["آبرو  دالی", "آبرو دالی"], "source_unit": "m2", "factor": 2}
    assert (await client.post(f"{API}/settings/item-rules", json=rule, headers=outsider)).status_code == 403
    r_res = await client.post(f"{API}/settings/item-rules", json=rule, headers=leader)
    assert r_res.status_code == 201 and r_res.json()["phrases"] == ["آبرو دالی"] and r_res.json()["factor"] == "2.000000"
    rule_id = r_res.json()["id"]
    assert (await client.post(f"{API}/settings/item-rules", json={**rule, "item_key": "nope"}, headers=leader)).status_code == 404
    assert (await client.put(f"{API}/settings/item-rules/{rule_id}", json={**rule, "factor": 3}, headers=leader)).json()["factor"] == "3.000000"
    assert len((await client.get(f"{API}/settings/item-rules", headers=leader)).json()) == 1
    assert (await client.delete(f"{API}/settings/item-rules/{rule_id}", headers=outsider)).status_code == 403
    assert (await client.delete(f"{API}/settings/item-rules/{rule_id}", headers=leader)).status_code == 204
    assert (await client.delete(f"{API}/settings/item-rules/{rule_id}", headers=leader)).status_code == 404
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


async def _two_sheet_document(tmp_path, project_id, uploader_id, actual_qty, plan_qty=None):
    wb = Workbook()
    add_income_sheet(wb, "درآمد", [(None, "بتن ریزی پی", "متر مکعب", actual_qty)], title=TITLE)
    if plan_qty is not None:
        add_income_sheet(wb, "درآمد برنامه ای", [(None, "بتن ریزی پی", "متر مکعب", plan_qty)], title=TITLE)
    path = save(wb, tmp_path, f"{uuid.uuid4().hex}.xlsx")
    async with async_session_factory() as db:
        doc = Document(filename="w.xlsx", file_path=path, content_type="application/octet-stream", status=DocumentStatus.READY,
                       content_hash=uuid.uuid4().hex + uuid.uuid4().hex, project_id=uuid.UUID(project_id), uploaded_by=uuid.UUID(uploader_id))
        db.add(doc)
        await db.commit()
        return str(doc.id)


async def _weekly_report(client, headers, project_id, doc_id, company_id, start, end):
    report = (await client.post(API, json={"project_id": project_id, "title": "w", "period_type": "week", "period_start": start,
                                           "period_end": end, "period_label": "هفته"}, headers=headers)).json()
    assert (await client.put(f"{API}/{report['id']}/files", json={"files": [{"document_id": doc_id, "company_id": company_id}]}, headers=headers)).status_code == 200
    assert (await client.post(f"{API}/{report['id']}/run", headers=headers)).status_code == 202
    await pipeline.run_report(uuid.UUID(report["id"]))
    return report["id"]


async def test_forecast_sheet_is_stored_separately_and_compared_with_next_reports_actuals(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "plan")
    company = await _company(client, leader)
    first = await _weekly_report(client, leader, project_id, await _two_sheet_document(tmp_path, project_id, leader_id, 25, 40), company, "2026-11-01", "2026-11-07")
    g = await _groups(client, leader, first)
    assert g["بتن ریزی پی"]["total_quantity"] == "25" or Decimal(g["بتن ریزی پی"]["total_quantity"]) == 25
    assert Decimal(g["بتن ریزی پی"]["planned_quantity"]) == 40 and g["بتن ریزی پی"]["n_lines"] == 2  # one group, two bases
    r = await client.post(f"{API}/{first}/review/confirm", json={"items": [_confirm(g["بتن ریزی پی"], "concrete")]}, headers=leader)
    assert r.status_code == 200, r.text

    actual = {x["item_key"]: Decimal(x["qty"]) for x in (await client.get(f"{API}/{first}/results?group_by=holding", headers=leader)).json()["rows"]}
    plan = {x["item_key"]: Decimal(x["qty"]) for x in (await client.get(f"{API}/{first}/results?group_by=holding&basis=planned", headers=leader)).json()["rows"]}
    assert actual["concrete"] == 25 and plan["concrete"] == 40  # the forecast never leaks into the actual total
    assert (await client.get(f"{API}/{first}/plan-vs-actual", headers=leader)).json()["previous_report"] is None

    second = await _weekly_report(client, leader, project_id, await _two_sheet_document(tmp_path, project_id, leader_id, 30), company, "2026-11-08", "2026-11-14")
    cmp = (await client.get(f"{API}/{second}/plan-vs-actual?group_by=holding", headers=leader)).json()
    assert cmp["previous_report"]["id"] == first and cmp["previous_report"]["adjacent"] is True
    row = next(x for x in cmp["rows"] if x["item_key"] == "concrete")
    assert Decimal(row["planned"]) == 40 and Decimal(row["actual"]) == 30 and Decimal(row["variance"]) == -10 and Decimal(row["achievement_pct"]) == Decimal("75.0")


async def test_other_is_remembered_across_reports_and_removed_rows_stay_visible(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "other")
    company = await _company(client, leader)
    rows = [(None, "بتن ریزی پی", "متر مکعب", 25), (None, "کارهای متفرقه خاص", "متر مکعب", 7)]
    first = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, rows=rows), company)
    g = await _groups(client, leader, first)
    # «سایر» with the default (global) memory; same call shape the UI now sends
    body = {"items": [_confirm(g["بتن ریزی پی"], "concrete"),
                      {"group_key": g["کارهای متفرقه خاص"]["group_key"], "disposition": "unmatched", "role": "na", "remember_scope": "global"}]}
    assert (await client.post(f"{API}/{first}/review/confirm", json=body, headers=leader)).status_code == 200
    other = (await client.get(f"{API}/{first}/results?group_by=holding&include=other", headers=leader)).json()["other"]
    assert [o["description"] for o in other] == ["کارهای متفرقه خاص"]

    second = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id, rows=rows, name="b.xlsx"), company)
    g2 = await _groups(client, leader, second)
    assert g2["کارهای متفرقه خاص"]["disposition"] == "unmatched" and g2["کارهای متفرقه خاص"]["confirmed"]
    assert g2["کارهای متفرقه خاص"]["reason"] == "memory_exact"

    # a legacy "excluded" row is never hidden: it is listed with the other rows
    legacy = {"items": [{"group_key": g2["کارهای متفرقه خاص"]["group_key"], "exclude_reason": "other", "role": "na", "remember_scope": "line"}]}
    assert (await client.post(f"{API}/{second}/review/confirm", json=legacy, headers=leader)).status_code == 200
    other2 = (await client.get(f"{API}/{second}/results?group_by=holding&include=other", headers=leader)).json()["other"]
    assert [(o["description"], o["effect"]) for o in other2] == [("کارهای متفرقه خاص", "excluded")]


async def test_narratives_crud_and_generate(client, tmp_path, monkeypatch):
    _, leader, leader_id, project_id, _ = await _world(client, "narratives")
    company = await _company(client, leader)
    report_id = await _new_report(client, leader, project_id, await _document(tmp_path, project_id, leader_id), company)

    # 1. GET narratives initially empty
    res = await client.get(f"{API}/{report_id}/narratives", headers=leader)
    assert res.status_code == 200
    assert res.json() == {}

    # 2. PUT narratives
    payload = {
        "narratives": {
            company: {
                "company_name": "شرکت محور گستر نصر",
                "raw_text": "پروژه زاهدان خاش لایه اساس تموم شد",
                "items": ["پروژه زاهدان خاش ۱۵۰۰ متر طول در مرحله اتمام لایه اساس"],
            }
        }
    }
    put_res = await client.put(f"{API}/{report_id}/narratives", json=payload, headers=leader)
    assert put_res.status_code == 200
    assert company in put_res.json()
    assert put_res.json()[company]["items"] == ["پروژه زاهدان خاش ۱۵۰۰ متر طول در مرحله اتمام لایه اساس"]

    # 3. GET report detail contains narratives
    detail_res = await client.get(f"{API}/{report_id}", headers=leader)
    assert detail_res.status_code == 200
    assert detail_res.json()["narratives"][company]["items"] == ["پروژه زاهدان خاش ۱۵۰۰ متر طول در مرحله اتمام لایه اساس"]

    # 4. POST generate narrative with mocked provider
    class _StubProvider:
        async def complete(self, messages, *args, **kwargs):
            return {
                "content": "پروژه زاهدان خاش در مرحله اتمام لایه اساس\n\nاخذ اسناد مناقصه گردنه خرمافروشان",
                "tool_calls": [],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            }

    from app.providers import llm_provider
    monkeypatch.setattr(llm_provider, "get_vr_llm_provider", lambda: _StubProvider())

    gen_res = await client.post(
        f"{API}/{report_id}/narratives/generate",
        json={"company_id": company, "company_name": "شرکت جهاد نصر سیستان", "raw_text": "زاهدان خاش لایه اساس تمام شد"},
        headers=leader,
    )
    assert gen_res.status_code == 200
    data = gen_res.json()
    assert len(data["items"]) == 2
    assert "پروژه زاهدان خاش" in data["items"][0]


async def _evm_document(tmp_path, project_id, uploader_id, rows, title="گزارش مدیریت ارزش کسب شده (EVM)"):
    wb = Workbook()
    ws = wb.active
    ws.title = "EVM"
    ws.append(["شرکت نمونه"])
    ws.append([title])
    ws.append(["ردیف", "نام پروژه", "مبلغ قرارداد (ریال)", "M-BCWS", "PV", "EV", "ev", "AC", "CPI=ev/AC", "SPI=EV/PV"])
    for row in rows:
        ws.append(row)
    path = save(wb, tmp_path, f"{uuid.uuid4().hex}.xlsx")
    async with async_session_factory() as db:
        doc = Document(filename="evm.xlsx", file_path=path, content_type="application/octet-stream", status=DocumentStatus.READY,
                       content_hash=uuid.uuid4().hex + uuid.uuid4().hex, project_id=uuid.UUID(project_id), uploaded_by=uuid.UUID(uploader_id))
        db.add(doc)
        await db.commit()
        return str(doc.id)


async def _evm_report(client, leader, project_id, docs, start, end):
    report = (await client.post(API, json={"project_id": project_id, "title": "e", "period_type": "week", "period_start": start,
                                           "period_end": end, "period_label": "هفته"}, headers=leader)).json()
    r = await client.put(f"{API}/{report['id']}/files", json={"files": docs}, headers=leader)
    assert r.status_code == 200, r.text
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 202
    await pipeline.run_report(uuid.UUID(report["id"]))
    return report["id"]


async def _evm(client, leader, rid):
    return (await client.get(f"{API}/{rid}/evm", headers=leader)).json()


def _project(data, company, name):
    c = next(x for x in data["actual"]["companies"] if x["company"] == company)
    return c, next(p for p in c["projects"] if p["project"] == name)


B = 10**9


async def test_evm_is_read_per_project_company_and_holding_without_any_forecast_section(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "evm")
    alef, be = await _company(client, leader, "شرکت الف"), await _company(client, leader, "شرکت ب")
    docs = [
        await _evm_document(tmp_path, project_id, leader_id, [
            [1, "پروژه الف", 1_000 * B, 100e9, 100e9, 80e9, 60e9, 50e9, 1.2, 0.8], [2, "پروژه ب", 500 * B, 50e9, 50e9, 20e9, 15e9, 30e9, 0.5, 0.4],
            ["جمع", None, None, 150e9, 150e9, 100e9, 75e9, 80e9, 0.94, 0.67]]),
        await _evm_document(tmp_path, project_id, leader_id, [[1, "پروژه ج", 9_000 * B, 10e9, 10e9, 10e9, 8e9, 4e9, 2.0, 1.0]]),
    ]
    rid = await _evm_report(client, leader, project_id, [{"document_id": docs[0], "company_id": alef}, {"document_id": docs[1], "company_id": be}],
                            "2026-11-02", "2026-11-08")
    data = await _evm(client, leader, rid)
    assert set(data) == {"report_id", "pv_mode", "actual"}  # no forecast EVM is reported
    a, first = _project(data, "شرکت الف", "پروژه الف")
    assert Decimal(first["pv"]) == 100 * B and first["pv_source"] == "file" and first["cpi"] == "1.20" and first["spi"] == "0.80"
    assert Decimal(a["total"]["ev"]) == 100 * B and a["total"]["cpi"] == "0.94" and a["total"]["spi"] == "0.67"  # ratios of sums
    assert a["reported_total"]["spi"] == "0.67"
    assert Decimal(data["actual"]["holding"]["ev"]) == 110 * B and Decimal(data["actual"]["holding"]["ac"]) == 84 * B
    # re-running replaces (never duplicates) the rows; a non-member is refused
    assert (await client.post(f"{API}/{rid}/run", headers=leader)).status_code == 202
    await pipeline.run_report(uuid.UUID(rid))
    again = await _evm(client, leader, rid)
    assert sum(len(c["projects"]) for c in again["actual"]["companies"]) == 3
    outsider, _ = await _register(client, "evm-outsider@example.com")
    assert (await client.get(f"{API}/{rid}/evm", headers=outsider)).status_code == 403


async def test_pv_comes_from_the_forecast_of_the_same_period_and_never_from_the_next_one(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "pv-forecast")
    company = await _company(client, leader)
    row = lambda ev: [[1, "پروژه الف", 1_000 * B, 100e9, 100e9, 80e9, 60e9, 50e9, 1.2, 0.8]] if ev is None else [[1, "پروژه الف", 1_000 * B, 100e9, 100e9, ev, ev * 0.75, 50e9, 1.2, 1.0]]  # noqa: E731
    actual = await _evm_document(tmp_path, project_id, leader_id, row(None), title="گزارش مدیریت ارزش کسب شده (EVM) (11 - 17 آبان ماه)")
    same = await _evm_document(tmp_path, project_id, leader_id, row(200e9), title="پیش بینی گزارش مدیریت ارزش کسب شده (EVM) (11 - 17 آبان ماه)")
    nxt = await _evm_document(tmp_path, project_id, leader_id, row(999e9), title="پیش بینی گزارش مدیریت ارزش کسب شده (EVM) (18 - 24 آبان ماه)")
    docs = [{"document_id": d, "company_id": company} for d in (actual, same, nxt)]
    rid = await _evm_report(client, leader, project_id, docs, "2026-11-02", "2026-11-08")  # Aban 11..17
    _, project = _project(await _evm(client, leader, rid), "محورگستر", "پروژه الف")
    assert Decimal(project["pv"]) == 200 * B and project["pv_source"] == "forecast_file"  # the EV of the forecast, not the 999 of next week
    assert Decimal(project["ev"]) == 80 * B and project["spi"] == "0.40" and project["cpi"] == "1.20"  # EV / AC / CPI stay the file's own


async def test_pv_falls_back_to_the_previous_reports_forecast(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "pv-prev")
    company = await _company(client, leader)
    first_actual = await _evm_document(tmp_path, project_id, leader_id, [[1, "پروژه الف", 1_000 * B, 100e9, 100e9, 80e9, 60e9, 50e9, 1.2, 0.8]],
                                       title="گزارش مدیریت ارزش کسب شده (EVM) (11 - 17 آبان ماه)")
    forecast = await _evm_document(tmp_path, project_id, leader_id, [[1, "پروژه الف", 1_000 * B, 100e9, 100e9, 160e9, 120e9, 50e9, 1.2, 1.0]],
                                   title="پیش بینی گزارش مدیریت ارزش کسب شده (EVM) (18 - 24 آبان ماه)")
    await _evm_report(client, leader, project_id, [{"document_id": d, "company_id": company} for d in (first_actual, forecast)], "2026-11-02", "2026-11-08")
    second_actual = await _evm_document(tmp_path, project_id, leader_id, [[1, "پروژه الف", 1_000 * B, 100e9, 100e9, 120e9, 90e9, 60e9, 1.5, 0.75]],
                                        title="گزارش مدیریت ارزش کسب شده (EVM) (18 - 24 آبان ماه)")
    rid2 = await _evm_report(client, leader, project_id, [{"document_id": second_actual, "company_id": company}], "2026-11-09", "2026-11-15")
    _, project = _project(await _evm(client, leader, rid2), "محورگستر", "پروژه الف")
    assert Decimal(project["pv"]) == 160 * B and project["pv_source"] == "previous_report" and project["spi"] == "0.75"  # 120 / 160


async def _pv_plan_document(tmp_path, project_id, uploader_id, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "PVF"
    ws.append(["شرکت نمونه"])
    ws.append(["درآمد برنامه ای پروژه های شرکت نمونه در ماه آبان"])
    ws.append(["ردیف", "نام پروژه", "مبلغ قرارداد", "کارکرد ماهانه طبق برنامه‌ی کارگاه(PV) (ریال)", "PV ماه پیش"])
    for index, (name, pv) in enumerate(rows, start=1):
        ws.append([index, name, 1_000 * B, pv, 5e9])
    path = save(wb, tmp_path, f"{uuid.uuid4().hex}.xlsx")
    async with async_session_factory() as db:
        doc = Document(filename="pv.xlsx", file_path=path, content_type="application/octet-stream", status=DocumentStatus.READY,
                       content_hash=uuid.uuid4().hex + uuid.uuid4().hex, project_id=uuid.UUID(project_id), uploaded_by=uuid.UUID(uploader_id))
        db.add(doc)
        await db.commit()
        return str(doc.id)


async def test_monthly_pv_plan_gives_the_days_share_of_the_month(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "pv-month")
    company = await _company(client, leader)
    actual = await _evm_document(tmp_path, project_id, leader_id, [[1, "احداث باند دوم محور زرند - سیریز", 1_000 * B, None, None, 80e9, 60e9, 50e9, 1.2, 0.0],
                                                                   [2, "پروژه کاملاً جدا", 5 * B, 1e9, 1e9, 1e9, 1e9, 1e9, 1.0, 1.0]])
    plan = await _pv_plan_document(tmp_path, project_id, leader_id, [("احداث باند دوم محور زرند-بافق", 300e9), ("پروژه دیگر", 7e9)])
    # the PV file is recognised by its content: kind and month are suggested, nothing else is needed
    report = (await client.post(API, json={"project_id": project_id, "title": "pv", "period_type": "week", "period_start": "2026-11-02",
                                           "period_end": "2026-11-08", "period_label": "هفته"}, headers=leader)).json()
    files = (await client.put(f"{API}/{report['id']}/files", json={"files": [
        {"document_id": actual, "company_id": company}, {"document_id": plan, "company_id": company, "kind": "monthly_pv"}]}, headers=leader)).json()
    pv_file = next(f for f in files if f["kind"] == "monthly_pv")
    assert pv_file["suggested_kind"] == "monthly_pv" and pv_file["suggested_plan_month"] == 8
    assert pv_file["plan"]["overlap_days"] == 7 and pv_file["plan"]["plan_days"] == 30  # the report's OWN week, not the next one
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 202
    await pipeline.run_report(uuid.UUID(report["id"]))
    data = await _evm(client, leader, report["id"])
    _, project = _project(data, "محورگستر", "احداث باند دوم محور زرند - سیریز")
    assert Decimal(project["pv"]) == Decimal(300 * B) * 7 / 30 and project["pv_source"] == "monthly_pv" and project["pv_match"] == "fuzzy"
    assert project["spi"] == "1.14" and project["pv_share"] == "7/30"  # EV 80B / PV 70B
    _, other = _project(data, "محورگستر", "پروژه کاملاً جدا")
    assert other["pv_source"] == "file"  # nothing in the plan matches it: the file's own PV stays



async def _monthly_report(client, leader, project_id, company, docs, start, end):
    report = (await client.post(API, json={"project_id": project_id, "title": "m", "period_type": "week", "period_start": start,
                                           "period_end": end, "period_label": "هفته"}, headers=leader)).json()
    r = await client.put(f"{API}/{report['id']}/files", json={"files": docs}, headers=leader)
    assert r.status_code == 200, r.text
    assert (await client.post(f"{API}/{report['id']}/run", headers=leader)).status_code == 202
    await pipeline.run_report(uuid.UUID(report["id"]))
    return report["id"], r.json()


async def _planned_concrete(client, headers, rid):
    g = await _groups(client, headers, rid)
    await client.post(f"{API}/{rid}/review/confirm", json={"items": [_confirm(g["بتن ریزی پی"], "concrete")]}, headers=headers)
    rows = (await client.get(f"{API}/{rid}/results?group_by=holding&basis=planned", headers=headers)).json()["rows"]
    return {x["item_key"]: Decimal(x["qty"]) for x in rows}


async def test_monthly_forecast_is_spread_over_the_days_of_the_next_period(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "monthly")
    company = await _company(client, leader)
    title = "گزارش درآمد پروژه سیرجان قطروئیه در ماه پیش بینی آبان"
    monthly = await _document(tmp_path, project_id, leader_id, rows=[(None, "بتن ریزی پی", "متر مکعب", 300)], name="m.xlsx", title=title)
    actual = await _document(tmp_path, project_id, leader_id, rows=[(None, "بتن ریزی پی", "متر مکعب", 40)], name="a.xlsx")
    docs = [{"document_id": actual, "company_id": company}, {"document_id": monthly, "company_id": company, "kind": "monthly_plan"}]

    # Aban 1405 = 2026-10-23 .. 2026-11-21 (30 days). Next period 11-08..11-14 lies fully inside: 7/30 of the month.
    rid, files = await _monthly_report(client, leader, project_id, company, docs, "2026-11-01", "2026-11-07")
    mf = next(f for f in files if f["kind"] == "monthly_plan")
    assert mf["suggested_plan_month"] == 8 and mf["plan_start"] == "2026-10-23" and mf["plan_end"] == "2026-11-21"
    assert mf["plan"]["overlap_days"] == 7 and mf["plan"]["plan_days"] == 30
    plan = await _planned_concrete(client, leader, rid)
    assert plan["concrete"] == Decimal("70")  # 300 x 7 / 30; the actual file's 40 never leaks into the forecast
    actual_rows = {x["item_key"]: Decimal(x["qty"]) for x in (await client.get(f"{API}/{rid}/results?group_by=holding", headers=leader)).json()["rows"]}
    assert actual_rows["concrete"] == 40
    src = (await client.get(f"{API}/{rid}/sources", headers=leader)).json()
    assert next(x for x in src if x["kind"] == "monthly_plan")["plan"]["factor"] == "0.233333"

    # a week that straddles the end of the month only gets the days that are inside it (Nov 19, 20, 21)
    rid2, _ = await _monthly_report(client, leader, project_id, company, [{**d, "document_id": d["document_id"]} for d in docs], "2026-11-12", "2026-11-18")
    assert (await _planned_concrete(client, leader, rid2))["concrete"] == Decimal("30")  # 300 x 3 / 30

    # a period outside the month contributes nothing
    rid3, _ = await _monthly_report(client, leader, project_id, company, docs, "2026-11-15", "2026-11-21")
    assert (await _planned_concrete(client, leader, rid3)).get("concrete", Decimal(0)) == 0


async def test_site_with_its_own_forecast_ignores_the_monthly_one(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "monthly2")
    company = await _company(client, leader)
    title = "گزارش درآمد پروژه سیرجان قطروئیه در ماه پیش بینی آبان"
    monthly = await _document(tmp_path, project_id, leader_id, rows=[(None, "بتن ریزی پی", "متر مکعب", 300)], name="m.xlsx", title=title)
    weekly = await _two_sheet_document(tmp_path, project_id, leader_id, 25, 12)  # forecast sheet of its own: 12
    docs = [{"document_id": weekly, "company_id": company}, {"document_id": monthly, "company_id": company, "kind": "monthly_plan"}]
    rid, _ = await _monthly_report(client, leader, project_id, company, docs, "2026-11-01", "2026-11-07")
    assert (await _planned_concrete(client, leader, rid))["concrete"] == Decimal("12")  # never 12 + 70


async def test_monthly_forecast_needs_a_month(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "monthly3")
    company = await _company(client, leader)
    plain = await _document(tmp_path, project_id, leader_id, name="p.xlsx")  # title names no forecast month
    report = (await client.post(API, json={"project_id": project_id, "title": "m", "period_type": "week", "period_start": "2026-11-01",
                                           "period_end": "2026-11-07", "period_label": "هفته"}, headers=leader)).json()
    body = {"files": [{"document_id": plain, "company_id": company, "kind": "monthly_plan"}]}
    assert (await client.put(f"{API}/{report['id']}/files", json=body, headers=leader)).status_code == 400
    body["files"][0]["plan_month"] = 8
    ok = await client.put(f"{API}/{report['id']}/files", json=body, headers=leader)
    assert ok.status_code == 200 and ok.json()[0]["plan_start"] == "2026-10-23"


_ZARAND = "eval/volume_report/second-aban/گزارش درآمد و هزینه هفتگی از 11 آبان الی 17 آبان پروژه زرند-سیریز.pdf"
_TOTAL_EVM = "eval/Total EVM Rep-MGSH SHAHRIVAR V4.xls"


@pytest.mark.skipif(not (__import__("pathlib").Path(_ZARAND).exists() and __import__("pathlib").Path(_TOTAL_EVM).exists()), reason="samples not present")
async def test_real_zarand_week_takes_its_pv_from_the_pvf_sheet_of_the_company_workbook(client, tmp_path):
    import shutil

    _, leader, leader_id, project_id, _ = await _world(client, "pv-real")
    company = await _company(client, leader)
    ids = []
    for source, suffix in ((_ZARAND, ".pdf"), (_TOTAL_EVM, ".xls")):
        path = tmp_path / f"{uuid.uuid4().hex}{suffix}"
        shutil.copy(source, path)
        async with async_session_factory() as db:
            doc = Document(filename=path.name, file_path=str(path), content_type="application/octet-stream", status=DocumentStatus.READY,
                           content_hash=uuid.uuid4().hex + uuid.uuid4().hex, project_id=uuid.UUID(project_id), uploaded_by=uuid.UUID(leader_id))
            db.add(doc)
            await db.commit()
            ids.append(str(doc.id))
    rid = await _evm_report(client, leader, project_id, [{"document_id": ids[0], "company_id": company},
                                                        {"document_id": ids[1], "company_id": company, "kind": "monthly_pv"}], "2026-11-02", "2026-11-08")  # 11-17 Aban
    c = (await _evm(client, leader, rid))["actual"]["companies"][0]
    project = c["projects"][0]
    assert project["pv_source"] == "monthly_pv" and project["pv_match"] == "fuzzy" and project["pv_share"] == "7/30"
    assert Decimal(project["pv"]) == (Decimal("1104392021869.88") * 7 / 30).quantize(Decimal("0.01"))  # PVF "زرند-بافق", Aban
    assert Decimal(project["ev"]) == Decimal("182553272695") and project["cpi"] == "1.36"  # EV / ev / AC / CPI: the project's own file
    assert project["spi"] == "0.71"


async def test_manual_pv_mode_uses_the_typed_values_and_blank_means_the_files_own_pv(client, tmp_path):
    _, leader, leader_id, project_id, _ = await _world(client, "pv-manual")
    company = await _company(client, leader)
    actual = await _evm_document(tmp_path, project_id, leader_id, [
        [1, "احداث باند دوم محور زرند - سیریز", 1_000 * B, 90e9, 90e9, 80e9, 60e9, 50e9, 1.2, 0.89],
        [2, "پروژه دوم", 500 * B, 40e9, 40e9, 20e9, 15e9, 30e9, 0.5, 0.5]])
    plan = await _pv_plan_document(tmp_path, project_id, leader_id, [("احداث باند دوم محور زرند-بافق", 300e9)])
    rid = await _evm_report(client, leader, project_id, [{"document_id": actual, "company_id": company},
                                                        {"document_id": plan, "company_id": company, "kind": "monthly_pv"}], "2026-11-02", "2026-11-08")
    data = await _evm(client, leader, rid)
    assert data["pv_mode"] == "auto"
    _, first = _project(data, "محورگستر", "احداث باند دوم محور زرند - سیریز")
    assert Decimal(first["pv"]) == 70 * B and first["pv_source"] == "monthly_pv"

    # manual mode: the typed value wins, the automatic one stays as the suggestion, a blank project keeps the file's PV
    body = {"mode": "manual", "values": [{"company_id": company, "project": "احداث باند دوم محور زرند - سیریز", "pv": "100000000000"}]}
    done = await client.put(f"{API}/{rid}/evm/pv", json=body, headers=leader)
    assert done.status_code == 200, done.text
    c, first = _project(done.json(), "محورگستر", "احداث باند دوم محور زرند - سیریز")
    assert done.json()["pv_mode"] == "manual" and Decimal(first["pv"]) == 100 * B and first["pv_source"] == "manual" and first["spi"] == "0.80"
    assert Decimal(first["pv_auto"]) == 70 * B and Decimal(first["pv_manual"]) == 100 * B
    _, second = _project(done.json(), "محورگستر", "پروژه دوم")
    assert Decimal(second["pv"]) == 40 * B and second["pv_source"] == "file"
    assert c["total"]["spi"] == "0.71"  # (80 + 20) / (100 + 40)

    # back to auto: the typed values are kept for later but ignored
    back = (await client.put(f"{API}/{rid}/evm/pv", json={"mode": "auto", "values": body["values"]}, headers=leader)).json()
    assert Decimal(_project(back, "محورگستر", "احداث باند دوم محور زرند - سیریز")[1]["pv"]) == 70 * B
    # invalid values and a published/foreign report are refused
    bad = await client.put(f"{API}/{rid}/evm/pv", json={"mode": "manual", "values": [{"company_id": company, "project": "x", "pv": "-5"}]}, headers=leader)
    assert bad.status_code == 422
    outsider, _ = await _register(client, "pv-outsider@example.com")
    assert (await client.put(f"{API}/{rid}/evm/pv", json=body, headers=outsider)).status_code == 403
