"""File manager (folders, move/copy/delete, status actions) of a project's documents. Requires Postgres + Redis."""
import uuid

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.features.documents import service
from app.features.documents.models import Document, DocumentChunk, DocumentStatus


@pytest.fixture(autouse=True)
def _isolated_storage(monkeypatch, tmp_path):
    """Uploads go to a temp dir and no ingestion job reaches the real Redis queue."""
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    queued: list[uuid.UUID] = []
    monkeypatch.setattr(service._queue, "enqueue", lambda _fn, document_id, *a, **kw: queued.append(document_id))
    return queued


@pytest.fixture
def queued(_isolated_storage):
    return _isolated_storage


async def _register(client, email: str) -> tuple[dict, str]:
    response = await client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret"})
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


async def _leader_with_project(client, tag: str) -> tuple[dict, str, str, str]:
    """(leader headers, project id, team id, admin-created second headers)."""
    admin, _ = await _register(client, f"owner-{tag}@example.com")
    leader, leader_id = await _register(client, f"leader-{tag}@example.com")
    team = await client.post("/api/v1/teams", json={"name": f"team-{tag}"}, headers=admin)
    team_id = team.json()["id"]
    await client.post(
        f"/api/v1/teams/{team_id}/members", json={"user_id": leader_id, "role": "leader"}, headers=admin
    )
    project = await client.post(f"/api/v1/teams/{team_id}/projects", json={"name": f"p-{tag}"}, headers=leader)
    return leader, project.json()["id"], team_id, admin


async def _second_project(client, leader, team_id, name) -> str:
    project = await client.post(f"/api/v1/teams/{team_id}/projects", json={"name": name}, headers=leader)
    return project.json()["id"]


async def _folder(client, headers, project_id, name, parent_id=None) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/folders", json={"name": name, "parent_id": parent_id}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _upload(client, headers, project_id, name, content=b"hello", folder_id=None) -> dict:
    data = {"folder_id": folder_id} if folder_id else None
    response = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": (name, content, "text/plain")},
        data=data,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["document"]


