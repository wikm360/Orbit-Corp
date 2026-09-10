from collections.abc import AsyncIterator

import pytest

from app.core.config import get_settings
from app.features.chat import service as chat_service
from app.providers.llm_provider import ChatMessage


class _StubLLMProvider:
    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        for token in ["Hello", ", ", "world!"]:
            yield token


class _StubEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        dim = get_settings().embedding_dimensions
        return [[0.0] * dim for _ in texts]


@pytest.fixture(autouse=True)
def _stub_providers(monkeypatch):
    monkeypatch.setattr(chat_service, "get_llm_provider", lambda: _StubLLMProvider())
    monkeypatch.setattr(chat_service, "get_embedding_provider", lambda: _StubEmbeddingProvider())


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
