import uuid

import pytest

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.features.chat.models import Conversation, ConversationType
from app.features.documents import service as documents_service
from app.features.documents.models import Document, DocumentChunk, DocumentStatus


async def _register(client, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    body = response.json()
    return body["access_token"], body["user"]["id"]


async def _leader_with_project(client, suffix: str, admin_headers: dict | None = None) -> tuple[str, str]:
    # Team creation requires org-admin, and only the very first registered
    # user becomes super_admin - callers seeding more than one team/project
    # in a single test must share one admin (via `admin_headers`) rather
    # than registering a fresh one each time.
    if admin_headers is None:
        admin_token, _ = await _register(client, f"owner-{suffix}@example.com")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
    leader_token, leader_id = await _register(client, f"leader-{suffix}@example.com")

    team = await client.post("/api/v1/teams", json={"name": f"team-{suffix}"}, headers=admin_headers)
    team_id = team.json()["id"]
    await client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": leader_id, "role": "leader"},
        headers=admin_headers,
    )
    project = await client.post(
        f"/api/v1/teams/{team_id}/projects", json={"name": f"project-{suffix}"}, headers=admin_headers
    )
    return leader_id, project.json()["id"]


async def _seed_conversation(db_session, *, project_id: uuid.UUID) -> Conversation:
    conversation = Conversation(type=ConversationType.PROJECT_GROUP, project_id=project_id)
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    return conversation


async def _seed_ready_document(db_session, *, project_id: uuid.UUID, pages: list[str]) -> Document:
    document = Document(
        filename="handbook.txt",
        file_path="/dev/null",
        content_type="text/plain",
        status=DocumentStatus.READY,
        content_hash=str(uuid.uuid4()),
        embedding_model=get_settings().embedding_model,
        project_id=project_id,
    )
    db_session.add(document)
    await db_session.flush()

    for index, content in enumerate(pages):
        metadata = {"heading": "Introduction"} if index == 0 else {}
        db_session.add(
            DocumentChunk(
                document_id=document.id,
                content=content,
                chunk_index=index,
                embedding=[0.0] * get_settings().embedding_dimensions,
                chunk_metadata=metadata,
            )
        )
    await db_session.commit()
    await db_session.refresh(document)
    return document


async def test_get_document_page_range_returns_only_requested_pages(client, db_session):
    leader_id, project_id = await _leader_with_project(client, "pagerange")
    document = await _seed_ready_document(
        db_session, project_id=uuid.UUID(project_id), pages=["alpha content", "beta content", "gamma content"]
    )
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))

    text = await documents_service.get_document_page_range(
        db_session,
        document.id,
        2,
        2,
        project_id=uuid.UUID(project_id),
        conversation_id=conversation.id,
    )

    assert "beta content" in text
    assert "alpha content" not in text
    assert "gamma content" not in text


async def test_get_full_document_content_concatenates_all_pages(client, db_session):
    leader_id, project_id = await _leader_with_project(client, "fullread")
    document = await _seed_ready_document(
        db_session, project_id=uuid.UUID(project_id), pages=["alpha content", "beta content"]
    )
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))

    text = await documents_service.get_full_document_content(
        db_session,
        document.id,
        project_id=uuid.UUID(project_id),
        conversation_id=conversation.id,
    )

    assert "alpha content" in text
    assert "beta content" in text


async def test_get_full_document_content_guards_against_oversized_documents(client, db_session):
    leader_id, project_id = await _leader_with_project(client, "toolarge")
    document = await _seed_ready_document(
        db_session, project_id=uuid.UUID(project_id), pages=["a fairly long page of sample text " * 20]
    )
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))

    result = await documents_service.get_full_document_content(
        db_session,
        document.id,
        project_id=uuid.UUID(project_id),
        conversation_id=conversation.id,
        max_tokens=5,
    )

    assert result["error"] == "DOCUMENT_TOO_LARGE"
    assert result["total_pages"] == 1


async def test_document_reads_are_scoped_to_accessible_projects(client, db_session):
    admin_token, _ = await _register(client, "owner-scope@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    leader_id, project_id = await _leader_with_project(client, "scopeA", admin_headers)
    _, other_project_id = await _leader_with_project(client, "scopeB", admin_headers)
    document = await _seed_ready_document(
        db_session, project_id=uuid.UUID(project_id), pages=["secret content"]
    )
    other_conversation = await _seed_conversation(db_session, project_id=uuid.UUID(other_project_id))

    with pytest.raises(NotFoundError):
        await documents_service.get_full_document_content(
            db_session,
            document.id,
            project_id=uuid.UUID(other_project_id),
            conversation_id=other_conversation.id,
        )


async def test_get_document_info_reports_facts_without_the_uploader(client, db_session):
    _, project_id = await _leader_with_project(client, "info")
    document = await _seed_ready_document(
        db_session, project_id=uuid.UUID(project_id), pages=["page one text", "page two text"]
    )
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))

    info = await documents_service.get_document_info(
        db_session, document.id, project_id=uuid.UUID(project_id), conversation_id=conversation.id
    )

    assert info["filename"] == "handbook.txt"
    assert info["content_type"] == "text/plain"
    assert info["status"] == "ready"
    assert info["scope"] == "project"
    assert info["total_pages"] == 2
    assert info["chunk_count"] == 2
    assert info["estimated_tokens"] > 0
    assert info["fits_read_entire_document"] is True
    assert "uploaded_by" not in info


async def test_get_document_info_flags_documents_too_large_to_read_whole(client, db_session, monkeypatch):
    _, project_id = await _leader_with_project(client, "infobig")
    document = await _seed_ready_document(
        db_session, project_id=uuid.UUID(project_id), pages=["word " * 50]
    )
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))
    monkeypatch.setattr(documents_service, "FULL_DOCUMENT_MAX_TOKENS", 5)

    info = await documents_service.get_document_info(
        db_session, document.id, project_id=uuid.UUID(project_id), conversation_id=conversation.id
    )

    assert info["fits_read_entire_document"] is False


async def test_get_document_info_is_scoped_to_accessible_projects(client, db_session):
    admin_token, _ = await _register(client, "owner-infoscope@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    _, project_id = await _leader_with_project(client, "infoA", admin_headers)
    _, other_project_id = await _leader_with_project(client, "infoB", admin_headers)
    document = await _seed_ready_document(db_session, project_id=uuid.UUID(project_id), pages=["secret"])
    other_conversation = await _seed_conversation(db_session, project_id=uuid.UUID(other_project_id))

    with pytest.raises(NotFoundError):
        await documents_service.get_document_info(
            db_session,
            document.id,
            project_id=uuid.UUID(other_project_id),
            conversation_id=other_conversation.id,
        )


def test_join_pages_cuts_at_a_page_boundary_and_says_where_to_continue(monkeypatch):
    from app.features.documents import service

    monkeypatch.setattr(service.settings, "read_pages_max_tokens", 300)
    pages = [(n, "word " * 200) for n in range(5, 10)]

    text = service._join_pages("a.pdf", pages, 9)

    assert "[صفحه 5]" in text and "[صفحه 9]" not in text
    assert "starting at page 6" in text

    monkeypatch.setattr(service.settings, "read_pages_max_tokens", 0)
    uncapped = service._join_pages("a.pdf", pages, 9)
    assert "[صفحه 9]" in uncapped and "Output cut" not in uncapped
