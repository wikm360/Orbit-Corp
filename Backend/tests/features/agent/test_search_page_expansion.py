import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.features.agent.tools.document_tools import SearchKnowledgeBaseTool
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType
from app.features.documents import service as documents_service
from app.features.documents.ingestion.parser import DocumentPage
from app.features.documents.ingestion.reconstructor import save_reconstructed_document
from app.features.documents.models import Document, DocumentStatus


def _chunk(doc_id, page, content, index=0):
    return SimpleNamespace(
        document_id=str(doc_id), document_filename="a.pdf", content=content, chunk_index=index, page_number=page, score=0.9
    )


async def test_hits_are_widened_to_their_full_page_once_per_page():
    doc = uuid.uuid4()
    chunks = [_chunk(doc, 5, "part A", 0), _chunk(doc, 5, "part B", 1), _chunk(doc, 9, "other page hit", 2)]
    pages = {(doc, 5): "FULL PAGE FIVE", (doc, 9): "FULL PAGE NINE"}
    with patch.object(documents_service, "get_page_texts", new=AsyncMock(return_value=pages)):
        out = await SearchKnowledgeBaseTool._passages(None, chunks, "page", None, uuid.uuid4())

    assert [text for _, text in out] == ["FULL PAGE FIVE", "FULL PAGE NINE"]  # page 5 appears once
    assert out[0][0] == "a.pdf (صفحه 5) - full page"


async def test_page_budget_falls_back_to_chunk_text_and_expand_chunk_skips_widening():
    doc = uuid.uuid4()
    chunks = [_chunk(doc, 1, "chunk one"), _chunk(doc, 2, "chunk two", 1)]
    big = "كلمه " * 400
    pages = {(doc, 1): big, (doc, 2): big}

    with (
        patch.object(documents_service, "get_page_texts", new=AsyncMock(return_value=pages)),
        patch("app.features.agent.tools.document_tools.settings") as settings,
    ):
        settings.search_page_expansion_max_tokens = 150  # room for roughly the first page only
        out = await SearchKnowledgeBaseTool._passages(None, chunks, "page", None, uuid.uuid4())
        assert out[0][0].endswith("full page") and documents_service._count_tokens(out[0][1]) <= 150
        assert out[1] == ("a.pdf (صفحه 2)", "chunk two")  # budget used up -> the matched chunk instead

        out = await SearchKnowledgeBaseTool._passages(None, chunks, "chunk", None, uuid.uuid4())
        assert [text for _, text in out] == ["chunk one", "chunk two"]


async def test_get_page_texts_reads_pages_and_respects_conversation_scope(db_session, tmp_path):
    user = User(email=f"{uuid.uuid4()}@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    own, other = (Conversation(type=ConversationType.PERSONAL, created_by=user.id) for _ in range(2))
    db_session.add_all([own, other])
    await db_session.flush()

    path = str(tmp_path / "doc.pdf")
    save_reconstructed_document(path, "doc.pdf", [DocumentPage(page_number=1, text="صفحه اول"), DocumentPage(page_number=2, text="صفحه دوم")])
    document = Document(
        filename="doc.pdf", file_path=path, content_type="application/pdf", status=DocumentStatus.READY,
        content_hash=str(uuid.uuid4()), conversation_id=own.id, uploaded_by=user.id,
    )
    db_session.add(document)
    await db_session.commit()

    texts = await documents_service.get_page_texts(db_session, [(document.id, 2), (document.id, 7)], project_id=None, conversation_id=own.id)
    assert texts == {(document.id, 2): "صفحه دوم"}  # a page that does not exist is simply absent

    hidden = await documents_service.get_page_texts(db_session, [(document.id, 1)], project_id=None, conversation_id=other.id)
    assert hidden == {}  # another conversation cannot read it through this helper
