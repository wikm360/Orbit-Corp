import asyncio
import os
from collections.abc import AsyncGenerator, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import Settings

# The suite drops and recreates the whole schema before every test, so it must
# never share a database with the app. Point it at TEST_DATABASE_URL, or at
# "<dev database>_test" on the same server. This has to happen before
# app.core.database is imported, since that module builds its engine at import.
_configured_url = make_url(os.environ.get("TEST_DATABASE_URL") or Settings().database_url)
_test_url = (
    _configured_url
    if _configured_url.database.endswith("_test")
    else _configured_url.set(database=f"{_configured_url.database}_test")
)
os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)

from app.core import model_registry  # noqa: E402,F401 - registers all models
from app.core.database import Base, async_session_factory, engine, get_db  # noqa: E402
from app.features.agent import engine as agent_engine_module  # noqa: E402
from app.features.agent.tools import document_tools as agent_document_tools  # noqa: E402
from app.features.chat.ws import manager as ws_manager  # noqa: E402
from app.features.memory import service as memory_service  # noqa: E402
from app.main import app  # noqa: E402

# These tests need a real Postgres with the `vector` extension available
# (e.g. `docker compose up -d postgres`) rather than SQLite, since
# document_chunks.embedding uses the pgvector column type.


def _assert_test_database() -> None:
    database = engine.url.database or ""
    if not database.endswith("_test"):
        raise RuntimeError(f"Refusing to reset schema of non-test database {database!r}")


@pytest.fixture(scope="session", autouse=True)
def _create_test_database() -> None:
    async def _create() -> None:
        admin_engine = create_async_engine(
            _test_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
        )
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": _test_url.database},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{_test_url.database}"'))
        await admin_engine.dispose()

    asyncio.run(_create())


@pytest_asyncio.fixture(autouse=True)
async def _reset_schema() -> AsyncGenerator[None, None]:
    _assert_test_database()
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Each test runs in its own event loop; pooled asyncpg/Redis connections
    # can't be reused across loops.
    await engine.dispose()
    await ws_manager._redis.connection_pool.disconnect()


class _StubLLMProvider:
    """Speaks the `StreamEvent` protocol (see `providers/llm_provider.py`):
    plain content deltas, never a tool call - so a test that doesn't script
    its own provider still gets a deterministic, tool-free answer."""

    async def stream_chat(self, messages, tools=None) -> AsyncIterator[dict]:
        for token in ["Hello", ", ", "world!"]:
            yield {"type": "content", "delta": token}


class _StubEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        dim = Settings().embedding_dimensions
        return [[0.0] * dim for _ in texts]


@pytest.fixture(autouse=True)
def _stub_providers(monkeypatch):
    # Keeps the suite offline: no test may reach a real LLM/embedding API.
    monkeypatch.setattr(agent_engine_module, "get_llm_provider", lambda: _StubLLMProvider())
    monkeypatch.setattr(agent_document_tools, "get_embedding_provider", lambda: _StubEmbeddingProvider())
    monkeypatch.setattr(memory_service, "get_embedding_provider", lambda: _StubEmbeddingProvider())


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
