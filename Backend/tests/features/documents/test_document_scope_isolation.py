import uuid

import pytest

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.core.exceptions import NotFoundError
from app.features.access_control.models import Team
from app.features.agent import engine as engine_module
from app.features.agent.engine import AgentEngine
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType
from app.features.documents import service as documents_service
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.features.projects.models import Project
from app.features.retrieval.service import get_retriever

_EMBEDDING = [1.0] + [0.0] * (get_settings().embedding_dimensions - 1)


async def _user(db_session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    return user


async def _conversation(db_session, user: User, *, project_id=None) -> Conversation:
    conversation = Conversation(
        type=ConversationType.PROJECT_GROUP if project_id else ConversationType.PERSONAL,
        created_by=user.id,
        project_id=project_id,
    )
    db_session.add(conversation)
    await db_session.flush()
    return conversation


async def _document(db_session, *, filename: str, uploaded_by, conversation_id=None, project_id=None):
    document = Document(
        filename=filename,
        file_path="/dev/null",
        content_type="text/plain",
        status=DocumentStatus.READY,
        content_hash=str(uuid.uuid4()),
        embedding_model=get_settings().embedding_model,
        conversation_id=conversation_id,
        project_id=project_id,
        uploaded_by=uploaded_by,
    )
    db_session.add(document)
    await db_session.flush()
    db_session.add(
        DocumentChunk(
            document_id=document.id,
            content=f"content of {filename}",
            chunk_index=0,
            embedding=_EMBEDDING,
            chunk_metadata={},
        )
    )
    return document


async def test_a_file_uploaded_to_one_chat_is_not_readable_from_another_chat(db_session):
    user = await _user(db_session)
    chat_a = await _conversation(db_session, user)
    chat_b = await _conversation(db_session, user)
    secret = await _document(db_session, filename="secret.txt", uploaded_by=user.id, conversation_id=chat_a.id)
    await db_session.commit()

    # Same user, different chat: must not be reachable.
    with pytest.raises(NotFoundError):
        await documents_service.get_document_outline(
            db_session, secret.id, project_id=None, conversation_id=chat_b.id
        )
    with pytest.raises(NotFoundError):
        await documents_service.get_full_document_content(
            db_session, secret.id, project_id=None, conversation_id=chat_b.id
        )

    # Its own chat still works.
    outline = await documents_service.get_document_outline(
        db_session, secret.id, project_id=None, conversation_id=chat_a.id
    )
    assert outline["filename"] == "secret.txt"


async def test_search_in_a_project_chat_never_returns_files_from_the_users_other_chats(db_session):
    user = await _user(db_session)
    team = Team(name=f"T-{uuid.uuid4()}")
    db_session.add(team)
    await db_session.flush()
    project = Project(team_id=team.id, name="P")
    db_session.add(project)
    await db_session.flush()

    project_chat = await _conversation(db_session, user, project_id=project.id)
    other_chat = await _conversation(db_session, user)
    await _document(db_session, filename="project-doc.txt", uploaded_by=user.id, project_id=project.id)
    await _document(db_session, filename="other-chat-doc.txt", uploaded_by=user.id, conversation_id=other_chat.id)
    await db_session.commit()

    chunks = await get_retriever().retrieve(db_session, project.id, project_chat.id, _EMBEDDING, top_k=10)

    assert {c.document_filename for c in chunks} == {"project-doc.txt"}


async def test_the_model_is_given_attachment_metadata_but_not_file_content(db_session, monkeypatch):
    user = await _user(db_session)
    chat = await _conversation(db_session, user)
    attached = await _document(db_session, filename="notes.txt", uploaded_by=user.id, conversation_id=chat.id)
    await db_session.commit()

    captured: list[list[dict]] = []

    class _CapturingProvider:
        def stream_chat(self, messages, tools=None):
            captured.append(messages)
            return self._stream()

        async def _stream(self):
            yield {"type": "content", "delta": "ok"}

    monkeypatch.setattr(engine_module, "get_llm_provider", lambda: _CapturingProvider())

    async def callback(event, data):
        pass

    context = UserContext(user=user, team_ids=[], led_team_ids=[], project_ids=[])
    await AgentEngine().run_agent_loop(db_session, chat, context, callback)

    system_prompt = captured[0][0]["content"]
    assert "notes.txt" in system_prompt
    assert str(attached.id) in system_prompt
    assert "content of notes.txt" not in system_prompt
