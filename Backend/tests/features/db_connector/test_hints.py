import pytest

from app.features.db_connector.hints import (
    ingest_hints,
    load_core_prompt,
    load_corpus,
    retrieve_hints,
)


def test_load_core_prompt():
    prompt = load_core_prompt()
    assert "محور گستر نصر" in prompt
    assert "قواعد ثابت" in prompt


def test_load_corpus():
    corpus = load_corpus()
    assert len(corpus) > 100
    assert "id" in corpus[0]
    assert "text" in corpus[0]


@pytest.mark.asyncio
async def test_hints_ingest_and_retrieve(db_session):
    stats = await ingest_hints(db_session)
    assert stats["total"] > 100

    # Retrieve hints for a sample question
    retrieved = await retrieve_hints(db_session, "مانده بدهی طرف حساب جهاد نصر")
    assert len(retrieved.keys) > 0
    assert len(retrieved.blocks) > 0