async def _listing(client, headers, project_id, folder_id=None) -> dict:
    params = {"folder_id": folder_id} if folder_id else {}
    response = await client.get(f"/api/v1/projects/{project_id}/files", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_folders_nest_and_list_with_breadcrumb(client):
    leader, pid, _, _ = await _leader_with_project(client, "nest")
    a = await _folder(client, leader, pid, "Contracts")
    b = await _folder(client, leader, pid, "2026", a["id"])
    doc = await _upload(client, leader, pid, "deal.txt", folder_id=b["id"])
    assert doc["folder_id"] == b["id"]

    root = await _listing(client, leader, pid)
    assert [f["folder"]["name"] for f in root["folders"]] == ["Contracts"]
    assert root["documents"] == []
    # counts roll up through the tree
    assert root["folders"][0]["status_counts"] == {"processing": 1}

    inner = await _listing(client, leader, pid, b["id"])
    assert [c["name"] for c in inner["breadcrumb"]] == ["Contracts", "2026"]
    assert [d["filename"] for d in inner["documents"]] == ["deal.txt"]


async def test_folder_names_are_unique_per_parent_case_insensitively(client):
    leader, pid, _, _ = await _leader_with_project(client, "uniq")
    a = await _folder(client, leader, pid, "Reports")
    response = await client.post(f"/api/v1/projects/{pid}/folders", json={"name": "reports"}, headers=leader)
    assert response.status_code == 409
    # the same name under another parent is fine
    await _folder(client, leader, pid, "Reports", a["id"])


@pytest.mark.parametrize("bad", ["", "  ", "a/b", "a\\b", "..", "."])
async def test_invalid_folder_names_are_rejected(client, bad):
    leader, pid, _, _ = await _leader_with_project(client, "badname")
    response = await client.post(f"/api/v1/projects/{pid}/folders", json={"name": bad}, headers=leader)
    assert response.status_code == 400


async def test_rename_folder_and_document_and_conflicts(client):
    leader, pid, _, _ = await _leader_with_project(client, "rename")
    await _folder(client, leader, pid, "A")
    b = await _folder(client, leader, pid, "B")
    renamed = await client.patch(f"/api/v1/projects/{pid}/folders/{b['id']}", json={"name": "C"}, headers=leader)
    assert renamed.json()["name"] == "C"
    clash = await client.patch(f"/api/v1/projects/{pid}/folders/{b['id']}", json={"name": "a"}, headers=leader)
    assert clash.status_code == 409

    d1 = await _upload(client, leader, pid, "one.txt", b"1")
    await _upload(client, leader, pid, "two.txt", b"2")
    ok = await client.patch(f"/api/v1/projects/{pid}/documents/{d1['id']}", json={"filename": "uno.txt"}, headers=leader)
    assert ok.json()["filename"] == "uno.txt"
    clash = await client.patch(f"/api/v1/projects/{pid}/documents/{d1['id']}", json={"filename": "TWO.txt"}, headers=leader)
    assert clash.status_code == 409


async def test_same_name_upload_gets_a_numbered_name(client):
    leader, pid, _, _ = await _leader_with_project(client, "dupname")
    first = await _upload(client, leader, pid, "report.txt", b"one")
    second = await _upload(client, leader, pid, "report.txt", b"two")
    third = await _upload(client, leader, pid, "report.txt", b"three")
    assert [first["filename"], second["filename"], third["filename"]] == ["report.txt", "report (1).txt", "report (2).txt"]


async def test_move_changes_location_without_reprocessing(client, db_session, queued):
    leader, pid, _, _ = await _leader_with_project(client, "move")
    src = await _folder(client, leader, pid, "Inbox")
    dst = await _folder(client, leader, pid, "Archive")
    doc = await _upload(client, leader, pid, "a.txt", folder_id=src["id"])
    jobs_before = len(queued)

    response = await client.post(
        f"/api/v1/projects/{pid}/files/move",
        json={"document_ids": [doc["id"]], "target_folder_id": dst["id"]},
        headers=leader,
    )
    assert response.json() == {"count": 1, "skipped": 0}
    assert len(queued) == jobs_before  # no new ingestion job
    moved = await db_session.get(Document, uuid.UUID(doc["id"]))
    await db_session.refresh(moved)
    assert str(moved.folder_id) == dst["id"]
    assert [d["filename"] for d in (await _listing(client, leader, pid, src["id"]))["documents"]] == []


async def test_move_folder_into_its_own_subtree_is_rejected(client):
    leader, pid, _, _ = await _leader_with_project(client, "cycle")
    a = await _folder(client, leader, pid, "A")
    b = await _folder(client, leader, pid, "B", a["id"])
    for target in (a["id"], b["id"]):
        response = await client.post(
            f"/api/v1/projects/{pid}/files/move",
            json={"folder_ids": [a["id"]], "target_folder_id": target},
            headers=leader,
        )
        assert response.status_code == 400


async def test_move_conflict_fails_atomically_or_renames_on_request(client):
    leader, pid, _, _ = await _leader_with_project(client, "conflict")
    dst = await _folder(client, leader, pid, "Dst")
    other = await _folder(client, leader, pid, "Other")
    await _upload(client, leader, pid, "x.txt", b"in-dst", folder_id=dst["id"])
    clash = await _upload(client, leader, pid, "x.txt", b"moving", folder_id=other["id"])
    free = await _upload(client, leader, pid, "y.txt", b"free", folder_id=other["id"])

    refused = await client.post(
        f"/api/v1/projects/{pid}/files/move",
        json={"document_ids": [clash["id"], free["id"]], "target_folder_id": dst["id"]},
        headers=leader,
    )
    assert refused.status_code == 409
    # nothing moved, not even the non-conflicting file
    assert len((await _listing(client, leader, pid, other["id"]))["documents"]) == 2

    renamed = await client.post(
        f"/api/v1/projects/{pid}/files/move",
        json={"document_ids": [clash["id"], free["id"]], "target_folder_id": dst["id"], "on_conflict": "rename"},
        headers=leader,
    )
    assert renamed.json()["count"] == 2
    names = sorted(d["filename"] for d in (await _listing(client, leader, pid, dst["id"]))["documents"])
    assert names == ["x (1).txt", "x.txt", "y.txt"]


async def test_move_into_project_root(client):
    leader, pid, _, _ = await _leader_with_project(client, "toroot")
    f = await _folder(client, leader, pid, "F")
    doc = await _upload(client, leader, pid, "a.txt", folder_id=f["id"])
    response = await client.post(
        f"/api/v1/projects/{pid}/files/move",
        json={"document_ids": [doc["id"]], "target_folder_id": None},
        headers=leader,
    )
    assert response.json()["count"] == 1
    assert [d["filename"] for d in (await _listing(client, leader, pid))["documents"]] == ["a.txt"]


async def test_copy_folder_tree_copies_ready_chunks_without_reprocessing(client, db_session, queued):
    leader, pid, _, _ = await _leader_with_project(client, "copy")
    src = await _folder(client, leader, pid, "Src")
    sub = await _folder(client, leader, pid, "Sub", src["id"])
    ready = await _upload(client, leader, pid, "ready.txt", b"r", folder_id=src["id"])
    nested = await _upload(client, leader, pid, "nested.txt", b"n", folder_id=sub["id"])
    # make `ready` a finished document with one chunk
    settings = get_settings()
    doc = await db_session.get(Document, uuid.UUID(ready["id"]))
    doc.status = DocumentStatus.READY
    doc.embedding_model = settings.embedding_model
    db_session.add(DocumentChunk(document_id=doc.id, content="hi", chunk_index=0, embedding=[0.0] * settings.embedding_dimensions))
    await db_session.commit()
    jobs_before = len(queued)

    response = await client.post(
        f"/api/v1/projects/{pid}/files/copy",
        json={"folder_ids": [src["id"]], "on_conflict": "rename"},  # root target: "Src" exists -> "Src (1)"
        headers=leader,
    )
    assert response.json()["count"] == 2

    root = await _listing(client, leader, pid)
    assert sorted(f["folder"]["name"] for f in root["folders"]) == ["Src", "Src (1)"]
    copy_id = next(f["folder"]["id"] for f in root["folders"] if f["folder"]["name"] == "Src (1)")
    copied = await _listing(client, leader, pid, copy_id)
    copied_ready = next(d for d in copied["documents"] if d["filename"] == "ready.txt")
    assert copied_ready["status"] == "ready"
    chunks = await db_session.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(copied_ready["id"]))
    )
    assert chunks == 1
    # the processing source file is processed again on its own; the ready one is not
    assert len(queued) == jobs_before + 1
    assert [f["folder"]["name"] for f in copied["folders"]] == ["Sub"]
    # originals untouched
    assert (await _listing(client, leader, pid, src["id"]))["documents"][0]["id"] == ready["id"]
    assert nested["id"] != (await _listing(client, leader, pid, copied["folders"][0]["folder"]["id"]))["documents"][0]["id"]


