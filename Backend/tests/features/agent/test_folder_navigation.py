"""Agentic folder navigation: the first-level tree in the prompt, `browse_folder`, and `path_prefix` search. Needs Postgres."""
import uuid

import pytest

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.core.security import hash_password
from app.features.agent import engine as engine_module
from app.features.agent.engine import AgentEngine
from app.features.agent.tools.document_tools import SearchKnowledgeBaseTool
from app.features.agent.tools.folder_tools import BrowseFolderTool, project_tree_summary
from app.features.agent.tools.registry import build_default_registry
from app.features.auth.models import User, UserRole
from app.features.chat.models import Conversation, ConversationType
from app.features.documents import folder_service
from app.features.documents.chunk_paths import refresh_chunk_paths
from app.features.documents.models import Document, DocumentChunk, DocumentFolder, DocumentStatus
from tests.features.documents.test_file_manager import _leader_with_project, _second_project


def _vector(hot: int) -> list[float]:
    """Unit vector; the query embeds to axis 0 and chunks to axis 1, so cosine similarity is 0 (never a NaN zero vector)."""
    vec = [0.0] * get_settings().embedding_dimensions
    vec[hot] = 1.0
    return vec


async def _setup(client, db_session, tag: str, with_second_project: bool = False):
    leader, pid, team_id, _ = await _leader_with_project(client, tag)
    project_id = uuid.UUID(pid)
    user = User(email=f"{uuid.uuid4()}@example.com", hashed_password=hash_password("supersecret"), role=UserRole.USER)
    db_session.add(user)
    await db_session.flush()
    conversation = Conversation(type=ConversationType.PERSONAL, created_by=user.id, linked_project_id=project_id)
    db_session.add(conversation)
    await db_session.commit()
    context = UserContext(user=user, team_ids=[], led_team_ids=[], project_ids=[project_id])
    if with_second_project:
        return project_id, user, conversation, context, uuid.UUID(await _second_project(client, leader, team_id, f"other-{tag}"))
    return project_id, user, conversation, context


async def _folder(db, project_id, user, name, parent=None) -> DocumentFolder:
    folder = DocumentFolder(project_id=project_id, parent_id=parent.id if parent else None, name=name, created_by=user.id)
    db.add(folder)
    await db.commit()
    return folder


async def _doc(db, project_id, user, name, folder=None, status=DocumentStatus.READY, content=None, error=None) -> Document:
    document = Document(
        filename=name, file_path=f"/x/{uuid.uuid4()}", content_type="application/pdf", content_hash=uuid.uuid4().hex, status=status, error_message=error,
        project_id=project_id, folder_id=folder.id if folder else None, uploaded_by=user.id,
    )
    db.add(document)
    await db.flush()
    if content is not None:
        db.add(DocumentChunk(document_id=document.id, content=content, chunk_index=0, embedding=_vector(1), chunk_metadata={"page": 1}))
    await db.commit()
    return document


def test_resolve_path_walks_names_case_insensitively_and_names_the_missing_part():
    pid, uid = uuid.uuid4(), uuid.uuid4()
    a = DocumentFolder(id=uuid.uuid4(), project_id=pid, parent_id=None, name="امور تعدیل", created_by=uid)
    b = DocumentFolder(id=uuid.uuid4(), project_id=pid, parent_id=a.id, name="Round2", created_by=uid)
    folders = {a.id: a, b.id: b}

    assert folder_service.resolve_path(folders, "") is None
    assert folder_service.resolve_path(folders, "/امور تعدیل/round2/") == b.id
    assert folder_service.resolve_path(folders, "امور تعدیل\\Round2") == b.id
    with pytest.raises(Exception, match="'Nope' not found inside 'امور تعدیل'"):
        folder_service.resolve_path(folders, "امور تعدیل/Nope")


async def test_tree_summary_lists_top_level_folders_with_recursive_counts_and_not_ready_files(client, db_session):
    project_id, user, _, _ = await _setup(client, db_session, "tree")
    adjust = await _folder(db_session, project_id, user, "امور تعدیل")
    round2 = await _folder(db_session, project_id, user, "تعدیل ۲", adjust)
    await _doc(db_session, project_id, user, "a.pdf", adjust)
    await _doc(db_session, project_id, user, "b.pdf", round2, status=DocumentStatus.FAILED, error="OCR boom")
    await _doc(db_session, project_id, user, "loose.pdf")

    tree = await project_tree_summary(db_session, project_id)

    assert "- امور تعدیل/ (2 files, 1 not ready (failed 1))" in tree
    assert "- loose.pdf (file, document_id:" in tree and "ready)" in tree
    assert "تعدیل ۲" not in tree  # only the first level


