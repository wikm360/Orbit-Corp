from app.providers.embedding_provider import EmbeddingProvider


async def embed_chunks(provider: EmbeddingProvider, chunks: list[str]) -> list[list[float]]:
    """Thin wrapper kept as its own ingestion step so batching/retry policy for
    embedding calls can evolve independently of the provider interface itself."""
    return await provider.embed(chunks)
