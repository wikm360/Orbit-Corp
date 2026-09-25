import uuid

import pytest

from app.core.config import Settings
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType
from app.features.documents.ingestion import pipeline as ingestion_pipeline
from app.features.documents.models import Document, DocumentStatus


class _StubEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        dim = Settings().embedding_dimensions
        return [[0.0] * dim for _ in texts]


async def _seed_conversation_document(db_session, *, file_path: str) -> Document:
    user = User(email=f"{uuid.uuid4()}@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    conversation = Conversation(type=ConversationType.PERSONAL, created_by=user.id)
    db_session.add(conversation)
    await db_session.flush()

    document = Document(
        filename="note.txt",
        file_path=file_path,
        content_type="text/plain",
        status=DocumentStatus.PROCESSING,
        content_hash=str(uuid.uuid4()),
        conversation_id=conversation.id,
        uploaded_by=user.id,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


async def test_ingestion_notifies_the_conversation_when_a_document_becomes_ready(
    db_session, monkeypatch, tmp_path
):
    monkeypatch.setattr(ingestion_pipeline, "get_embedding_provider", lambda: _StubEmbeddingProvider())

    notified: list[tuple[uuid.UUID, dict]] = []

    async def fake_publish_event(conversation_id: uuid.UUID, event: dict) -> None:
        notified.append((conversation_id, event))

    monkeypatch.setattr(ingestion_pipeline, "publish_event", fake_publish_event)

    file_path = tmp_path / "note.txt"
    file_path.write_text("Our refund policy: five business days.")
    document = await _seed_conversation_document(db_session, file_path=str(file_path))

    await ingestion_pipeline.run_ingestion_pipeline(document.id, str(file_path))

    assert len(notified) == 1
    conversation_id, event = notified[0]
    assert conversation_id == document.conversation_id
    assert event == {
        "event": "document_status",
        "document_id": str(document.id),
        "status": "ready",
        "filename": "note.txt",
    }

    await db_session.refresh(document)
    assert document.status == DocumentStatus.READY


async def test_ingestion_persists_a_utf16_txt_file_without_a_postgres_encoding_error(
    db_session, monkeypatch, tmp_path
):
    """Regression test for a real production failure: a Windows-originated
    UTF-16 transcript was parsed as if it were UTF-8, leaving a literal NUL
    byte after every character, which Postgres rejects outright on insert
    into `document_chunks` (`CharacterNotInRepertoireError: invalid byte
    sequence for encoding "UTF8": 0x00`). Exercises the real DB insert, not
    just the parser, since that's the layer where it actually surfaced."""
    monkeypatch.setattr(ingestion_pipeline, "get_embedding_provider", lambda: _StubEmbeddingProvider())

    async def fake_publish_event(conversation_id, event) -> None:
        pass

    monkeypatch.setattr(ingestion_pipeline, "publish_event", fake_publish_event)

    file_path = tmp_path / "transcript.txt"
    file_path.write_bytes(
        "(.venv) E:\\wikm\\STT\\STT>python transcribe.py\nمتن فارسی تستی\n".encode("utf-16")
    )
    document = await _seed_conversation_document(db_session, file_path=str(file_path))

    await ingestion_pipeline.run_ingestion_pipeline(document.id, str(file_path))

    await db_session.refresh(document)
    assert document.status == DocumentStatus.READY


async def test_ingestion_notifies_the_conversation_when_a_document_fails(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(ingestion_pipeline, "get_embedding_provider", lambda: _StubEmbeddingProvider())

    notified: list[tuple[uuid.UUID, dict]] = []

    async def fake_publish_event(conversation_id: uuid.UUID, event: dict) -> None:
        notified.append((conversation_id, event))

    monkeypatch.setattr(ingestion_pipeline, "publish_event", fake_publish_event)

    missing_path = str(tmp_path / "does-not-exist.txt")
    document = await _seed_conversation_document(db_session, file_path=missing_path)

    with pytest.raises(FileNotFoundError):
        await ingestion_pipeline.run_ingestion_pipeline(document.id, missing_path)

    assert len(notified) == 1
    conversation_id, event = notified[0]
    assert conversation_id == document.conversation_id
    assert event["event"] == "document_status"
    assert event["status"] == "failed"

    await db_session.refresh(document)
    assert document.status == DocumentStatus.FAILED
    assert document.error_message


async def test_no_notification_for_project_scoped_documents(db_session, monkeypatch, tmp_path):
    """Only conversation-scoped uploads have a live channel to notify on."""
    from app.features.access_control.models import Team
    from app.features.projects.models import Project

    monkeypatch.setattr(ingestion_pipeline, "get_embedding_provider", lambda: _StubEmbeddingProvider())

    notified: list[tuple[uuid.UUID, dict]] = []

    async def fake_publish_event(conversation_id: uuid.UUID, event: dict) -> None:
        notified.append((conversation_id, event))

    monkeypatch.setattr(ingestion_pipeline, "publish_event", fake_publish_event)

    team = Team(name=f"T-{uuid.uuid4()}")
    db_session.add(team)
    await db_session.flush()
    project = Project(team_id=team.id, name="P")
    db_session.add(project)
    await db_session.flush()

    file_path = tmp_path / "note.txt"
    file_path.write_text("project doc content")
    document = Document(
        filename="note.txt",
        file_path=str(file_path),
        content_type="text/plain",
        status=DocumentStatus.PROCESSING,
        content_hash=str(uuid.uuid4()),
        project_id=project.id,
    )
    db_session.add(document)
    await db_session.commit()

    await ingestion_pipeline.run_ingestion_pipeline(document.id, str(file_path))

    assert notified == []
