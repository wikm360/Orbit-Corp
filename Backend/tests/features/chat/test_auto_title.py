import asyncio


async def _register(client, email: str) -> dict:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _send(client, headers, conversation_id, message) -> str:
    async with client.stream(
        "POST", "/api/v1/chat", json={"conversation_id": conversation_id, "message": message}, headers=headers
    ) as response:
        return "".join([chunk async for chunk in response.aiter_text()])


async def _title(client, headers, conversation_id) -> str:
    detail = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=headers)
    return detail.json()["title"]


async def _project(client, headers) -> str:
    team = await client.post("/api/v1/teams", json={"name": "T"}, headers=headers)
    project = await client.post(
        f"/api/v1/teams/{team.json()['id']}/projects", json={"name": "P"}, headers=headers
    )
    return project.json()["id"]


async def test_a_project_linked_personal_chat_is_titled_from_its_first_message(client):
    headers = await _register(client, "autotitle1@example.com")
    project_id = await _project(client, headers)
    created = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "personal", "linked_project_id": project_id},
        headers=headers,
    )
    conversation_id = created.json()["id"]
    assert created.json()["title"] == "New conversation"

    body = await _send(client, headers, conversation_id, "What is our   refund policy?")

    assert await _title(client, headers, conversation_id) == "What is our refund policy?"
    assert '"title": "What is our refund policy?"' in body  # in the SSE start event

    await _send(client, headers, conversation_id, "And for enterprise customers?")
    assert await _title(client, headers, conversation_id) == "What is our refund policy?"


async def test_a_title_the_user_chose_is_never_overwritten(client):
    headers = await _register(client, "autotitle2@example.com")
    created = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "personal", "title": "My own title"},
        headers=headers,
    )
    conversation_id = created.json()["id"]

    await _send(client, headers, conversation_id, "hello there")

    assert await _title(client, headers, conversation_id) == "My own title"


async def test_a_group_chat_is_titled_from_its_first_message_without_the_bot_trigger(client):
    headers = await _register(client, "autotitle3@example.com")
    project_id = await _project(client, headers)
    created = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "project_group", "project_id": project_id},
        headers=headers,
    )
    conversation_id = created.json()["id"]
    assert created.json()["title"] == "New group conversation"

    await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "@bot summarize the Q3 roadmap"},
        headers=headers,
    )
    await asyncio.sleep(0.3)  # let the detached AI reply finish before teardown

    assert await _title(client, headers, conversation_id) == "summarize the Q3 roadmap"

    await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "second message"},
        headers=headers,
    )
    assert await _title(client, headers, conversation_id) == "summarize the Q3 roadmap"