async def test_copy_folder_into_itself_is_rejected(client):
    leader, pid, _, _ = await _leader_with_project(client, "copyself")
    a = await _folder(client, leader, pid, "A")
    response = await client.post(
        f"/api/v1/projects/{pid}/files/copy", json={"folder_ids": [a["id"]], "target_folder_id": a["id"]}, headers=leader
    )
    assert response.status_code == 400


async def test_delete_folder_removes_everything_inside_but_keeps_files_shared_with_other_documents(
    client, db_session, tmp_path
):
    leader, pid, _, _ = await _leader_with_project(client, "delete")
    f = await _folder(client, leader, pid, "Doomed")
    sub = await _folder(client, leader, pid, "Sub", f["id"])
    inside = await _upload(client, leader, pid, "inside.txt", b"same-bytes", folder_id=f["id"])
    deep = await _upload(client, leader, pid, "deep.txt", b"deep", folder_id=sub["id"])
    survivor = await _upload(client, leader, pid, "survivor.txt", b"same-bytes")  # root, same content
    shared_path = (await db_session.get(Document, uuid.UUID(survivor["id"]))).file_path

    response = await client.post(f"/api/v1/projects/{pid}/files/delete", json={"folder_ids": [f["id"]]}, headers=leader)
    assert response.json()["count"] == 2

    assert (await _listing(client, leader, pid))["folders"] == []
    remaining = (await db_session.execute(select(Document.id))).scalars().all()
    assert uuid.UUID(survivor["id"]) in remaining
    assert uuid.UUID(inside["id"]) not in remaining and uuid.UUID(deep["id"]) not in remaining
    # `inside.txt` shared its stored file with `survivor.txt` only if dedup applied; either way survivor's file exists
    from pathlib import Path

    assert Path(shared_path).exists()


