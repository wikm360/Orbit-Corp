import asyncio


async def _register(client, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    body = response.json()
    return body["access_token"], body["user"]["id"]


async def _setup_project_with_two_members(client, suffix: str):
    admin_token, _ = await _register(client, f"gc-admin-{suffix}@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    member_token, member_id = await _register(client, f"gc-member-{suffix}@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}

    outsider_token, _ = await _register(client, f"gc-outsider-{suffix}@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    team = await client.post(
        "/api/v1/teams", json={"name": f"gc-team-{suffix}"}, headers=admin_headers
    )
    team_id = team.json()["id"]

    await client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": member_id, "role": "member"},
        headers=admin_headers,
    )

    project = await client.post(
        f"/api/v1/teams/{team_id}/projects",
        json={"name": f"gc-project-{suffix}"},
        headers=admin_headers,
    )
    project_id = project.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": member_id},
        headers=admin_headers,
    )

    return admin_headers, member_headers, outsider_headers, project_id


async def test_project_group_chat_visible_to_members_only(client):
    admin_headers, member_headers, outsider_headers, project_id = await _setup_project_with_two_members(
        client, "visibility"
    )

    create = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "project_group", "project_id": project_id},
        headers=admin_headers,
    )
    assert create.status_code == 200
    conversation_id = create.json()["id"]

    member_view = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=member_headers
    )
    assert member_view.status_code == 200

    outsider_view = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=outsider_headers
    )
    assert outsider_view.status_code == 403


async def test_group_message_posted_and_visible_to_all_members(client):
    admin_headers, member_headers, _outsider_headers, project_id = await _setup_project_with_two_members(
        client, "post"
    )

    create = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "project_group", "project_id": project_id},
        headers=admin_headers,
    )
    conversation_id = create.json()["id"]

    post = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "hello team"},
        headers=member_headers,
    )
    assert post.status_code == 200
    assert post.json()["sender_type"] == "user"

    detail = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=admin_headers)
    contents = [m["content"] for m in detail.json()["messages"]]
    assert "hello team" in contents


async def test_group_message_with_trigger_gets_ai_reply(client):
    admin_headers, member_headers, _outsider_headers, project_id = await _setup_project_with_two_members(
        client, "trigger"
    )

    create = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "project_group", "project_id": project_id},
        headers=admin_headers,
    )
    conversation_id = create.json()["id"]

    await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "@bot what is our policy?"},
        headers=member_headers,
    )

    sender_types: list[str] = []
    for _ in range(30):
        await asyncio.sleep(0.1)
        detail = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=admin_headers)
        sender_types = [m["sender_type"] for m in detail.json()["messages"]]
        if "assistant" in sender_types:
            break

    assert "assistant" in sender_types


async def test_plain_group_message_does_not_trigger_ai(client):
    admin_headers, member_headers, _outsider_headers, project_id = await _setup_project_with_two_members(
        client, "notrigger"
    )

    create = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "project_group", "project_id": project_id},
        headers=admin_headers,
    )
    conversation_id = create.json()["id"]

    await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "just chatting, no bot needed"},
        headers=member_headers,
    )
    await asyncio.sleep(0.3)

    detail = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=admin_headers)
    sender_types = [m["sender_type"] for m in detail.json()["messages"]]
    assert sender_types == ["user"]
