import uuid

from app.core.config import get_settings
from app.features.agent import engine as agent_engine_module
from app.features.agent.tools import document_tools as agent_document_tools
from app.features.documents.models import Document, DocumentChunk, DocumentStatus


async def _register(client, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    body = response.json()
    return body["access_token"], body["user"]["id"]


class _ConstantEmbeddingProvider:
    """A non-zero, identical vector for every text, so a query and the
    seeded chunk are a perfect (distance ~0) cosine match regardless of
    what's actually asked - keeps this test's retrieval scoring
    deterministic without depending on real semantic similarity."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        dim = get_settings().embedding_dimensions
        return [[1.0] + [0.0] * (dim - 1) for _ in texts]


class _ToolCallThenAnswerProvider:
    """Scripted model: calls `search_knowledge_base` on the first turn, then
    answers using whatever the tool returned."""

    def __init__(self):
        self.calls = 0

    def stream_chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return self._events(
                [
                    {
                        "type": "tool_calls",
                        "calls": [
                            {
                                "id": "call_1",
                                "name": "search_knowledge_base",
                                "arguments": '{"query": "refund policy"}',
                            }
                        ],
                    }
                ]
            )
        return self._events([{"type": "content", "delta": "Refunds are processed within 5 days."}])

    async def _events(self, events):
        for event in events:
            yield event


async def test_personal_chat_calls_a_tool_and_streams_a_citation_bearing_answer(
    client, db_session, monkeypatch
):
    token, user_id = await _register(client, "toolcaller@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    team = await client.post("/api/v1/teams", json={"name": "tool-team"}, headers=headers)
    project = await client.post(
        f"/api/v1/teams/{team.json()['id']}/projects", json={"name": "tool-project"}, headers=headers
    )
    project_id = project.json()["id"]

    embedding = [1.0] + [0.0] * (get_settings().embedding_dimensions - 1)
    document = Document(
        filename="policy.txt",
        file_path="/dev/null",
        content_type="text/plain",
        status=DocumentStatus.READY,
        content_hash=str(uuid.uuid4()),
        embedding_model=get_settings().embedding_model,
        project_id=uuid.UUID(project_id),
    )
    db_session.add(document)
    await db_session.flush()
    db_session.add(
        DocumentChunk(
            document_id=document.id,
            content="Our refund policy: refunds are processed within 5 business days.",
            chunk_index=0,
            embedding=embedding,
            chunk_metadata={},
        )
    )
    await db_session.commit()

    create = await client.post(
        "/api/v1/chat/conversations",
        json={"type": "personal", "linked_project_id": project_id},
        headers=headers,
    )
    assert create.status_code == 200
    conversation_id = create.json()["id"]

    monkeypatch.setattr(agent_document_tools, "get_embedding_provider", lambda: _ConstantEmbeddingProvider())
    monkeypatch.setattr(agent_engine_module, "get_llm_provider", lambda: _ToolCallThenAnswerProvider())

    async with client.stream(
        "POST",
        "/api/v1/chat",
        json={"conversation_id": conversation_id, "message": "What's our refund policy?"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        body = ""
        async for chunk in response.aiter_text():
            body += chunk

    assert "event: status" in body
    assert '"tool": "search_knowledge_base"' in body
    assert "Refunds are processed within 5 days." in body
    assert "event: done" in body
    assert '"document_filename": "policy.txt"' in body

    detail = await client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=headers)
    assistant_messages = [m for m in detail.json()["messages"] if m["sender_type"] == "assistant"]
    assert len(assistant_messages) == 1
    assert assistant_messages[0]["content"] == "Refunds are processed within 5 days."
    assert assistant_messages[0]["sources"][0]["document_filename"] == "policy.txt"
