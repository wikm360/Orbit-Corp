import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.features.memory.models import MemoryCategory, ProjectMemory
from app.providers.embedding_provider import get_embedding_provider


async def remember(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID | None,
    fact_text: str,
    category: MemoryCategory,
) -> ProjectMemory:
    embedding_provider = get_embedding_provider()
    [embedding] = await embedding_provider.embed([fact_text])

    memory = ProjectMemory(
        project_id=project_id,
        created_by_user_id=user_id,
        fact_text=fact_text,
        category=category,
        embedding=embedding,
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


async def recall(
    db: AsyncSession,
    project_id: uuid.UUID,
    query: str,
    category: MemoryCategory | None = None,
    top_k: int = 5,
) -> list[ProjectMemory]:
    embedding_provider = get_embedding_provider()
    [query_embedding] = await embedding_provider.embed([query])

    distance = ProjectMemory.embedding.cosine_distance(query_embedding)
    stmt = select(ProjectMemory).where(ProjectMemory.project_id == project_id)
    if category is not None:
        stmt = stmt.where(ProjectMemory.category == category)
    stmt = stmt.order_by(distance).limit(top_k)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_project_memories(db: AsyncSession, project_id: uuid.UUID) -> list[ProjectMemory]:
    result = await db.execute(
        select(ProjectMemory)
        .where(ProjectMemory.project_id == project_id)
        .order_by(ProjectMemory.created_at.desc())
    )
    return list(result.scalars().all())


async def get_memory(db: AsyncSession, memory_id: uuid.UUID) -> ProjectMemory:
    memory = await db.get(ProjectMemory, memory_id)
    if memory is None:
        raise NotFoundError("Memory not found")
    return memory


async def update_memory(
    db: AsyncSession,
    memory: ProjectMemory,
    *,
    fact_text: str | None,
    category: MemoryCategory | None,
    is_verified: bool | None,
) -> ProjectMemory:
    if fact_text is not None and fact_text != memory.fact_text:
        # The embedding is derived from fact_text - stale otherwise, and
        # `recall`'s semantic search would keep matching on the old wording.
        embedding_provider = get_embedding_provider()
        [embedding] = await embedding_provider.embed([fact_text])
        memory.fact_text = fact_text
        memory.embedding = embedding
    if category is not None:
        memory.category = category
    if is_verified is not None:
        memory.is_verified = is_verified

    await db.commit()
    await db.refresh(memory)
    return memory


async def delete_memory(db: AsyncSession, memory_id: uuid.UUID) -> None:
    memory = await get_memory(db, memory_id)
    await db.delete(memory)
    await db.commit()
