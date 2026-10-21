import json
from functools import lru_cache
from typing import Annotated, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, populated from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Organization RAG Assistant"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Structured HTTP traffic logs written to the backend CLI. JSON bodies are
    # included up to the limit; credentials and token-like fields are redacted.
    request_logging_enabled: bool = True
    request_log_body_limit_bytes: int = 65_536

    # CORS
    # `NoDecode` stops pydantic-settings from JSON-decoding this env var
    # itself before our validator runs — without it, any value that isn't
    # valid JSON (e.g. a plain "http://localhost:3000" or a comma-separated
    # list) crashes at startup instead of reaching `_parse_str_list` below.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://185.58.243.123:3000",
        "http://185.58.243.123",
        "http://45.95.65.134:3000",
        "http://45.95.65.134",
    ]

    @field_validator("cors_origins", "llm_strip_content_tags", mode="before")
    @classmethod
    def _parse_str_list(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

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
    # Short-lived: a leaked access token stops working on its own soon.
    access_token_expire_minutes: int = 30
    # Long-lived: refreshed silently by the client, rotated on every use.
    refresh_token_expire_days: int = 30
    # Public sign-ups: when false, only the first user (super admin) can self-register;
    # further users must be added by an admin.
    allow_public_registration: bool = True

    # File storage
    upload_dir: str = "./data/uploads"
    max_upload_size_mb: int = 50
    # Cap on files per batch-upload request (clients send bigger sets in several requests).
    max_batch_upload_files: int = 20

    # Embedding provider (BGE-M3 via OpenAI-compatible /v1/embeddings endpoint)
    embedding_api_base_url: str = "https://api.example.com/v1"
    embedding_api_key: str = ""
    embedding_model: str = "bge-m3"
    embedding_dimensions: int = 1536
    # Send `dimensions` with every /embeddings request (needed to use text-embedding-3-large at 1536 dims).
    embedding_send_dimensions: bool = False
    # Embedding batches in flight at once per document (total load = WORKER_REPLICAS x this); lower it on 429s.
    embedding_concurrency: int = 4

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
    llm_strip_content_tags: Annotated[list[str], NoDecode] = []
    # Dedicated vision-capable model for OCR and image analysis (falls back to llm_model if None)
    llm_vision_model: str | None = None
    # Dedicated model for writing SQL for the accounting-database connector (falls back to llm_model if None)
    llm_sql_model: str | None = None

    # Ingestion OCR
    ocr_enabled: bool = True
    ocr_max_images_per_doc: int = 50
    ocr_min_image_dimension: int = 60
    # PDF pages whose text layer is unusable (visual-order Persian presentation forms, or symbol garbage) are rendered and
    # OCR'd instead of trusting the layer; capped per document because it is one vision call per page.
    ocr_replace_bad_text_layer: bool = True
    ocr_max_replaced_pages: int = 300
    # Pages OCR'd at the same time inside one document (each call takes 10-30 s). Measured: 12 concurrent pages were 3.2x
    # faster than 4 with no failures. The real load is WORKER_REPLICAS x this value, so lower it if the provider rate-limits (429).
    ocr_concurrency: int = 12
    # Processes used to parse the pages of one PDF (decoding scanned images is CPU-bound). 1 = single process.
    pdf_parse_workers: int = 4
    # DPI used by pdftoppm when rendering PDF pages for OCR (200 DPI ensures crisp small numbers in tables).
    pdf_render_dpi: int = 200
    # Max dimension (width or height) to resize images before sending to Vision OCR (2560 preserves fine tabular details).
    ocr_max_image_dimension: int = 2560
    # JPEG quality for Vision OCR image optimization (95 prevents DCT quantization artifacts around small numbers).
    ocr_jpeg_quality: int = 95
    # Output budget of one vision-OCR call. A dense table page needs ~2.5-3k tokens, so the old 2048 truncated it.
    # Keep it generous but use a non-reasoning model: reasoning models spend this budget on thinking and return no text.
    ocr_max_tokens: int = 6000
    # RQ job timeout for one document (OCR of a long scanned PDF is slow).
    ingestion_job_timeout_seconds: int = 3600

    # Rahkaran accounting-database connector (read-only SQL Server, schema `ai`).
    # Off by default: when enabled the agent gets the `ask_accounting_db` tool.
    rahkaran_db_enabled: bool = False
    rahkaran_db_host: str = "mssql"
    rahkaran_db_port: int = 1433
    rahkaran_db_name: str = "MehvarGostar"
    rahkaran_db_user: str = "rahkaran_ai_reader"
    rahkaran_db_password: str = ""
    rahkaran_db_query_timeout_seconds: int = 60
    # Hard cap of rows read from SQL Server per query (SET ROWCOUNT), and how many rows are shown to the model.
    rahkaran_db_max_rows: int = 500
    rahkaran_db_rows_to_model: int = 60
    # SQL generation: attempts (initial + repairs after a validation/execution error) and hints retrieved per question.
    rahkaran_sql_max_attempts: int = 3
    rahkaran_hints_top_k: int = 8
    # Rows of a result stored on the chat message for display (the model sees rahkaran_db_rows_to_model); downloads re-run the SQL up to the export cap.
    rahkaran_artifact_max_rows: int = 100
    rahkaran_export_max_rows: int = 5000

    # Chunking
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 50

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.3
    # search_knowledge_base widens the top chunks to their full pages ("small-to-big"); this caps the page text returned per
    # search. Hits beyond the budget fall back to their chunk text. 0 disables the widening.
    search_page_expansion_max_tokens: int = 6000
    # Hybrid document retrieval: vector + Postgres full-text (+ trigram for short queries) fused with Reciprocal Rank Fusion.
    # Off = the previous vector-only behaviour.
    retrieval_hybrid_enabled: bool = True
    # Candidates taken from each ranking before fusion.
    retrieval_candidates: int = 30
    retrieval_rrf_k: int = 60
    # A full-text candidate only counts as a lexical match if it contains at least this many distinct query words
    # (capped by the number of words in the query), so one common word cannot drag in unrelated chunks.
    retrieval_lexical_min_term_hits: int = 2
    retrieval_trigram_enabled: bool = True
    # Trigram only runs for short, keyword-like queries (long questions match nothing by trigram similarity).
    retrieval_trigram_max_terms: int = 3
    retrieval_trigram_threshold: float = 0.65
    # LLM re-ranking of the hybrid candidates (one extra, short LLM call per search). Measured on the evaluation corpus:
    # hit@1 0.65 -> 0.85, hit@5 0.89 -> 0.93-0.95, and questions with no answer return nothing. Off by default.
    retrieval_rerank_enabled: bool = False
    # Falls back to `llm_model` when unset; a small fast model (e.g. gpt-4.1-mini) is as good as a big one for this.
    llm_rerank_model: str | None = None
    retrieval_rerank_candidates: int = 20
    retrieval_rerank_passage_chars: int = 600
    retrieval_rerank_timeout_seconds: int = 30

    # Group chat: prefix that triggers an AI reply in a project group chat
    # (case-insensitive). Personal chats always reply, no trigger needed.
    ai_trigger_token: str = "@bot"


@lru_cache
def get_settings() -> Settings:
    return Settings()
