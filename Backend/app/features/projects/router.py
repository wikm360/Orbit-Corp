import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    UserContext,
    get_current_user_context,
    require_project_access,
    require_project_manager,
    require_team_manager,
)
from app.core.exceptions import ForbiddenError
from app.features.auth.schemas import UserRead
from app.features.projects import service
from app.features.projects.models import Project

router = APIRouter(tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    name: str
    description: str | None


class ProjectMemberRead(BaseModel):
    user: UserRead


class ProjectMemberAdd(BaseModel):
    user_id: uuid.UUID


@router.post("/teams/{team_id}/projects", response_model=ProjectRead)
async def create_project(
    team_id: uuid.UUID,
    payload: ProjectCreate,
    context: UserContext = Depends(require_team_manager),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_project(db, team_id, payload.name, payload.description, context.id)


@router.get("/teams/{team_id}/projects", response_model=list[ProjectRead])
async def list_team_projects(
    team_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    if team_id not in context.team_ids and not context.is_admin:
        raise ForbiddenError("You are not a member of this team")
    all_projects = await service.list_team_projects(db, team_id)
    if context.is_admin or team_id in context.led_team_ids:
        return all_projects
    # Regular team members only see the projects they've actually been added to.
    return [p for p in all_projects if p.id in context.project_ids]


@router.get("/projects/mine", response_model=list[ProjectRead])
async def list_my_projects(
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_user_projects(db, context.id)


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(project: Project = Depends(require_project_access)):
    return project


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberRead])
async def list_project_members(
    project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_project_members(db, project.id)
    return [ProjectMemberRead(user=UserRead.model_validate(user)) for user, _membership in rows]


@router.post("/projects/{project_id}/members", status_code=204)
async def add_project_member(
    payload: ProjectMemberAdd,
    context: UserContext = Depends(get_current_user_context),
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    await service.add_project_member(db, project.id, payload.user_id, context.id)


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
async def remove_project_member(
    user_id: uuid.UUID,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    await service.remove_project_member(db, project.id, user_id)
