async def _register_admin_with_team(client, email: str) -> tuple[str, str]:
    register = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    team = await client.post(
        "/api/v1/admin/teams", json={"name": f"team-{email}"}, headers=headers
    )
    team_id = team.json()["id"]

    user_id = register.json()["user"]["id"]
    await client.post(
        "/api/v1/admin/team-memberships",
        json={"user_id": user_id, "team_id": team_id},
        headers=headers,
    )
    return headers["Authorization"], team_id


async def test_upload_document_requires_team_membership(client):
    auth_header, _ = await _register_admin_with_team(client, "docs1@example.com")

    other_team = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        "/api/v1/documents",
        data={"team_id": other_team},
        files={"file": ("note.txt", b"hello world", "text/plain")},
        headers={"Authorization": auth_header},
    )
    assert response.status_code == 400


async def test_upload_rejects_unsupported_extension(client):
    auth_header, team_id = await _register_admin_with_team(client, "docs2@example.com")

    response = await client.post(
        "/api/v1/documents",
        data={"team_id": team_id},
        files={"file": ("archive.zip", b"binarydata", "application/zip")},
        headers={"Authorization": auth_header},
    )
    assert response.status_code == 400


async def test_list_documents_empty_for_new_team(client):
    auth_header, _ = await _register_admin_with_team(client, "docs3@example.com")

    response = await client.get(
        "/api/v1/documents", headers={"Authorization": auth_header}
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_upload_valid_document_is_queued_as_processing(client):
    """Requires Redis to be reachable (`docker compose up -d postgres redis`),
    since a successful upload enqueues an ingestion job."""
    auth_header, team_id = await _register_admin_with_team(client, "docs4@example.com")

    response = await client.post(
        "/api/v1/documents",
        data={"team_id": team_id},
        files={"file": ("note.txt", b"hello organization", "text/plain")},
        headers={"Authorization": auth_header},
    )
    assert response.status_code == 200
    body = response.json()["document"]
    assert body["status"] == "processing"
    assert body["filename"] == "note.txt"
