async def _register(client, email: str) -> str:
    register = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return register.json()["access_token"]


async def test_chat_streams_general_response_without_documents(client):
    """With no documents indexed, retrieval finds nothing so the assistant
    should fall back to a general (non-RAG) response with no sources."""
    token = await _register(client, "chatuser@example.com")

    async with client.stream(
        "POST",
        "/api/v1/chat",
        json={"message": "Hello there"},
        headers={"Authorization": f"Bearer {token}"},
    ) as response:
        assert response.status_code == 200
        body = ""
        async for chunk in response.aiter_text():
            body += chunk

    assert "event: start" in body
    assert "Hello" in body
    assert '"sources": []' in body


async def test_conversation_history_is_persisted(client):
    token = await _register(client, "chathistory@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with client.stream(
        "POST", "/api/v1/chat", json={"message": "First message"}, headers=headers
    ) as response:
        async for _ in response.aiter_text():
            pass

    conversations = await client.get("/api/v1/chat/conversations", headers=headers)
    assert conversations.status_code == 200
    assert len(conversations.json()) == 1

    conversation_id = conversations.json()[0]["id"]
    detail = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=headers
    )
    assert detail.status_code == 200
    sender_types = [m["sender_type"] for m in detail.json()["messages"]]
    assert sender_types == ["user", "assistant"]
