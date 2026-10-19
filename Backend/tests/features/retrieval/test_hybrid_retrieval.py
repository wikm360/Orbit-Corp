import uuid

from app.core.config import get_settings
from app.features.chat.models import Conversation, ConversationType
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.features.projects.models import Project
from app.features.access_control.models import Team
from app.features.retrieval import service as retrieval_service
from app.features.retrieval.service import (
    HybridRetriever,
    VectorRetriever,
    get_retriever,
    query_terms,
    reciprocal_rank_fusion,
)

DIM = get_settings().embedding_dimensions


def _unit(index: int) -> list[float]:
    vector = [0.0] * DIM
    vector[index] = 1.0
    return vector


async def _project(db) -> Project:
    team = Team(name=f"T-{uuid.uuid4()}")
    db.add(team)
    await db.flush()
    project = Project(team_id=team.id, name=f"P-{uuid.uuid4()}")
    db.add(project)
    await db.flush()
    return project


async def _conversation(db, project: Project) -> Conversation:
    conversation = Conversation(type=ConversationType.PROJECT_GROUP, project_id=project.id)
    db.add(conversation)
    await db.flush()
    return conversation


async def _document(db, project: Project, texts_and_vectors: list[tuple[str, list[float]]]) -> Document:
    document = Document(
        filename="doc.pdf",
        file_path="/dev/null",
        content_type="application/pdf",
        status=DocumentStatus.READY,
        content_hash=str(uuid.uuid4()),
        embedding_model=get_settings().embedding_model,
        project_id=project.id,
    )
    db.add(document)
    await db.flush()
    for index, (content, vector) in enumerate(texts_and_vectors):
        db.add(
            DocumentChunk(
                document_id=document.id,
                content=content,
                chunk_index=index,
                embedding=vector,
                chunk_metadata={"page": index + 1},
            )
        )
    await db.commit()
    return document


def test_reciprocal_rank_fusion_rewards_items_in_several_rankings():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a"]], k=60)
    assert fused["a"] > fused["b"]
    assert fused["c"] > fused["b"]
    assert set(fused) == {"a", "b", "c"}


def test_query_terms_normalizes_dedupes_and_drops_stopwords():
    assert query_terms("بند ۱۲ بند و از قرارداد") == ["بند", "12", "قرارداد"]


async def test_chunk_search_text_is_filled_and_normalized(db_session):
    project = await _project(db_session)
    await _document(db_session, project, [("شركت ۱۴۰۴، بند 3.4", _unit(0))])
    from sqlalchemy import select

    chunk = (await db_session.execute(select(DocumentChunk))).scalar_one()
    assert chunk.search_text == "شرکت 1404  بند 3 4"
    assert chunk.search_tsv is not None


async def test_hybrid_finds_an_exact_term_the_embedding_misses(db_session):
    project = await _project(db_session)
    conversation = await _conversation(db_session, project)
    await _document(
        db_session,
        project,
        [
            ("متن عمومی درباره ایمنی کارگاه", _unit(0)),  # what the query vector points at
            ("طبق بند پرداخت شماره ZX-7781 مبلغ تسویه می شود", _unit(1)),  # the exact code, vector-orthogonal
        ],
    )
    query_embedding = _unit(0)

    vector_only = await VectorRetriever().retrieve(db_session, project.id, conversation.id, query_embedding, top_k=1)
    hybrid = await HybridRetriever().retrieve(
        db_session, project.id, conversation.id, query_embedding, top_k=2, query_text="ZX-7781 تسویه"
    )

    assert "ZX-7781" not in vector_only[0].content
    exact = [c for c in hybrid if "ZX-7781" in c.content]
    assert exact and exact[0].lexical_match is True


async def test_one_common_word_is_not_enough_for_a_lexical_match(db_session):
    project = await _project(db_session)
    conversation = await _conversation(db_session, project)
    await _document(
        db_session,
        project,
        [("فهرست قرارداد های منعقد شده", _unit(1))],
    )
    # Only the word «قرارداد» overlaps (1 of 3 terms; two hits are required) and the vector is orthogonal.
    chunks = await HybridRetriever().retrieve(
        db_session,
        project.id,
        conversation.id,
        _unit(0),
        top_k=5,
        query_text="قرارداد خرید سیمان",
        min_similarity=0.3,
    )
    assert chunks == []


async def test_trigram_forgives_a_typo_in_a_short_query(db_session):
    project = await _project(db_session)
    conversation = await _conversation(db_session, project)
    await _document(db_session, project, [("صورتجلسه تحویل موقت پیمانکار", _unit(1))])
    chunks = await HybridRetriever().retrieve(
        db_session, project.id, conversation.id, _unit(0), top_k=5, query_text="تحویل موقد", min_similarity=0.3
    )
    assert len(chunks) == 1
    assert chunks[0].lexical_match is True


async def test_lexical_search_never_crosses_the_access_scope(db_session):
    project = await _project(db_session)
    other_project = await _project(db_session)
    other_conversation = await _conversation(db_session, other_project)
    await _document(db_session, project, [("رمز محرمانه ZX-9999 فقط برای این پروژه", _unit(1))])

    chunks = await HybridRetriever().retrieve(
        db_session, other_project.id, other_conversation.id, _unit(0), top_k=5, query_text="ZX-9999 محرمانه"
    )
    assert chunks == []


async def test_hybrid_can_be_disabled(db_session, monkeypatch):
    monkeypatch.setattr(retrieval_service, "get_settings", lambda: type("S", (), {"retrieval_hybrid_enabled": False, "retrieval_rerank_enabled": False})())
    assert isinstance(get_retriever(), VectorRetriever)
