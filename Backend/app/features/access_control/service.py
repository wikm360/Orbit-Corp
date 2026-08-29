import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.access_control.models import Team, TeamMembership


async def get_user_team_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(TeamMembership.team_id).where(TeamMembership.user_id == user_id)
    )
    return [row[0] for row in result.all()]


async def list_teams(db: AsyncSession) -> list[Team]:
    result = await db.execute(select(Team).order_by(Team.name))
    return list(result.scalars().all())


async def get_user_teams(db: AsyncSession, user_id: uuid.UUID) -> list[Team]:
    result = await db.execute(
        select(Team).join(TeamMembership).where(TeamMembership.user_id == user_id).order_by(Team.name)
    )
    return list(result.scalars().all())


async def add_user_to_team(db: AsyncSession, user_id: uuid.UUID, team_id: uuid.UUID) -> None:
    exists = await db.execute(
        select(TeamMembership).where(
            TeamMembership.user_id == user_id, TeamMembership.team_id == team_id
        )
    )
    if exists.scalar_one_or_none() is not None:
        return
    db.add(TeamMembership(user_id=user_id, team_id=team_id))
    await db.commit()