async def test_browse_folder_lists_subfolders_files_ids_and_status_and_guides_a_wrong_path(client, db_session):
    project_id, user, conversation, context = await _setup(client, db_session, "browse")
    adjust = await _folder(db_session, project_id, user, "امور تعدیل")
    round2 = await _folder(db_session, project_id, user, "تعدیل شماره2", adjust)
    approval = await _doc(db_session, project_id, user, "تایید کارفرما.pdf", round2)
    scan = await _doc(db_session, project_id, user, "scan.pdf", round2, status=DocumentStatus.FAILED, error="insufficient credit")
    tool = BrowseFolderTool()

    top = (await tool.execute(db=db_session, context=context, conversation=conversation)).text
    assert top.startswith("Folder: (top level)") and "- امور تعدیل/ (2 files, 1 not ready (failed 1))" in top

    inner = (await tool.execute(db=db_session, context=context, conversation=conversation, path="امور تعدیل/تعدیل شماره2")).text
    assert f"- تایید کارفرما.pdf | document_id: {approval.id} | ready" in inner
    assert f"document_id: {scan.id} | failed: insufficient credit" in inner

    bad = (await tool.execute(db=db_session, context=context, conversation=conversation, path="امور مالی")).text
    assert "not found" in bad and "Top-level folders: امور تعدیل" in bad


async def test_browse_folder_pages_long_listings(client, db_session):
    project_id, user, conversation, context = await _setup(client, db_session, "paging")
    folder = await _folder(db_session, project_id, user, "Big")
    for i in range(105):
        db_session.add(Document(filename=f"f{i:03}.pdf", file_path=f"/x/{i}", content_type="x", content_hash=f"h{i}", status=DocumentStatus.READY, project_id=project_id, folder_id=folder.id, uploaded_by=user.id))
    await db_session.commit()
    tool = BrowseFolderTool()

    first = (await tool.execute(db=db_session, context=context, conversation=conversation, path="Big")).text
    assert "Files (105, showing 1-100)" in first and "offset=100" in first and "f099.pdf" in first and "f100.pdf" not in first
    second = (await tool.execute(db=db_session, context=context, conversation=conversation, path="Big", offset=100)).text
    assert "f104.pdf" in second and "more files" not in second


async def test_browse_folder_is_only_offered_when_the_chat_has_a_project(client, db_session):
    project_id, user, conversation, context = await _setup(client, db_session, "avail")
    plain = Conversation(type=ConversationType.PERSONAL, created_by=user.id)
    db_session.add(plain)
    await db_session.commit()
    registry = build_default_registry()

    names = lambda conv: {t["function"]["name"] for t in registry.to_openai_tools(context, conv)}  # noqa: E731
    assert "browse_folder" in names(conversation)
    assert "browse_folder" not in names(plain)
    assert "list_project_documents" not in names(conversation)


async def test_browse_folder_cannot_see_another_projects_folders(client, db_session):
    project_id, user, conversation, context, other_project = await _setup(client, db_session, "mine", with_second_project=True)
    await _folder(db_session, other_project, user, "SECRET-FOLDER")

    text = (await BrowseFolderTool().execute(db=db_session, context=context, conversation=conversation, path="SECRET-FOLDER")).text

    assert "not found" in text and "SECRET" not in text.split("Top-level folders:")[1]


