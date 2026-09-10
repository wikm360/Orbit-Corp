import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.features.access_control.models import Team, TeamMembership, TeamRole
from app.features.auth.models import User


async def get_user_team_roles(db: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, TeamRole]:
    """All teams a user belongs to, mapped to their role within each one."""
    result = await db.execute(
        select(TeamMembership.team_id, TeamMembership.role).where(TeamMembership.user_id == user_id)
    )
    return {team_id: role for team_id, role in result.all()}


async def get_user_team_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(await get_user_team_roles(db, user_id))


async def get_user_led_team_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    roles = await get_user_team_roles(db, user_id)
    return [team_id for team_id, role in roles.items() if role == TeamRole.LEADER]


async def is_team_member(db: AsyncSession, user_id: uuid.UUID, team_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(TeamMembership.id).where(
            TeamMembership.user_id == user_id, TeamMembership.team_id == team_id
        )
    )
    return result.scalar_one_or_none() is not None


async def list_teams(db: AsyncSession) -> list[Team]:
    result = await db.execute(select(Team).order_by(Team.name))
    return list(result.scalars().all())


async def get_team(db: AsyncSession, team_id: uuid.UUID) -> Team:
    team = await db.get(Team, team_id)
    if team is None:
        raise NotFoundError("Team not found")
    return team


async def get_user_teams(db: AsyncSession, user_id: uuid.UUID) -> list[Team]:
    result = await db.execute(
        select(Team).join(TeamMembership).where(TeamMembership.user_id == user_id).order_by(Team.name)
    )
    return list(result.scalars().all())


async def create_team(
    db: AsyncSession, name: str, description: str | None, created_by: uuid.UUID
) -> Team:
    existing = await db.execute(select(Team).where(Team.name == name))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A team with this name already exists")
    team = Team(name=name, description=description, created_by=created_by)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


async def list_team_members(db: AsyncSession, team_id: uuid.UUID) -> list[tuple[User, TeamMembership]]:
    result = await db.execute(
        select(User, TeamMembership)
        .join(TeamMembership, TeamMembership.user_id == User.id)
        .where(TeamMembership.team_id == team_id)
        .order_by(TeamMembership.created_at)
    )
    return [(user, membership) for user, membership in result.all()]


async def add_user_to_team(
    db: AsyncSession,
    user_id: uuid.UUID,
    team_id: uuid.UUID,
    role: TeamRole,
    added_by: uuid.UUID,
) -> TeamMembership:
    user = await db.get(User, user_id)
    team = await db.get(Team, team_id)
    if user is None or team is None:
        raise NotFoundError("User or team not found")

    existing = await db.execute(
        select(TeamMembership).where(
            TeamMembership.user_id == user_id, TeamMembership.team_id == team_id
        )
    )
    membership = existing.scalar_one_or_none()
    if membership is not None:
        membership.role = role
        await db.commit()
        await db.refresh(membership)
        return membership

    membership = TeamMembership(user_id=user_id, team_id=team_id, role=role, added_by=added_by)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


async def remove_user_from_team(db: AsyncSession, user_id: uuid.UUID, team_id: uuid.UUID) -> None:
    result = await db.execute(
        select(TeamMembership).where(
            TeamMembership.user_id == user_id, TeamMembership.team_id == team_id
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise NotFoundError("Membership not found")
    await db.delete(membership)
    await db.commit()