async def test_cancel_marks_processing_documents_and_retry_requeues_them(client, db_session, queued):
    leader, pid, _, _ = await _leader_with_project(client, "cancel")
    doc = await _upload(client, leader, pid, "slow.txt")

    cancelled = await client.post(f"/api/v1/projects/{pid}/documents/{doc['id']}/cancel", headers=leader)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    again = await client.post(f"/api/v1/projects/{pid}/documents/{doc['id']}/cancel", headers=leader)
    assert again.status_code == 400  # nothing to cancel any more

    jobs_before = len(queued)
    retried = await client.post(f"/api/v1/projects/{pid}/files/retry", json={"document_ids": [doc["id"]]}, headers=leader)
    assert retried.json() == {"count": 1, "skipped": 0}
    assert len(queued) == jobs_before + 1
    listing = await _listing(client, leader, pid)
    assert listing["documents"][0]["status"] == "processing"


async def test_bulk_cancel_and_retry_skip_documents_in_other_states(client, db_session):
    leader, pid, _, _ = await _leader_with_project(client, "bulk")
    folder = await _folder(client, leader, pid, "Batch")
    docs = [await _upload(client, leader, pid, f"d{i}.txt", f"c{i}".encode(), folder_id=folder["id"]) for i in range(3)]
    ready = await db_session.get(Document, uuid.UUID(docs[0]["id"]))
    ready.status = DocumentStatus.READY
    failed = await db_session.get(Document, uuid.UUID(docs[1]["id"]))
    failed.status = DocumentStatus.FAILED
    await db_session.commit()

    cancel = await client.post(f"/api/v1/projects/{pid}/files/cancel", json={"folder_ids": [folder["id"]]}, headers=leader)
    assert cancel.json() == {"count": 1, "skipped": 2}  # only the processing one
    retry = await client.post(f"/api/v1/projects/{pid}/files/retry", json={"folder_ids": [folder["id"]]}, headers=leader)
    assert retry.json() == {"count": 2, "skipped": 1}  # failed + cancelled; ready is skipped


async def test_unsupported_file_cannot_be_retried_until_its_type_is_supported(client):
    leader, pid, _, _ = await _leader_with_project(client, "unsup")
    doc = await _upload(client, leader, pid, "map.dwg", b"AC1027")
    response = await client.post(f"/api/v1/projects/{pid}/documents/{doc['id']}/retry", headers=leader)
    assert response.status_code == 400
    bulk = await client.post(f"/api/v1/projects/{pid}/files/retry", json={"document_ids": [doc["id"]]}, headers=leader)
    assert bulk.json() == {"count": 0, "skipped": 1}


async def test_search_finds_documents_with_their_folder_path(client):
    leader, pid, _, _ = await _leader_with_project(client, "search")
    a = await _folder(client, leader, pid, "Finance")
    await _upload(client, leader, pid, "Invoice_100%.txt", b"x", folder_id=a["id"])
    await _upload(client, leader, pid, "other.txt", b"y")
    hits = (await client.get(f"/api/v1/projects/{pid}/files/search", params={"q": "invoice_100%"}, headers=leader)).json()
    assert [(h["document"]["filename"], h["path"]) for h in hits] == [("Invoice_100%.txt", ["Finance"])]
    assert (await client.get(f"/api/v1/projects/{pid}/files/search", params={"q": " "}, headers=leader)).status_code == 400


# --- access ---------------------------------------------------------------------------------------------------------