async def test_search_with_path_prefix_only_looks_inside_that_folder(client, db_session, monkeypatch):
    project_id, user, conversation, context = await _setup(client, db_session, "scoped")
    inside = await _folder(db_session, project_id, user, "تعدیل ۲")
    outside = await _folder(db_session, project_id, user, "صورت وضعیت")
    a = await _doc(db_session, project_id, user, "تایید کارفرما.pdf", inside, content="مبلغ تایید شده کارفرما")
    b = await _doc(db_session, project_id, user, "وضعیت ۳.pdf", outside, content="مبلغ تایید شده کارفرما")
    await refresh_chunk_paths(db_session, project_id)

    class _Embedder:
        async def embed(self, texts):
            return [_vector(0) for _ in texts]

    import app.features.agent.tools.document_tools as dt

    monkeypatch.setattr(dt, "get_embedding_provider", lambda: _Embedder())
    monkeypatch.setattr(get_settings(), "retrieval_rerank_enabled", False)
    monkeypatch.setattr(dt.settings, "retrieval_score_threshold", -1.0)
    tool = SearchKnowledgeBaseTool()

    everywhere = await tool.execute(db=db_session, context=context, conversation=conversation, query="مبلغ تایید کارفرما")
    scoped = await tool.execute(db=db_session, context=context, conversation=conversation, query="مبلغ تایید کارفرما", path_prefix="تعدیل ۲")

    assert {c.document_id for c in everywhere.citations} == {str(a.id), str(b.id)}
    assert {c.document_id for c in scoped.citations} == {str(a.id)}
    assert "تعدیل ۲/تایید کارفرما.pdf" in scoped.text  # the label carries the folder path

    missing = await tool.execute(db=db_session, context=context, conversation=conversation, query="x", path_prefix="نیست")
    assert "not found" in missing.text and not missing.citations

    # a file name (bare, or with its folder) confines the search to that one file
    by_name = await tool.execute(
        db=db_session, context=context, conversation=conversation, query="مبلغ تایید کارفرما", path_prefix="وضعیت ۳.pdf"
    )
    by_path = await tool.execute(
        db=db_session, context=context, conversation=conversation, query="مبلغ تایید کارفرما", path_prefix="تعدیل ۲/تایید کارفرما.pdf"
    )
    assert {c.document_id for c in by_name.citations} == {str(b.id)}
    assert {c.document_id for c in by_path.citations} == {str(a.id)}


async def test_folder_and_file_names_are_searchable_even_when_the_text_never_says_them(client, db_session, monkeypatch):
    project_id, user, conversation, context = await _setup(client, db_session, "names")
    folder = await _folder(db_session, project_id, user, "تعدیل شماره2")
    target = await _doc(db_session, project_id, user, "تائید کارفرما تعدیل 2.pdf", folder, content="مبلغ ۱۲۰ میلیون ریال")
    await _doc(db_session, project_id, user, "other.pdf", None, content="متن بی ربط درباره بتن")
    await refresh_chunk_paths(db_session, project_id)

    class _Embedder:
        async def embed(self, texts):
            return [_vector(0) for _ in texts]

    import app.features.agent.tools.document_tools as dt

    monkeypatch.setattr(dt, "get_embedding_provider", lambda: _Embedder())
    monkeypatch.setattr(get_settings(), "retrieval_rerank_enabled", False)
    monkeypatch.setattr(dt.settings, "retrieval_score_threshold", 2.0)  # vector side rejects everything: only lexical can match

    result = await SearchKnowledgeBaseTool().execute(db=db_session, context=context, conversation=conversation, query="تایید کارفرما تعدیل شماره 2")

    assert [c.document_id for c in result.citations] == [str(target.id)]


async def test_system_prompt_puts_the_stable_parts_first_and_the_project_tree_before_chat_uploads(client, db_session, monkeypatch):
    project_id, user, conversation, context = await _setup(client, db_session, "prompt")
    await _folder(db_session, project_id, user, "امور تعدیل")
    await _doc(db_session, project_id, user, "upload.pdf")  # not a conversation upload: only shows via the tree
    chat_doc = Document(filename="chat-file.png", file_path="/x/1", content_type="image/png", content_hash="chat", status=DocumentStatus.READY, conversation_id=conversation.id, uploaded_by=user.id)
    db_session.add(chat_doc)
    await db_session.commit()
    monkeypatch.setattr(get_settings(), "rahkaran_db_enabled", False)

    messages = await AgentEngine()._build_messages(db_session, conversation, context)
    system = messages[0]["content"]

    assert system.startswith(engine_module.SYSTEM_PROMPT)
    assert system.index("Project knowledge base - top level") < system.index("Files uploaded directly to this chat")
    assert "- امور تعدیل/ (0 files)" in system or "امور تعدیل/" in system
    assert "browse_folder" in system


async def test_a_chat_without_a_project_gets_no_tree(client, db_session):
    _, user, conversation, context = await _setup(client, db_session, "notree")
    plain = Conversation(type=ConversationType.PERSONAL, created_by=user.id)
    db_session.add(plain)
    await db_session.commit()

    messages = await AgentEngine()._build_messages(db_session, plain, context)

    assert "Project knowledge base" not in messages[0]["content"]
