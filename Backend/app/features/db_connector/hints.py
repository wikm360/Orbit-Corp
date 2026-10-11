"""Schema-hint corpus: load from `sql/rahkaran/hints/out`, ingest into Postgres (embeddings via the project's embedding provider),
and retrieve the most useful chunks for a question with hybrid search (pgvector cosine + BM25, fused by reciprocal rank)."""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.features.db_connector.lexical import Bm25Index
from app.features.db_connector.models import SchemaHint
from app.providers.embedding_provider import get_embedding_provider

logger = logging.getLogger(__name__)

HINTS_DIR = Path(__file__).resolve().parents[3] / "sql" / "rahkaran" / "hints" / "out"
_EMBED_BATCH = 32
_CACHE_TTL_SECONDS = 300
_RRF_K = 60
# Max chunks of each kind in one prompt (view parts of a retrieved view are appended on top of these caps).
_KIND_CAPS = {"view": 4, "example": 2, "note": 2, "glossary": 2}
_MAX_PROMPT_CHARS = 22000


@dataclass
class Hint:
    key: str
    kind: str
    title: str
    content: str
    views: list[str]
    keywords: list[str]


def load_core_prompt() -> str:
    return (HINTS_DIR / "core_prompt.md").read_text(encoding="utf-8")


def load_corpus(path: Path | None = None) -> list[dict]:
    path = path or HINTS_DIR / "hints.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _hash(chunk: dict, model: str) -> str:
    return hashlib.sha256(f"{model}\n{chunk['title']}\n{chunk['text']}".encode()).hexdigest()


async def ingest_hints(db: AsyncSession, corpus: list[dict] | None = None) -> dict:
    """Upsert the corpus. Unchanged chunks keep their embedding; changed/new ones are embedded; chunks missing from the corpus are
    deleted. If the embedding API is unavailable the chunks are stored without a vector (lexical retrieval still works)."""
    settings = get_settings()
    corpus = corpus if corpus is not None else load_corpus()
    existing = {h.hint_key: h for h in (await db.execute(select(SchemaHint))).scalars().all()}
    stats = {"total": len(corpus), "unchanged": 0, "embedded": 0, "stored_without_embedding": 0, "deleted": 0}

    to_embed: list[tuple[SchemaHint, str]] = []
    for chunk in corpus:
        digest = _hash(chunk, settings.embedding_model)
        row = existing.get(chunk["id"])
        if row is None:
            row = SchemaHint(hint_key=chunk["id"], kind=chunk["kind"], title=chunk["title"], content=chunk["text"],
                             views=chunk.get("views", []), keywords=chunk.get("keywords", []), content_hash=digest)
            db.add(row)
        elif row.content_hash == digest and row.embedding is not None:
            stats["unchanged"] += 1
            continue
        else:
            row.kind, row.title, row.content = chunk["kind"], chunk["title"], chunk["text"]
            row.views, row.keywords, row.content_hash = chunk.get("views", []), chunk.get("keywords", []), digest
            row.embedding, row.embedding_model = None, None
        to_embed.append((row, chunk["text"]))

    provider = get_embedding_provider()
    for i in range(0, len(to_embed), _EMBED_BATCH):
        batch = to_embed[i : i + _EMBED_BATCH]
        try:
            vectors = await provider.embed([text for _, text in batch])
        except Exception as exc:
            logger.warning("Embedding unavailable, storing %d hints without vectors: %s", len(batch), exc)
            stats["stored_without_embedding"] += len(batch)
            continue
        for (row, _), vector in zip(batch, vectors):
            row.embedding, row.embedding_model = vector, settings.embedding_model
            stats["embedded"] += 1

    keep = {c["id"] for c in corpus}
    stale = [k for k in existing if k not in keep]
    if stale:
        await db.execute(delete(SchemaHint).where(SchemaHint.hint_key.in_(stale)))
        stats["deleted"] = len(stale)
    await db.commit()
    invalidate_cache()
    return stats


# ---------------------------------------------------------------- retrieval

_cache: tuple[float, list[Hint], Bm25Index] | None = None


def invalidate_cache() -> None:
    global _cache
    _cache = None


def _index(hints: list[Hint]) -> Bm25Index:
    return Bm25Index([f"{h.title} {h.content}" for h in hints], [f"{h.title} {' '.join(h.keywords)}" for h in hints])


