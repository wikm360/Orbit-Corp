from app.features.documents.ingestion.embedder import embed_chunks


class _RecordingProvider:
    def __init__(self):
        self.batch_sizes: list[int] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.batch_sizes.append(len(texts))
        return [[float(len(t))] for t in texts]


async def test_embed_chunks_splits_large_inputs_into_batches_and_keeps_order():
    provider = _RecordingProvider()
    chunks = ["x" * (i + 1) for i in range(150)]

    result = await embed_chunks(provider, chunks)

    assert provider.batch_sizes == [64, 64, 22]
    assert result == [[float(i + 1)] for i in range(150)]


async def test_embed_chunks_with_no_chunks_makes_no_request():
    provider = _RecordingProvider()

    assert await embed_chunks(provider, []) == []
    assert provider.batch_sizes == []
