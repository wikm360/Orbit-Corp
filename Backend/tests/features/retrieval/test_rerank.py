import asyncio
import uuid

from app.features.retrieval import service as retrieval_service
from app.features.retrieval.service import (
    HybridRetriever,
    RerankingRetriever,
    RetrievedChunk,
    VectorRetriever,
    get_retriever,
    parse_rerank_indexes,
)


def _chunk(index: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"c{index}", document_id="d", document_filename="f.pdf", content=f"passage {index}",
        chunk_index=index, score=0.5,
    )


class _InnerRetriever:
    def __init__(self, count: int = 6):
        self.chunks = [_chunk(i) for i in range(count)]
        self.requested_top_k = None

    async def retrieve(self, db, project_id, conversation_id, query_embedding, top_k, query_text=None, min_similarity=None):
        self.requested_top_k = top_k
        return self.chunks[:top_k]


class _ScriptedProvider:
    def __init__(self, reply=None, error=None, delay=0.0):
        self.reply, self.error, self.delay = reply, error, delay
        self.prompts: list[str] = []

    async def stream_chat(self, messages, tools=None):
        self.prompts.append(messages[0]["content"])
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        yield {"type": "content", "delta": self.reply[:5]}
        yield {"type": "content", "delta": self.reply[5:]}


async def _rerank(provider, inner=None, top_k=3, query="سؤال"):
    inner = inner or _InnerRetriever()
    retriever = RerankingRetriever(inner, provider)
    return await retriever.retrieve(None, uuid.uuid4(), uuid.uuid4(), [0.0], top_k, query_text=query), inner


def test_parse_rerank_indexes_accepts_a_json_array_inside_chatter():
    assert parse_rerank_indexes("Sure! [2, 0, 5]", 6, 5) == [2, 0, 5]
    assert parse_rerank_indexes("```json\n[1]\n```", 6, 5) == [1]


def test_parse_rerank_indexes_drops_invalid_and_duplicate_values_and_caps_the_count():
    assert parse_rerank_indexes("[1, 1, 9, -1, \"2\", true, 3, 4, 0]", 6, 3) == [1, 3, 4]


def test_parse_rerank_indexes_distinguishes_empty_from_garbage():
    assert parse_rerank_indexes("[]", 6, 5) == []
    assert parse_rerank_indexes("I cannot tell", 6, 5) is None
    assert parse_rerank_indexes("[1, 2", 6, 5) is None


async def test_rerank_orders_by_the_model_reply_and_asks_for_a_wider_candidate_list():
    provider = _ScriptedProvider("[4, 1]")
    results, inner = await _rerank(provider)

    assert [c.chunk_id for c in results] == ["c4", "c1"]
    assert inner.requested_top_k >= 20
    assert "سؤال" in provider.prompts[0] and "[0] passage 0" in provider.prompts[0]


async def test_an_empty_reply_means_nothing_answers_the_question():
    results, _ = await _rerank(_ScriptedProvider("[]"))
    assert results == []


async def test_provider_errors_fall_back_to_the_unranked_top_results():
    results, _ = await _rerank(_ScriptedProvider(error=RuntimeError("gateway down")))
    assert [c.chunk_id for c in results] == ["c0", "c1", "c2"]


async def test_unparsable_replies_fall_back_to_the_unranked_top_results():
    results, _ = await _rerank(_ScriptedProvider("no idea"))
    assert [c.chunk_id for c in results] == ["c0", "c1", "c2"]


async def test_a_slow_provider_times_out_and_falls_back(monkeypatch):
    monkeypatch.setattr(retrieval_service.get_settings(), "retrieval_rerank_timeout_seconds", 0.05)
    results, _ = await _rerank(_ScriptedProvider("[5]", delay=1.0))
    assert [c.chunk_id for c in results] == ["c0", "c1", "c2"]


async def test_a_single_candidate_or_no_query_skips_the_llm():
    provider = _ScriptedProvider("[0]")
    single, _ = await _rerank(provider, inner=_InnerRetriever(count=1))
    no_query, _ = await _rerank(provider, query=None)

    assert [c.chunk_id for c in single] == ["c0"]
    assert len(no_query) == 3
    assert provider.prompts == []


def test_get_retriever_wraps_only_when_rerank_is_enabled(monkeypatch):
    settings = retrieval_service.get_settings()
    monkeypatch.setattr(settings, "retrieval_hybrid_enabled", True)

    monkeypatch.setattr(settings, "retrieval_rerank_enabled", False)
    assert isinstance(get_retriever(), HybridRetriever)

    monkeypatch.setattr(settings, "retrieval_rerank_enabled", True)
    assert isinstance(get_retriever(), RerankingRetriever)

    monkeypatch.setattr(settings, "retrieval_hybrid_enabled", False)
    assert isinstance(get_retriever()._inner, VectorRetriever)
