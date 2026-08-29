import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.features.access_control.models import Team
from app.features.access_control.service import add_user_to_team, get_user_teams
from app.features.auth.models import User
from app.features.documents.models import Document


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def list_users_with_teams(db: AsyncSession) -> list[tuple[User, list[Team]]]:
    users = await list_users(db)
    return [(user, await get_user_teams(db, user.id)) for user in users]


async def create_team(db: AsyncSession, name: str) -> Team:
    existing = await db.execute(select(Team).where(Team.name == name))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A team with this name already exists")
    team = Team(name=name)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


async def list_teams(db: AsyncSession) -> list[Team]:
    result = await db.execute(select(Team).order_by(Team.name))
    return list(result.scalars().all())


async def assign_user_to_team(db: AsyncSession, user_id: uuid.UUID, team_id: uuid.UUID) -> None:
    user = await db.get(User, user_id)
    team = await db.get(Team, team_id)
    if user is None or team is None:
        raise NotFoundError("User or team not found")
    await add_user_to_team(db, user_id, team_id)


async def list_all_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return list(result.scalars().all())
