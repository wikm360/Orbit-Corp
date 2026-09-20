from sqlalchemy.orm import configure_mappers


async def _register(client, email: str) -> tuple[dict, str]:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


async def _team_with_project(client):
    admin, _ = await _register(client, "admin@example.com")  # first user = super admin
    member, member_id = await _register(client, "member@example.com")

    team_id = (await client.post("/api/v1/teams", json={"name": "T"}, headers=admin)).json()["id"]
    await client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": member_id, "role": "member"},
        headers=admin,
    )
    project_id = (
        await client.post(f"/api/v1/teams/{team_id}/projects", json={"name": "P"}, headers=admin)
    ).json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/members", json={"user_id": member_id}, headers=admin
    )
    return admin, member, member_id, team_id, project_id


def test_orm_mappers_configure():
    configure_mappers()


async def test_first_registered_user_is_super_admin_and_later_ones_are_not(client):
    _, _ = await _register(client, "first@example.com")
    second = await client.post(
        "/api/v1/auth/register", json={"email": "second@example.com", "password": "supersecret"}
    )
    first_me = await client.post(
        "/api/v1/auth/login", json={"email": "first@example.com", "password": "supersecret"}
    )
    assert first_me.json()["user"]["role"] == "super_admin"
    assert second.json()["user"]["role"] == "user"


async def test_removing_user_from_team_revokes_project_access(client):
    admin, member, member_id, team_id, project_id = await _team_with_project(client)

    assert (await client.get(f"/api/v1/projects/{project_id}", headers=member)).status_code == 200
    mine = await client.get("/api/v1/projects/mine", headers=member)
    assert [p["id"] for p in mine.json()] == [project_id]

    removed = await client.delete(f"/api/v1/teams/{team_id}/members/{member_id}", headers=admin)
    assert removed.status_code == 204

    assert (await client.get(f"/api/v1/projects/{project_id}", headers=member)).status_code == 403
    assert (await client.get("/api/v1/projects/mine", headers=member)).json() == []


async def test_removed_user_loses_project_group_chat_access(client):
    admin, member, member_id, team_id, project_id = await _team_with_project(client)
    conversation = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "project_group", "project_id": project_id},
        headers=admin,
    )
    conversation_id = conversation.json()["id"]
    url = f"/api/v1/chat/conversations/{conversation_id}"
    assert (await client.get(url, headers=member)).status_code == 200

    await client.delete(f"/api/v1/teams/{team_id}/members/{member_id}", headers=admin)

    assert (await client.get(url, headers=member)).status_code == 403


async def test_member_cannot_manage_team_and_admin_can_read_personal_chats(client):
    admin, member, member_id, team_id, project_id = await _team_with_project(client)

    forbidden = await client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": member_id, "role": "leader"},
        headers=member,
    )
    assert forbidden.status_code == 403

    personal = await client.post(
        "/api/v1/chat/conversations", json={"type": "personal"}, headers=member
    )
    conversation_id = personal.json()["id"]
    assert (
        await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=admin)
    ).status_code == 200
    outsider, _ = await _register(client, "outsider@example.com")
    assert (
        await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=outsider)
    ).status_code == 403
