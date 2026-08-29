from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, populated from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Organization RAG Assistant"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/org_rag"
    )

    # Redis / RQ
    redis_url: str = "redis://localhost:6379/0"
    ingestion_queue_name: str = "ingestion"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # File storage
    upload_dir: str = "./data/uploads"
    max_upload_size_mb: int = 50

    # Embedding provider (BGE-M3 via OpenAI-compatible /v1/embeddings endpoint)
    embedding_api_base_url: str = "https://api.example.com/v1"
    embedding_api_key: str = ""
    embedding_model: str = "bge-m3"
    embedding_dimensions: int = 1024

    # LLM provider (OpenAI-compatible chat completions endpoint)
    llm_api_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    # Set true for reasoning models (e.g. Qwen3.x) that otherwise leak
    # <thought>/<details> chain-of-thought into the streamed content itself.
    # Leave false for real OpenAI models, which don't recognize this param.
    llm_disable_thinking: bool = False
    # Belt-and-suspenders for the same issue: `enable_thinking` isn't always
    # honored, so these tag names (without angle brackets) are stripped out
    # of the streamed content client-side, block and all. Empty by default.
    llm_strip_content_tags: list[str] = []

    # Chunking
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 50

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.3


@lru_cache
def get_settings() -> Settings:
    return Settings()
