import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.features.documents.models import Document, DocumentChunk, DocumentStatus


async def _register(client, email: str) -> dict:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _project(client, admin: dict) -> str:
    team = await client.post("/api/v1/teams", json={"name": "T"}, headers=admin)
    project = await client.post(
        f"/api/v1/teams/{team.json()['id']}/projects", json={"name": "P"}, headers=admin
    )
    return project.json()["id"]


async def test_batch_upload_accepts_valid_files_and_reports_rejected_ones_individually(client):
    """Requires Redis (`docker compose up -d postgres redis`): every accepted
    file is enqueued as its own ingestion job."""
    admin = await _register(client, "bulk@example.com")
    project_id = await _project(client, admin)

    response = await client.post(
        f"/api/v1/projects/{project_id}/documents/batch",
        files=[
            # A folder upload sends the relative path as the file name.
            ("files", ("policies/hr/leave.txt", b"leave policy", "text/plain")),
            ("files", ("policies/finance/travel.txt", b"travel policy", "text/plain")),
            ("files", ("archive.zip", b"PK\x03\x04", "application/zip")),
            ("files", ("empty.txt", b"", "text/plain")),
        ],
        headers=admin,
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["accepted"], body["rejected"]) == (2, 2)

    by_name = {item["filename"]: item for item in body["items"]}
    assert by_name["policies/hr/leave.txt"]["status"] == "accepted"
    assert by_name["policies/hr/leave.txt"]["document"]["status"] == "processing"
    assert by_name["policies/hr/leave.txt"]["document"]["project_id"] == project_id
    assert by_name["policies/finance/travel.txt"]["status"] == "accepted"
    assert by_name["archive.zip"]["status"] == "rejected"
    assert "Unsupported file type" in by_name["archive.zip"]["error"]
    assert by_name["empty.txt"] == {
        "filename": "empty.txt",
        "status": "rejected",
        "document": None,
        "error": "File is empty",
    }

    listing = await client.get(f"/api/v1/projects/{project_id}/documents", headers=admin)
    assert {d["filename"] for d in listing.json()} == {
        "policies/hr/leave.txt",
        "policies/finance/travel.txt",
    }


async def test_batch_upload_rejects_more_files_than_the_per_request_limit(client):
    admin = await _register(client, "bulk-limit@example.com")
    project_id = await _project(client, admin)
    too_many = get_settings().max_batch_upload_files + 1

    response = await client.post(
        f"/api/v1/projects/{project_id}/documents/batch",
        files=[("files", (f"f{i}.txt", b"x", "text/plain")) for i in range(too_many)],
        headers=admin,
    )

    assert response.status_code == 400


async def test_batch_upload_is_forbidden_for_a_non_manager(client):
    admin = await _register(client, "bulk-admin@example.com")
    outsider = await _register(client, "bulk-outsider@example.com")
    project_id = await _project(client, admin)

    response = await client.post(
        f"/api/v1/projects/{project_id}/documents/batch",
        files=[("files", ("a.txt", b"x", "text/plain"))],
        headers=outsider,
    )

    assert response.status_code == 403


async def test_conversation_batch_upload_attaches_every_file_to_that_chat(client):
    headers = await _register(client, "bulk-chat@example.com")
    conversation = await client.post(
        "/api/v1/chat/conversations", json={"type": "personal"}, headers=headers
    )
    conversation_id = conversation.json()["id"]

    response = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/documents/batch",
        files=[
            ("files", ("a.txt", b"first", "text/plain")),
            ("files", ("b.txt", b"second", "text/plain")),
        ],
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["accepted"] == 2
    listing = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}/documents", headers=headers
    )
    assert {d["filename"] for d in listing.json()} == {"a.txt", "b.txt"}
    assert all(d["conversation_id"] == conversation_id for d in listing.json())


async def test_a_failed_document_can_be_retried_but_a_ready_one_cannot(client, db_session):
    admin = await _register(client, "bulk-retry@example.com")
    project_id = await _project(client, admin)

    upload = await client.post(
        f"/api/v1/projects/{project_id}/documents/batch",
        files=[("files", ("a.txt", b"retry me", "text/plain"))],
        headers=admin,
    )
    document_id = uuid.UUID(upload.json()["items"][0]["document"]["id"])

    # Simulate a failed ingestion that had already persisted a stray chunk.
    document = await db_session.get(Document, document_id)
    document.status = DocumentStatus.FAILED
    document.error_message = "embedding API rate limit"
    db_session.add(
        DocumentChunk(
            document_id=document_id,
            content="stale",
            chunk_index=0,
            embedding=[0.0] * get_settings().embedding_dimensions,
            chunk_metadata={},
        )
    )
    await db_session.commit()

    retry = await client.post(
        f"/api/v1/projects/{project_id}/documents/{document_id}/retry", headers=admin
    )
    assert retry.status_code == 200
    assert retry.json()["status"] == "processing"
    assert retry.json()["error_message"] is None

    db_session.expire_all()
    chunks = (await db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == document_id))).all()
    assert chunks == []

    document = await db_session.get(Document, document_id)
    document.status = DocumentStatus.READY
    await db_session.commit()
    not_failed = await client.post(
        f"/api/v1/projects/{project_id}/documents/{document_id}/retry", headers=admin
    )
    assert not_failed.status_code == 400
