"""Run the evaluation questions against the ingested scratch database and print hit@k / MRR per retrieval variant.

    EVAL_PG_BASE=... python tools/retrieval_eval/evaluate.py            # variants on the chunks currently in the DB
    EVAL_PG_BASE=... python tools/retrieval_eval/evaluate.py --rerank --rerank-model gpt-4.1-mini
    EVAL_PG_BASE=... python tools/retrieval_eval/evaluate.py --matrix   # chunk size x embedding model (re-chunks and re-embeds)

Metrics (positive questions): hit@k = a relevant chunk is within the top k; MRR = mean 1/rank of the first relevant chunk.
For negative questions the table shows how many returned nothing at the configured similarity threshold.
Embeddings of chunks/questions are cached in the work dir, so repeat runs cost nothing.
"""

import argparse
import asyncio
import copy
import hashlib
import json
import statistics
import uuid

import common  # noqa: F401  (must come first)
from questions import Q
from sqlalchemy import delete, text

from app.core.config import get_settings
from app.core.database import async_session_factory, engine
from app.features.documents.ingestion.chunker import chunk_document_pages
from app.features.documents.ingestion.parser import DocumentPage
from app.features.documents.models import DocumentChunk
from app.features.retrieval import service as retrieval
from app.providers.embedding_provider import BGEM3EmbeddingProvider

SETTINGS = get_settings()
CONVERSATION_ID = uuid.uuid4()
_CACHE: dict[str, dict] = {}


async def embed(model: str, send_dimensions: bool, texts: list[str]) -> list[list[float]]:
    path = common.WORKDIR / f"embeddings_{model}.json"
    cache = _CACHE.setdefault(model, json.loads(path.read_text()) if path.exists() else {})
    provider = BGEM3EmbeddingProvider(
        SETTINGS.embedding_api_base_url, SETTINGS.embedding_api_key, model, SETTINGS.embedding_dimensions,
        send_dimensions=send_dimensions,
    )
    key = lambda t: hashlib.sha1(t.encode()).hexdigest()  # noqa: E731
    todo = [t for t in dict.fromkeys(texts) if key(t) not in cache]
    for start in range(0, len(todo), 48):
        batch = todo[start : start + 48]
        for text_, vector in zip(batch, await provider.embed(batch), strict=True):
            cache[key(text_)] = vector
    path.write_text(json.dumps(cache))
    return [cache[key(t)] for t in texts]


async def search(db, kind: str, query_vector, query: str, threshold: float | None):
    project = common.project_id()
    if kind == "rerank":
        return await retrieval.RerankingRetriever(retrieval.HybridRetriever()).retrieve(
            db, project, CONVERSATION_ID, query_vector, 5, query_text=query, min_similarity=threshold
        )
    if kind == "hybrid":
        return await retrieval.HybridRetriever().retrieve(
            db, project, CONVERSATION_ID, query_vector, 5, query_text=query, min_similarity=threshold
        )
    return await retrieval.VectorRetriever().retrieve(db, project, CONVERSATION_ID, query_vector, 5, min_similarity=threshold)


async def score(db, kind: str, model: str, send_dimensions: bool, threshold: float | None) -> dict:
    vectors = await embed(model, send_dimensions, [q for _, _, q, _ in Q])
    ranks, chars, neg_empty, neg_total = [], [], 0, 0
    for (_, _, query, must), vector in zip(Q, vectors, strict=True):
        results = await search(db, kind, vector, query, threshold)
        if must is None:
            neg_total += 1
            neg_empty += not results
            continue
        ranks.append(next((i + 1 for i, r in enumerate(results) if common.relevant(must, r.content)), None))
        chars.append(sum(len(r.content) for r in results))
    n = len(ranks)
    return {
        "hit@1": sum(r == 1 for r in ranks) / n,
        "hit@3": sum(bool(r and r <= 3) for r in ranks) / n,
        "hit@5": sum(bool(r) for r in ranks) / n,
        "mrr": sum(1 / r for r in ranks if r) / n,
        "chars": statistics.mean(chars),
        "neg_empty": f"{neg_empty}/{neg_total}",
    }