async def _load_hints(db: AsyncSession) -> tuple[list[Hint], Bm25Index]:
    global _cache
    now = time.monotonic()
    if _cache and now - _cache[0] < _CACHE_TTL_SECONDS:
        return _cache[1], _cache[2]
    rows = (await db.execute(select(SchemaHint.hint_key, SchemaHint.kind, SchemaHint.title, SchemaHint.content,
                                    SchemaHint.views, SchemaHint.keywords).order_by(SchemaHint.hint_key))).all()
    if rows:
        hints = [Hint(r[0], r[1], r[2], r[3], list(r[4] or []), list(r[5] or [])) for r in rows]
    else:  # not ingested yet: fall back to the file so the connector still works (lexical only)
        logger.warning("schema_hints is empty - using the hint file directly (run the ingest to enable vector search)")
        hints = [Hint(c["id"], c["kind"], c["title"], c["text"], c.get("views", []), c.get("keywords", [])) for c in load_corpus()]
    index = _index(hints)
    _cache = (now, hints, index)
    return hints, index


_EMBED_CACHE_MAX = 256
_EMBED_CACHE_TTL_SECONDS = 3600
_embed_cache: dict[str, tuple[float, list[float]]] = {}


async def _question_embedding(question: str) -> list[float]:
    """Embedding of a question, cached for an hour: repeated or retried questions skip the ~6 s embedding API round trip."""
    key = " ".join(question.split())
    now = time.monotonic()
    cached = _embed_cache.get(key)
    if cached and now - cached[0] < _EMBED_CACHE_TTL_SECONDS:
        return cached[1]
    [embedding] = await get_embedding_provider().embed([question])
    if len(_embed_cache) >= _EMBED_CACHE_MAX:
        _embed_cache.pop(next(iter(_embed_cache)))
    _embed_cache[key] = (now, embedding)
    return embedding


async def _vector_ranking(db: AsyncSession, question: str, limit: int) -> list[str]:
    try:
        embedding = await _question_embedding(question)
    except Exception as exc:
        logger.warning("Question embedding failed, using lexical retrieval only: %s", exc)
        return []
    distance = SchemaHint.embedding.cosine_distance(embedding)
    result = await db.execute(select(SchemaHint.hint_key).where(SchemaHint.embedding.is_not(None)).order_by(distance).limit(limit))
    return [r[0] for r in result.all()]


@dataclass
class RetrievedHints:
    keys: list[str]
    blocks: list[str]  # ready-to-insert text blocks, most relevant first


def _view_parts(hints: list[Hint], key: str) -> list[Hint]:
    parts = key.rsplit(":", 1)[0] + ":"
    return [h for h in hints if h.key.startswith(parts) and h.key != key]


async def retrieve_hints(db: AsyncSession, question: str, top_k: int | None = None) -> RetrievedHints:
    top_k = top_k or get_settings().rahkaran_hints_top_k
    hints, index = await _load_hints(db)
    by_key = {h.key: h for h in hints}

    lexical = [hints[i].key for i in index.top(question, 30)]
    vector = await _vector_ranking(db, question, 30)
    fused: dict[str, float] = {}
    for ranking in (lexical, vector):
        for rank, key in enumerate(ranking):
            fused[key] = fused.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
    ordered = [k for k, _ in sorted(fused.items(), key=lambda kv: kv[1], reverse=True) if k in by_key]

    chosen: list[Hint] = []
    counts: dict[str, int] = {}
    for key in ordered:
        h = by_key[key]
        if counts.get(h.kind, 0) >= _KIND_CAPS.get(h.kind, 2) or len(chosen) >= top_k:
            continue
        chosen.append(h)
        counts[h.kind] = counts.get(h.kind, 0) + 1

    # A view's column list may be split in several chunks: give the model the whole list for every selected view.
    seen = {h.key for h in chosen}
    extra: list[Hint] = []
    for h in chosen:
        if h.kind == "view":
            for part in _view_parts(hints, h.key):
                if part.key not in seen:
                    seen.add(part.key)
                    extra.append(part)
    selected = chosen + extra

    blocks, keys, total = [], [], 0
    for h in selected:
        if total + len(h.content) > _MAX_PROMPT_CHARS and blocks:
            break
        blocks.append(h.content)
        keys.append(h.key)
        total += len(h.content)
    return RetrievedHints(keys=keys, blocks=blocks)
