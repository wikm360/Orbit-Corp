from app.providers.embedding_provider import EmbeddingProvider

# OpenAI-style embedding APIs reject a request over 2048 inputs or ~300k
# tokens; a large document can produce far more chunks than that.
_BATCH_SIZE = 64


async def embed_chunks(provider: EmbeddingProvider, chunks: list[str]) -> list[list[float]]:
    """Thin wrapper kept as its own ingestion step so batching/retry policy for
    embedding calls can evolve independently of the provider interface itself."""
    embeddings: list[list[float]] = []
    for start in range(0, len(chunks), _BATCH_SIZE):
        embeddings.extend(await provider.embed(chunks[start : start + _BATCH_SIZE]))
    return embeddings
