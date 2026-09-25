from app.core.config import Settings


class _StubEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        dim = Settings().embedding_dimensions
        return [[0.0] * dim for _ in texts]


async def _register(client, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    body = response.json()
    return body["access_token"], body["user"]["id"]


async def _setup_project_with_two_members(client, suffix: str, admin_headers: dict | None = None):
    # Team creation requires org-admin, and only the very first registered
    # user becomes super_admin - a test seeding more than one team/project
    # must share one admin rather than registering a fresh one each time.
    if admin_headers is None:
        admin_token, _ = await _register(client, f"mem-admin-{suffix}@example.com")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

    member_token, member_id = await _register(client, f"mem-member-{suffix}@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}

    team = await client.post("/api/v1/teams", json={"name": f"mem-team-{suffix}"}, headers=admin_headers)
    team_id = team.json()["id"]

    await client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": member_id, "role": "member"},
        headers=admin_headers,
    )

    project = await client.post(
        f"/api/v1/teams/{team_id}/projects", json={"name": f"mem-project-{suffix}"}, headers=admin_headers
    )
    project_id = project.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/members", json={"user_id": member_id}, headers=admin_headers
    )

    return admin_headers, member_headers, project_id


async def test_project_manager_can_create_list_update_verify_and_delete_a_memory(client, monkeypatch):
    from app.features.memory import service as memory_service

    monkeypatch.setattr(memory_service, "get_embedding_provider", lambda: _StubEmbeddingProvider())

    admin_headers, _member_headers, project_id = await _setup_project_with_two_members(client, "crud")

    create = await client.post(
        f"/api/v1/projects/{project_id}/memories",
        json={"fact_text": "We deploy on Fridays.", "category": "timeline"},
        headers=admin_headers,
    )
    assert create.status_code == 200
    memory = create.json()
    assert memory["fact_text"] == "We deploy on Fridays."
    assert memory["is_verified"] is False
    memory_id = memory["id"]

    listing = await client.get(f"/api/v1/projects/{project_id}/memories", headers=admin_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    update = await client.patch(
        f"/api/v1/projects/{project_id}/memories/{memory_id}",
        json={"fact_text": "We deploy on Thursdays now.", "is_verified": True},
        headers=admin_headers,
    )
    assert update.status_code == 200
    assert update.json()["fact_text"] == "We deploy on Thursdays now."
    assert update.json()["is_verified"] is True

    delete = await client.delete(
        f"/api/v1/projects/{project_id}/memories/{memory_id}", headers=admin_headers
    )
    assert delete.status_code == 204

    listing_after = await client.get(f"/api/v1/projects/{project_id}/memories", headers=admin_headers)
    assert listing_after.json() == []


async def test_plain_project_member_cannot_manage_memory(client, monkeypatch):
    from app.features.memory import service as memory_service

    monkeypatch.setattr(memory_service, "get_embedding_provider", lambda: _StubEmbeddingProvider())

    admin_headers, member_headers, project_id = await _setup_project_with_two_members(client, "rbac")

    create_as_admin = await client.post(
        f"/api/v1/projects/{project_id}/memories",
        json={"fact_text": "Some fact.", "category": "convention"},
        headers=admin_headers,
    )
    memory_id = create_as_admin.json()["id"]

    forbidden_list = await client.get(
        f"/api/v1/projects/{project_id}/memories", headers=member_headers
    )
    assert forbidden_list.status_code == 403

    forbidden_create = await client.post(
        f"/api/v1/projects/{project_id}/memories",
        json={"fact_text": "Member trying to add.", "category": "convention"},
        headers=member_headers,
    )
    assert forbidden_create.status_code == 403

    forbidden_update = await client.patch(
        f"/api/v1/projects/{project_id}/memories/{memory_id}",
        json={"is_verified": True},
        headers=member_headers,
    )
    assert forbidden_update.status_code == 403

    forbidden_delete = await client.delete(
        f"/api/v1/projects/{project_id}/memories/{memory_id}", headers=member_headers
    )
    assert forbidden_delete.status_code == 403


async def test_memory_from_another_project_is_rejected(client, monkeypatch):
    from app.features.memory import service as memory_service

    monkeypatch.setattr(memory_service, "get_embedding_provider", lambda: _StubEmbeddingProvider())

    admin_headers, _member_headers, project_a = await _setup_project_with_two_members(client, "crossA")
    _admin_headers_b, _member_headers_b, project_b = await _setup_project_with_two_members(
        client, "crossB", admin_headers
    )

    create = await client.post(
        f"/api/v1/projects/{project_a}/memories",
        json={"fact_text": "Project A secret.", "category": "business_rule"},
        headers=admin_headers,
    )
    memory_id = create.json()["id"]

    cross_update = await client.patch(
        f"/api/v1/projects/{project_b}/memories/{memory_id}",
        json={"is_verified": True},
        headers=admin_headers,
    )
    assert cross_update.status_code == 400
