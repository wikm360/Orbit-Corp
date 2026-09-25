async def _register(client, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    body = response.json()
    return body["access_token"], body["user"]["id"]


async def test_personal_conversation_title_can_be_renamed(client):
    token, _ = await _register(client, "renamer@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/chat/conversations", json={"type": "personal"}, headers=headers
    )
    assert create.status_code == 200
    conversation_id = create.json()["id"]
    assert create.json()["title"] == "New conversation"

    patch = await client.patch(
        f"/api/v1/chat/conversations/{conversation_id}",
        json={"title": "Renamed chat", "linked_project_id": None},
        headers=headers,
    )
    assert patch.status_code == 200
    assert patch.json()["title"] == "Renamed chat"

    detail = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=headers)
    assert detail.json()["title"] == "Renamed chat"


async def test_omitting_title_leaves_it_untouched(client):
    token, _ = await _register(client, "notitlechange@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "personal", "title": "Original title"},
        headers=headers,
    )
    conversation_id = create.json()["id"]

    patch = await client.patch(
        f"/api/v1/chat/conversations/{conversation_id}",
        json={"linked_project_id": None},
        headers=headers,
    )
    assert patch.status_code == 200
    assert patch.json()["title"] == "Original title"


async def test_group_conversation_title_does_not_default_to_project_name_and_can_be_renamed(client):
    admin_token, _ = await _register(client, "grouprename-admin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    team = await client.post("/api/v1/teams", json={"name": "rename-team"}, headers=admin_headers)
    project = await client.post(
        f"/api/v1/teams/{team.json()['id']}/projects",
        json={"name": "Distinctive Project Name"},
        headers=admin_headers,
    )
    project_id = project.json()["id"]

    create = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "project_group", "project_id": project_id},
        headers=admin_headers,
    )
    assert create.status_code == 200
    conversation_id = create.json()["id"]
    # The title must be an independent default, not a stand-in for the
    # project's name.
    assert create.json()["title"] != "Distinctive Project Name"

    patch = await client.patch(
        f"/api/v1/chat/conversations/{conversation_id}",
        json={"title": "Sprint planning", "linked_project_id": None},
        headers=admin_headers,
    )
    assert patch.status_code == 200
    assert patch.json()["title"] == "Sprint planning"
