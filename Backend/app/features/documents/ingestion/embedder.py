import asyncio
import contextlib

from app.core.config import get_settings
from app.providers.embedding_provider import EmbeddingProvider

# OpenAI-style embedding APIs reject a request over 2048 inputs or ~300k
# tokens; a large document can produce far more chunks than that.
_BATCH_SIZE = 64


async def embed_chunks(
    provider: EmbeddingProvider, chunks: list[str], concurrency: int | None = None
) -> list[list[float]]:
    """Thin wrapper kept as its own ingestion step so batching/retry policy for
    embedding calls can evolve independently of the provider interface itself.

    Batches are sent concurrently (at most `concurrency` in flight; total load =
    WORKER_REPLICAS x this). `gather` returns results in input order, so the
    vectors still line up with `chunks`."""
    if concurrency is None:
        concurrency = get_settings().embedding_concurrency
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _embed_batch(batch: list[str]) -> list[list[float]]:
        async with semaphore:
            return await provider.embed(batch)

    # One shared HTTP client per document when the provider supports it (stub/other providers just skip this).
    session = getattr(provider, "session", None)
    async with session() if session is not None else contextlib.nullcontext():
        batches = await asyncio.gather(
            *(_embed_batch(chunks[start : start + _BATCH_SIZE]) for start in range(0, len(chunks), _BATCH_SIZE))
        )
    return [vector for batch in batches for vector in batch]
