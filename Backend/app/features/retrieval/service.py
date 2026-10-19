import asyncio
import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import func, literal, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.text_normalization import words
from app.features.documents.models import Document, DocumentChunk
from app.features.retrieval.access_filter import accessible_documents_filter
from app.providers.llm_provider import LLMProvider, get_rerank_llm_provider

logger = logging.getLogger(__name__)

_MAX_QUERY_TERMS = 16


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_filename: str
    content: str
    chunk_index: int
    # Cosine similarity to the query embedding (NaN-safe callers should not assume it is sortable).
    score: float
    page_number: int | None = None
    # True when full-text / trigram search also found this chunk (so a low `score` does not make it irrelevant).
    lexical_match: bool = False


def query_terms(query: str) -> list[str]:
    """Distinct normalized query words (no stopwords), in order, capped."""
    seen: dict[str, None] = {}
    for word in words(query):
        seen.setdefault(word, None)
    return list(seen)[:_MAX_QUERY_TERMS]


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion: each ranking gives an item 1/(k + rank); scores are summed across rankings."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking):
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + rank + 1)
    return fused


class Retriever(ABC):
    """Abstract retrieval interface (`HybridRetriever` is the default; `VectorRetriever` is the vector-only fallback)."""

    @abstractmethod
    async def retrieve(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        conversation_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
        query_text: str | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        ...


def _columns(distance):
    """Only what a result needs - never the 1536-float embedding or the tsvector, which would be shipped for every candidate."""
    return (
        DocumentChunk.id,
        DocumentChunk.document_id,
        DocumentChunk.content,
        DocumentChunk.chunk_index,
        DocumentChunk.chunk_metadata,
        DocumentChunk.search_text,
        Document.filename,
        distance.label("distance"),
    )


def _to_retrieved(row) -> RetrievedChunk:
    meta = row.chunk_metadata or {}
    return RetrievedChunk(
        chunk_id=str(row.id),
        document_id=str(row.document_id),
        document_filename=row.filename,
        content=row.content,
        chunk_index=row.chunk_index,
        score=1 - row.distance,
        page_number=meta.get("page") or meta.get("page_number"),
    )


def _passes(similarity: float, min_similarity: float | None) -> bool:
    # `not (x < min)` rather than `x >= min`: a NaN similarity (zero vectors) is not rejected, as before.
    return min_similarity is None or not (similarity < min_similarity)


class VectorRetriever(Retriever):
    """pgvector cosine similarity search with access filtering (the pre-hybrid behaviour)."""

    async def retrieve(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        conversation_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
        query_text: str | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(*_columns(distance))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(accessible_documents_filter(project_id, conversation_id))
            .order_by(distance)
            .limit(top_k)
        )
        result = await db.execute(stmt)
        chunks = [_to_retrieved(row) for row in result.all()]
        return [c for c in chunks if _passes(c.score, min_similarity)]


class HybridRetriever(Retriever):
    """Vector + Postgres full-text (+ trigram for short queries), fused with Reciprocal Rank Fusion.

    Why: embeddings blur exact tokens (clause numbers, codes, names, rare terms); full-text finds them exactly; trigram
    forgives typos in short queries. All three run inside the same access filter, so nothing outside the
    conversation's scope can enter through the lexical side either.

    `RetrievedChunk.score` stays the cosine similarity (the number the threshold and the UI know); the fused rank only
    decides the order. A chunk that scores low by vector but was found lexically is kept (`lexical_match`).
    """

    async def retrieve(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        conversation_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
        query_text: str | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        settings = get_settings()
        terms = query_terms(query_text) if query_text else []
        if not terms:
            return await VectorRetriever().retrieve(
                db, project_id, conversation_id, query_embedding, top_k, min_similarity=min_similarity
            )

        limit = max(top_k, settings.retrieval_candidates)
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        access = accessible_documents_filter(project_id, conversation_id)

        def base():
            return (
                select(*_columns(distance))
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(access)
            )

        vector_rows = (await db.execute(base().order_by(distance).limit(limit))).all()

        tsquery = func.to_tsquery(literal_column("'simple'::regconfig"), " | ".join(f"'{t}'" for t in terms))
        fts_rows = (
            await db.execute(
                base()
                .where(DocumentChunk.search_tsv.op("@@")(tsquery))
                .order_by(func.ts_rank_cd(DocumentChunk.search_tsv, tsquery).desc())
                .limit(limit)
            )
        ).all()
        required_hits = min(settings.retrieval_lexical_min_term_hits, len(terms))
        wanted = set(terms)
        fts_rows = [
            row
            for row in fts_rows
            if len(wanted & set(words(row.search_text or row.content))) >= required_hits
        ]

        trigram_rows: list = []
        if settings.retrieval_trigram_enabled and len(terms) <= settings.retrieval_trigram_max_terms:
            phrase = " ".join(terms)
            # Transaction-local, so the threshold cannot leak into other queries on pooled connections.
            await db.execute(
                text("SELECT set_config('pg_trgm.word_similarity_threshold', :v, true)"),
                {"v": str(settings.retrieval_trigram_threshold)},
            )
            trigram_rows = (
                await db.execute(
                    base()
                    .where(literal(phrase).op("<%")(DocumentChunk.search_text))
                    .order_by(func.word_similarity(phrase, DocumentChunk.search_text).desc())
                    .limit(limit)
                )
            ).all()

        by_id: dict[str, RetrievedChunk] = {}
        lexical_ids: set[str] = set()
        for rows in (fts_rows, trigram_rows):
            for row in rows:
                key = str(row.id)
                lexical_ids.add(key)
                by_id.setdefault(key, _to_retrieved(row))
        vector_ranking: list[str] = []
        for row in vector_rows:
            key = str(row.id)
            by_id.setdefault(key, _to_retrieved(row))
            # Weak vector-only hits are dropped before ranking so they cannot occupy top_k slots.
            if key in lexical_ids or _passes(1 - row.distance, min_similarity):
                vector_ranking.append(key)

        fused = reciprocal_rank_fusion(
            [
                vector_ranking,
                [str(row.id) for row in fts_rows],
                [str(row.id) for row in trigram_rows],
            ],
            k=settings.retrieval_rrf_k,
        )
        ordered = sorted(fused, key=lambda key: fused[key], reverse=True)[:top_k]
        results = []
        for key in ordered:
            item = by_id[key]
            item.lexical_match = key in lexical_ids
            results.append(item)
        logger.debug(
            "hybrid retrieval: vector=%d fts=%d trigram=%d -> %d", len(vector_rows), len(fts_rows), len(trigram_rows), len(results)
        )
        return results


_RERANK_PROMPT = (
    "You are a search re-ranker. Question: {query}\n\n"
    "Candidate passages (some may be irrelevant):\n\n{listing}\n\n"
    "Return ONLY a JSON array with the indexes of the passages (at most {top_k}) that contain information needed to "
    "answer the question, best first. Return [] if none of them helps answer it."
)


def parse_rerank_indexes(raw: str, candidate_count: int, top_k: int) -> list[int] | None:
    """Indexes from the model's reply (deduplicated, in range, at most top_k); None when the reply is not a JSON array."""
    match = re.search(r"\[[^\[\]]*\]", raw or "", re.S)
    if match is None:
        return None
    try:
        values = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    indexes: list[int] = []
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < candidate_count and value not in indexes:
            indexes.append(value)
    return indexes[:top_k]


class RerankingRetriever(Retriever):
    """Takes a wider candidate list from `inner` and lets an LLM pick and order the passages that actually answer the query.

    The cosine/lexical stages are good at *finding* the right passage but only moderately good at *ordering* it; reading
    the passages next to the question fixes the order and also drops candidates that merely look similar (an empty answer
    means "nothing here answers this", which the agent can report instead of improvising from loosely related text).
    Any failure (timeout, provider error, unparsable reply) falls back to the inner retriever's own top results.
    """

    def __init__(self, inner: Retriever, provider: LLMProvider | None = None):
        self._inner = inner
        self._provider = provider

    async def retrieve(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        conversation_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
        query_text: str | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        settings = get_settings()
        candidates = await self._inner.retrieve(
            db, project_id, conversation_id, query_embedding,
            max(top_k, settings.retrieval_rerank_candidates), query_text=query_text, min_similarity=min_similarity,
        )
        if not query_text or len(candidates) <= 1:
            return candidates[:top_k]

        try:
            indexes = await asyncio.wait_for(
                self._rank(query_text, candidates, top_k), timeout=settings.retrieval_rerank_timeout_seconds
            )
        except Exception as exc:  # noqa: BLE001 - re-ranking is an improvement, never a reason to fail a search
            logger.warning("Re-ranking failed (%s: %s); using the unranked order", type(exc).__name__, exc)
            return candidates[:top_k]
        if indexes is None:
            logger.warning("Re-ranker reply was not a JSON array; using the unranked order")
            return candidates[:top_k]
        return [candidates[i] for i in indexes]

    async def _rank(self, query: str, candidates: list[RetrievedChunk], top_k: int) -> list[int] | None:
        limit = get_settings().retrieval_rerank_passage_chars
        listing = "\n\n".join(f"[{i}] {chunk.content[:limit]}" for i, chunk in enumerate(candidates))
        prompt = _RERANK_PROMPT.format(query=query, listing=listing, top_k=top_k)
        provider = self._provider or get_rerank_llm_provider()
        reply = ""
        async for event in provider.stream_chat([{"role": "user", "content": prompt}]):
            if event["type"] == "content":
                reply += event["delta"]
        return parse_rerank_indexes(reply, len(candidates), top_k)


def get_retriever() -> Retriever:
    settings = get_settings()
    retriever: Retriever = HybridRetriever() if settings.retrieval_hybrid_enabled else VectorRetriever()
    return RerankingRetriever(retriever) if settings.retrieval_rerank_enabled else retriever
