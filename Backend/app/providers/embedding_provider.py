import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx

from app.core.config import get_settings


class EmbeddingProvider(ABC):
    """Abstract interface every embedding backend must implement.

    Kept separate from callers so swapping BGE-M3 for another model/provider,
    or adding a fallback provider, never touches ingestion or retrieval code.
    """

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, in the same order."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        ...


class BGEM3EmbeddingProvider(EmbeddingProvider):
    """Calls an OpenAI-compatible `/embeddings` endpoint serving BGE-M3.

    This format is used by most self-hosted/third-party BGE-M3 deployments
    (vLLM, Infinity, SiliconFlow, DeepInfra, ...).
    """

    # Rate limits (429) and transient server errors are expected when several
    # workers embed a big batch of documents at once - retried with backoff
    # instead of failing the whole document.
    _MAX_ATTEMPTS = 5
    _RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        dimensions: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._transport = transport

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=60, transport=self._transport) as client:
            for attempt in range(1, self._MAX_ATTEMPTS + 1):
                try:
                    response = await client.post(
                        f"{self._base_url}/embeddings",
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json={"model": self._model, "input": texts},
                    )
                except httpx.TransportError:
                    if attempt == self._MAX_ATTEMPTS:
                        raise
                    await asyncio.sleep(self._backoff(attempt))
                    continue

                if response.status_code in self._RETRYABLE_STATUS and attempt < self._MAX_ATTEMPTS:
                    await asyncio.sleep(self._backoff(attempt, response.headers.get("Retry-After")))
                    continue

                response.raise_for_status()
                data = response.json()
                ordered = sorted(data["data"], key=lambda item: item["index"])
                return [item["embedding"] for item in ordered]
        raise AssertionError("unreachable")  # the loop always returns or raises

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None = None) -> float:
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), 30.0)
        return min(2.0 ** (attempt - 1), 30.0)  # 1s, 2s, 4s, 8s


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    return BGEM3EmbeddingProvider(
        base_url=settings.embedding_api_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