async def test_mutations_need_a_manager_but_listing_needs_only_project_access(client):
    leader, pid, team_id, admin = await _leader_with_project(client, "acl")
    member, member_id = await _register(client, "member-acl@example.com")
    outsider, _ = await _register(client, "outsider-acl@example.com")
    await client.post(f"/api/v1/teams/{team_id}/members", json={"user_id": member_id, "role": "member"}, headers=admin)
    await client.post(f"/api/v1/projects/{pid}/members", json={"user_id": member_id}, headers=leader)
    folder = await _folder(client, leader, pid, "Shared")

    assert (await client.get(f"/api/v1/projects/{pid}/files", headers=member)).status_code == 200
    assert (await client.get(f"/api/v1/projects/{pid}/files", headers=outsider)).status_code == 403

    mutations = [
        ("post", f"/api/v1/projects/{pid}/folders", {"name": "x"}),
        ("patch", f"/api/v1/projects/{pid}/folders/{folder['id']}", {"name": "y"}),
        ("post", f"/api/v1/projects/{pid}/files/move", {"folder_ids": [folder["id"]]}),
        ("post", f"/api/v1/projects/{pid}/files/copy", {"folder_ids": [folder["id"]]}),
        ("post", f"/api/v1/projects/{pid}/files/delete", {"folder_ids": [folder["id"]]}),
        ("post", f"/api/v1/projects/{pid}/files/retry", {"folder_ids": [folder["id"]]}),
        ("post", f"/api/v1/projects/{pid}/files/cancel", {"folder_ids": [folder["id"]]}),
    ]
    for who in (member, outsider):
        for method, url, body in mutations:
            response = await getattr(client, method)(url, json=body, headers=who)
            assert response.status_code == 403, (method, url, response.status_code)
    assert [f["folder"]["name"] for f in (await _listing(client, leader, pid))["folders"]] == ["Shared"]


async def test_items_of_another_project_are_not_found(client):
    leader, pid, team_id, _ = await _leader_with_project(client, "mine")
    other_leader, other_pid = leader, await _second_project(client, leader, team_id, "theirs")
    foreign_folder = await _folder(client, other_leader, other_pid, "Secret")
    foreign_doc = await _upload(client, other_leader, other_pid, "secret.txt")

    assert (await client.get(f"/api/v1/projects/{pid}/files", params={"folder_id": foreign_folder["id"]}, headers=leader)).status_code == 404
    assert (await client.post(f"/api/v1/projects/{pid}/folders", json={"name": "x", "parent_id": foreign_folder["id"]}, headers=leader)).status_code == 404
    for action in ("move", "copy", "delete", "retry", "cancel"):
        for body in ({"folder_ids": [foreign_folder["id"]]}, {"document_ids": [foreign_doc["id"]]}):
            response = await client.post(f"/api/v1/projects/{pid}/files/{action}", json=body, headers=leader)
            assert response.status_code == 404, (action, body)
    moved_into_foreign = await client.post(
        f"/api/v1/projects/{pid}/files/move",
        json={"document_ids": [], "folder_ids": [], "target_folder_id": foreign_folder["id"]},
        headers=leader,
    )
    assert moved_into_foreign.status_code in (400, 404)
    assert (await client.patch(f"/api/v1/projects/{pid}/documents/{foreign_doc['id']}", json={"filename": "z.txt"}, headers=leader)).status_code == 404
    assert (await client.post(f"/api/v1/projects/{pid}/documents/{foreign_doc['id']}/cancel", headers=leader)).status_code == 400
    # the other project is untouched
    assert len((await _listing(client, other_leader, other_pid))["documents"]) == 1


async def test_upload_into_a_foreign_or_unknown_folder_is_not_found(client):
    leader, pid, team_id, _ = await _leader_with_project(client, "upl")
    foreign = await _folder(client, leader, await _second_project(client, leader, team_id, "other"), "x")
    response = await client.post(
        f"/api/v1/projects/{pid}/documents",
        files={"file": ("a.txt", b"a", "text/plain")},
        data={"folder_id": foreign["id"]},
        headers=leader,
    )
    assert response.status_code == 404
    batch = await client.post(
        f"/api/v1/projects/{pid}/documents/batch",
        files=[("files", ("a.txt", b"a", "text/plain"))],
        data={"folder_id": str(uuid.uuid4())},
        headers=leader,
    )
    assert batch.status_code == 404
