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

    def __init__(self, base_url: str, api_key: str, model: str, dimensions: int):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()
            ordered = sorted(data["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in ordered]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    return BGEM3EmbeddingProvider(
        base_url=settings.embedding_api_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
