import uuid

import pytest

from app.core.config import Settings
from app.core.security import hash_password
from app.features.auth.models import User, UserRole
from app.features.memory import service as memory_service
from app.features.memory.models import MemoryCategory
from app.features.projects.models import Project
from app.features.access_control.models import Team


class _StubEmbeddingProvider:
    """Deterministic stand-in: embeds each text to a vector derived from its
    length, so semantically similar-length facts end up nearer each other -
    good enough to prove `recall` orders by proximity, without a real model.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        dim = Settings().embedding_dimensions
        vectors = []
        for text in texts:
            value = (len(text) % 50) / 50.0
            vectors.append([value] * dim)
        return vectors


@pytest.fixture(autouse=True)
def _stub_memory_embedding(monkeypatch):
    monkeypatch.setattr(memory_service, "get_embedding_provider", lambda: _StubEmbeddingProvider())


async def _seed_project(db_session) -> Project:
    team = Team(name=f"T-{uuid.uuid4()}")
    db_session.add(team)
    await db_session.flush()

    project = Project(team_id=team.id, name="P")
    db_session.add(project)
    await db_session.flush()
    return project


async def _seed_user(db_session) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        hashed_password=hash_password("supersecret"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_remember_persists_a_project_memory(db_session):
    project = await _seed_project(db_session)
    user = await _seed_user(db_session)

    memory = await memory_service.remember(
        db_session,
        project.id,
        user.id,
        "The API always returns dates in UTC.",
        MemoryCategory.CONVENTION,
    )

    assert memory.id is not None
    assert memory.project_id == project.id
    assert memory.created_by_user_id == user.id
    assert memory.category == MemoryCategory.CONVENTION
    assert memory.is_verified is False
    assert memory.confidence_score == 1.0


async def test_recall_is_scoped_to_the_project(db_session):
    project_a = await _seed_project(db_session)
    project_b = await _seed_project(db_session)
    user = await _seed_user(db_session)

    await memory_service.remember(
        db_session, project_a.id, user.id, "Deploys happen on Fridays.", MemoryCategory.TIMELINE
    )
    await memory_service.remember(
        db_session, project_b.id, user.id, "We use PostgreSQL 16.", MemoryCategory.TECHNICAL_DECISION
    )

    results = await memory_service.recall(db_session, project_a.id, "when do we deploy")

    assert len(results) == 1
    assert results[0].project_id == project_a.id


async def test_recall_filters_by_category(db_session):
    project = await _seed_project(db_session)
    user = await _seed_user(db_session)

    await memory_service.remember(
        db_session, project.id, user.id, "Timelines are tight.", MemoryCategory.TIMELINE
    )
    await memory_service.remember(
        db_session, project.id, user.id, "We use FastAPI.", MemoryCategory.TECHNICAL_DECISION
    )

    results = await memory_service.recall(
        db_session, project.id, "stack", category=MemoryCategory.TECHNICAL_DECISION
    )

    assert len(results) == 1
    assert results[0].category == MemoryCategory.TECHNICAL_DECISION