def row(name: str, m: dict) -> str:
    return (f"{name:34} hit@1={m['hit@1']:.2f} hit@3={m['hit@3']:.2f} hit@5={m['hit@5']:.2f} MRR={m['mrr']:.3f} "
            f"avg_chars_top5={m['chars']:.0f} negatives_empty={m['neg_empty']}")


async def variants(model: str, send_dimensions: bool, threshold: float, rerank: bool) -> None:
    experiments = {
        "vector only": ("vector", {}),
        "hybrid (current settings)": ("hybrid", {}),
        "hybrid, no trigram": ("hybrid", {"retrieval_trigram_enabled": False}),
        "hybrid, min_term_hits=1": ("hybrid", {"retrieval_lexical_min_term_hits": 1}),
        "hybrid, rrf_k=20": ("hybrid", {"retrieval_rrf_k": 20}),
        "hybrid, 60 candidates": ("hybrid", {"retrieval_candidates": 60}),
    }
    if rerank:  # one LLM call per question
        experiments["hybrid + LLM re-rank"] = ("rerank", {})
    async with async_session_factory() as db:
        for name, (kind, overrides) in experiments.items():
            settings = copy.copy(SETTINGS)
            for key, value in overrides.items():
                setattr(settings, key, value)
            retrieval.get_settings = lambda s=settings: s
            print(row(name, await score(db, kind, model, send_dimensions, threshold)), flush=True)


async def matrix() -> None:
    async with async_session_factory() as db:
        rows = (await db.execute(text("SELECT id, file_path FROM documents"))).all()
    docs = []
    for document_id, path in rows:
        data = json.loads(open(path + ".reconstructed.json", encoding="utf-8").read())
        docs.append((document_id, [DocumentPage(p["page"], p["text"], metadata=dict(p["metadata"])) for p in data["pages"]]))
    for model, send_dimensions in (("text-embedding-3-small", False), ("text-embedding-3-large", True)):
        for size, overlap in ((500, 50), (1000, 100), (1500, 150)):
            chunks = [(d, i, c) for d, pages in docs for i, c in enumerate(chunk_document_pages(pages, size, overlap))]
            vectors = await embed(model, send_dimensions, [c.content for _, _, c in chunks])
            async with async_session_factory() as db:
                await db.execute(delete(DocumentChunk))
                for (document_id, index, chunk), vector in zip(chunks, vectors, strict=True):
                    db.add(DocumentChunk(document_id=document_id, content=chunk.content, chunk_index=index,
                                         embedding=vector, chunk_metadata=chunk.metadata))
                await db.commit()
                for kind in ("vector", "hybrid"):
                    print(row(f"{model[-5:]} {size}/{overlap} {kind} ({len(chunks)} chunks)",
                              await score(db, kind, model, send_dimensions, None)), flush=True)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", action="store_true", help="re-chunk + re-embed for several sizes and models (replaces the chunks in the scratch DB)")
    parser.add_argument("--model", default=SETTINGS.embedding_model)
    parser.add_argument("--send-dimensions", action="store_true", default=SETTINGS.embedding_send_dimensions)
    parser.add_argument("--rerank", action="store_true", help="also evaluate LLM re-ranking (one LLM call per question)")
    parser.add_argument("--rerank-model", help="model for re-ranking (default: LLM_RERANK_MODEL or LLM_MODEL)")
    parser.add_argument("--threshold", type=float, default=SETTINGS.retrieval_score_threshold)
    args = parser.parse_args()
    if args.rerank_model:
        SETTINGS.llm_rerank_model = args.rerank_model
    if args.matrix:
        await matrix()
    else:
        await variants(args.model, args.send_dimensions, args.threshold, args.rerank)
    await engine.dispose()


asyncio.run(main())
