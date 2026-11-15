import uuid

from app.core.config import get_settings
from app.features.documents.models import Document, DocumentChunk, DocumentStatus


async def _register(client, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    body = response.json()
    return body["access_token"], body["user"]["id"]


async def _setup_leader_with_project(client, suffix: str) -> tuple[dict, str, str]:
    """First registered user becomes super_admin and creates the team+leader;
    the leader then creates their own project."""
    admin_token, _ = await _register(client, f"owner-{suffix}@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    leader_token, leader_id = await _register(client, f"leader-{suffix}@example.com")
    leader_headers = {"Authorization": f"Bearer {leader_token}"}

    team = await client.post(
        "/api/v1/teams", json={"name": f"team-{suffix}"}, headers=admin_headers
    )
    team_id = team.json()["id"]

    await client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": leader_id, "role": "leader"},
        headers=admin_headers,
    )

    project = await client.post(
        f"/api/v1/teams/{team_id}/projects",
        json={"name": f"project-{suffix}"},
        headers=leader_headers,
    )
    return leader_headers, project.json()["id"], team_id


async def test_upload_document_forbidden_for_non_manager(client):
    admin_token, _ = await _register(client, "owner-perm@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    outsider_token, _ = await _register(client, "outsider-perm@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    team = await client.post("/api/v1/teams", json={"name": "team-perm"}, headers=admin_headers)
    project = await client.post(
        f"/api/v1/teams/{team.json()['id']}/projects",
        json={"name": "project-perm"},
        headers=admin_headers,
    )

    response = await client.post(
        f"/api/v1/projects/{project.json()['id']}/documents",
        files={"file": ("note.txt", b"hello world", "text/plain")},
        headers=outsider_headers,
    )
    assert response.status_code == 403


async def test_upload_keeps_unsupported_extension_as_unsupported(client):
    """The file manager stores a file it cannot parse (it stays visible and can be processed once supported)."""
    leader_headers, project_id, _ = await _setup_leader_with_project(client, "ext")

    response = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("drawing.dwg", b"binarydata", "application/octet-stream")},
        headers=leader_headers,
    )
    assert response.status_code == 200
    assert response.json()["document"]["status"] == "unsupported"


async def test_list_documents_empty_for_new_project(client):
    leader_headers, project_id, _ = await _setup_leader_with_project(client, "empty")

    response = await client.get(f"/api/v1/projects/{project_id}/documents", headers=leader_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_upload_valid_document_is_queued_as_processing(client):
    """Requires Redis to be reachable (`docker compose up -d postgres redis`),
    since a successful upload enqueues an ingestion job."""
    leader_headers, project_id, _ = await _setup_leader_with_project(client, "upload")

    response = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("note.txt", b"hello organization", "text/plain")},
        headers=leader_headers,
    )
    assert response.status_code == 200
    body = response.json()["document"]
    assert body["status"] == "processing"
    assert body["filename"] == "note.txt"
    assert body["project_id"] == project_id


async def test_duplicate_file_reuses_storage_and_skips_reembedding(client, db_session):
    """No RQ worker runs in tests, so the first upload's ingestion is
    completed manually here to simulate it, then a byte-identical second
    upload should skip storage and re-embedding entirely."""
    leader_headers, project_id, _ = await _setup_leader_with_project(client, "dedup")
    content = b"identical content for dedup test"

    first = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("dup.txt", content, "text/plain")},
        headers=leader_headers,
    )
    assert first.status_code == 200
    first_doc = first.json()["document"]
    assert first_doc["status"] == "processing"

    document = await db_session.get(Document, uuid.UUID(first_doc["id"]))
    document.status = DocumentStatus.READY
    document.embedding_model = get_settings().embedding_model
    db_session.add(
        DocumentChunk(
            document_id=document.id,
            content=content.decode(),
            chunk_index=0,
            embedding=[0.0] * get_settings().embedding_dimensions,
            chunk_metadata={},
        )
    )
    await db_session.commit()

    second = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("dup-copy.txt", content, "text/plain")},
        headers=leader_headers,
    )
    assert second.status_code == 200
    second_doc = second.json()["document"]

    assert second_doc["id"] != first_doc["id"]
    assert second_doc["status"] == "ready"

    reloaded_first = await db_session.get(Document, uuid.UUID(first_doc["id"]))
    reloaded_second = await db_session.get(Document, uuid.UUID(second_doc["id"]))
    assert reloaded_first.file_path == reloaded_second.file_path


async def test_download_and_preview_project_document(client):
    leader_headers, project_id, _ = await _setup_leader_with_project(client, "dl")
    content = b"sample document content for download test"

    upload_res = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("sample.txt", content, "text/plain")},
        headers=leader_headers,
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document"]["id"]

    # 1. Download as attachment
    dl_res = await client.get(
        f"/api/v1/projects/{project_id}/documents/{doc_id}/download",
        headers=leader_headers,
    )
    assert dl_res.status_code == 200
    assert dl_res.content == content
    assert "attachment" in dl_res.headers.get("content-disposition", "")
    assert "sample.txt" in dl_res.headers.get("content-disposition", "")

    # 2. View file inline
    inline_res = await client.get(
        f"/api/v1/projects/{project_id}/documents/{doc_id}/file?disposition=inline",
        headers=leader_headers,
    )
    assert inline_res.status_code == 200
    assert inline_res.content == content
    assert "inline" in inline_res.headers.get("content-disposition", "")

    # 3. Preview document content
    preview_res = await client.get(
        f"/api/v1/projects/{project_id}/documents/{doc_id}/preview",
        headers=leader_headers,
    )
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["document_id"] == doc_id
    assert preview_data["filename"] == "sample.txt"
    assert preview_data["total_pages"] >= 1
    assert any("sample document content" in p["text"] for p in preview_data["pages"])


async def test_download_document_forbidden_for_outsider(client):
    leader_headers, project_id, _ = await _setup_leader_with_project(client, "sec")
    outsider_token, _ = await _register(client, "outsider-dl@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    upload_res = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("secret.txt", b"top secret", "text/plain")},
        headers=leader_headers,
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document"]["id"]

    # Outsider cannot download or preview
    assert (
        await client.get(
            f"/api/v1/projects/{project_id}/documents/{doc_id}/download",
            headers=outsider_headers,
        )
    ).status_code == 403

    assert (
        await client.get(
            f"/api/v1/projects/{project_id}/documents/{doc_id}/preview",
            headers=outsider_headers,
        )
    ).status_code == 403


async def test_download_document_cross_project_rejected(client):
    admin_token, _ = await _register(client, "admin-cross@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    team_a = (await client.post("/api/v1/teams", json={"name": "team-a"}, headers=admin_headers)).json()
    proj_a = (await client.post(f"/api/v1/teams/{team_a['id']}/projects", json={"name": "proj-a"}, headers=admin_headers)).json()

    team_b = (await client.post("/api/v1/teams", json={"name": "team-b"}, headers=admin_headers)).json()
    proj_b = (await client.post(f"/api/v1/teams/{team_b['id']}/projects", json={"name": "proj-b"}, headers=admin_headers)).json()

    upload_res = await client.post(
        f"/api/v1/projects/{proj_a['id']}/documents",
        files={"file": ("a.txt", b"content a", "text/plain")},
        headers=admin_headers,
    )
    doc_id = upload_res.json()["document"]["id"]

    # Requesting doc of project A via project B URL
    bad_res = await client.get(
        f"/api/v1/projects/{proj_b['id']}/documents/{doc_id}/download",
        headers=admin_headers,
    )
    assert bad_res.status_code == 400
