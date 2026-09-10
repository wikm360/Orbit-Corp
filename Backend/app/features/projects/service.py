import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.features.access_control.service import is_team_member
from app.features.auth.models import User
from app.features.projects.models import Project, ProjectMembership


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


async def list_team_projects(db: AsyncSession, team_id: uuid.UUID) -> list[Project]:
    result = await db.execute(
        select(Project).where(Project.team_id == team_id).order_by(Project.name)
    )
    return list(result.scalars().all())


async def list_user_projects(db: AsyncSession, user_id: uuid.UUID) -> list[Project]:
    result = await db.execute(
        select(Project)
        .join(ProjectMembership, ProjectMembership.project_id == Project.id)
        .where(ProjectMembership.user_id == user_id)
        .order_by(Project.name)
    )
    return list(result.scalars().all())


async def get_user_project_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(ProjectMembership.project_id).where(ProjectMembership.user_id == user_id)
    )
    return [row[0] for row in result.all()]


async def is_project_member(db: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(ProjectMembership.id).where(
            ProjectMembership.user_id == user_id, ProjectMembership.project_id == project_id
        )
    )
    return result.scalar_one_or_none() is not None


async def create_project(
    db: AsyncSession,
    team_id: uuid.UUID,
    name: str,
    description: str | None,
    created_by: uuid.UUID,
) -> Project:
    existing = await db.execute(
        select(Project).where(Project.team_id == team_id, Project.name == name)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A project with this name already exists in this team")

    project = Project(team_id=team_id, name=name, description=description, created_by=created_by)
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # The creator (a team leader or admin) automatically gets access to what they made.
    db.add(ProjectMembership(project_id=project.id, user_id=created_by, added_by=created_by))
    await db.commit()
    return project


async def list_project_members(
    db: AsyncSession, project_id: uuid.UUID
) -> list[tuple[User, ProjectMembership]]:
    result = await db.execute(
        select(User, ProjectMembership)
        .join(ProjectMembership, ProjectMembership.user_id == User.id)
        .where(ProjectMembership.project_id == project_id)
        .order_by(ProjectMembership.created_at)
    )
    return [(user, membership) for user, membership in result.all()]


async def add_project_member(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, added_by: uuid.UUID
) -> ProjectMembership:
    project = await get_project(db, project_id)
    if not await is_team_member(db, user_id, project.team_id):
        raise BadRequestError("The user must belong to the project's team before joining the project")

    existing = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id, ProjectMembership.user_id == user_id
        )
    )
    membership = existing.scalar_one_or_none()
    if membership is not None:
        return membership

    membership = ProjectMembership(project_id=project_id, user_id=user_id, added_by=added_by)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


async def remove_project_member(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id, ProjectMembership.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise NotFoundError("Membership not found")
    await db.delete(membership)
    await db.commit()
