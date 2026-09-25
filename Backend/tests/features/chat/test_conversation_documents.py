async def _register(client, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return response.json()["access_token"]


async def test_uploaded_conversation_document_is_listed_with_its_status(client):
    """Requires Redis to be reachable (`docker compose up -d postgres redis`),
    since a successful upload enqueues an ingestion job."""
    token = await _register(client, "convdocs@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/chat/conversations", json={"type": "personal"}, headers=headers
    )
    conversation_id = create.json()["id"]

    upload = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/documents",
        files={"file": ("note.txt", b"hello organization", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 200
    assert upload.json()["document"]["status"] == "processing"

    listing = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}/documents", headers=headers
    )
    assert listing.status_code == 200
    docs = listing.json()
    assert len(docs) == 1
    assert docs[0]["filename"] == "note.txt"
    assert docs[0]["conversation_id"] == conversation_id


async def test_conversation_documents_are_only_visible_to_the_owner(client):
    token = await _register(client, "convdocs-owner@example.com")
    other_token = await _register(client, "convdocs-outsider@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    create = await client.post(
        "/api/v1/chat/conversations", json={"type": "personal"}, headers=headers
    )
    conversation_id = create.json()["id"]

    forbidden = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}/documents", headers=other_headers
    )
    assert forbidden.status_code == 403
