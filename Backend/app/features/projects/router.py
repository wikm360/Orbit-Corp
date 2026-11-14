import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    UserContext,
    get_current_user_context,
    forbid_self_grant,
    require_project_access,
    require_project_membership_manager,
    require_team_workspace_manager,
)
from app.core.exceptions import ForbiddenError, NotFoundError
from app.features.auth.models import User
from app.features.auth.schemas import UserRead
from app.features.projects import service
from app.features.projects.models import Project
from app.features.projects.permissions import PROJECT_PERMISSIONS

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
    # What the caller may do here: everything for admins/the team's leader, else the delegated permissions.
    my_permissions: list[str] = []


class ProjectMemberRead(BaseModel):
    user: UserRead
    permissions: list[str] = []


class MemberPermissionsUpdate(BaseModel):
    permissions: list[str]


def _project_read(project: Project, context: UserContext) -> ProjectRead:
    effective = context.project_permission_set(project.id, project.team_id)
    return ProjectRead(
        id=project.id, team_id=project.team_id, name=project.name, description=project.description,
        my_permissions=[p for p in PROJECT_PERMISSIONS if p in effective],
    )


class ProjectMemberAdd(BaseModel):
    user_id: uuid.UUID


@router.post("/teams/{team_id}/projects", response_model=ProjectRead)
async def create_project(
    team_id: uuid.UUID,
    payload: ProjectCreate,
    context: UserContext = Depends(require_team_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    project = await service.create_project(db, team_id, payload.name, payload.description, context.id, add_creator=context.leads_team(team_id))
    return _project_read(project, context)


@router.get("/teams/{team_id}/projects", response_model=list[ProjectRead])
async def list_team_projects(
    team_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    if team_id not in context.team_ids and not context.manages_workspace:
        raise ForbiddenError("You are not a member of this team")
    all_projects = await service.list_team_projects(db, team_id)
    if context.can_manage_team(team_id):
        return [_project_read(p, context) for p in all_projects]
    # Regular team members only see the projects they've actually been added to.
    return [_project_read(p, context) for p in all_projects if p.id in context.project_ids]


@router.get("/projects/mine", response_model=list[ProjectRead])
async def list_my_projects(
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return [_project_read(p, context) for p in await service.list_user_projects(db, context.id)]


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(
    project: Project = Depends(require_project_access),
    context: UserContext = Depends(get_current_user_context),
):
    return _project_read(project, context)


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberRead])
async def list_project_members(
    project_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    # Members/leaders/admins as before, plus delegated workspace managers (the list is metadata, not content).
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    if not (context.is_project_member(project.id) or context.can_manage_team(project.team_id)):
        raise ForbiddenError("You are not a member of this project")
    rows = await service.list_project_members(db, project.id)
    return [ProjectMemberRead(user=UserRead.model_validate(user), permissions=list(membership.permissions or [])) for user, membership in rows]


@router.post("/projects/{project_id}/members", status_code=204)
async def add_project_member(
    payload: ProjectMemberAdd,
    context: UserContext = Depends(get_current_user_context),
    project: Project = Depends(require_project_membership_manager),
    db: AsyncSession = Depends(get_db),
):
    forbid_self_grant(context, project.team_id, payload.user_id)
    await service.add_project_member(db, project.id, payload.user_id, context.id)


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
async def remove_project_member(
    user_id: uuid.UUID,
    project: Project = Depends(require_project_membership_manager),
    db: AsyncSession = Depends(get_db),
):
    await service.remove_project_member(db, project.id, user_id)


@router.get("/project-permissions", response_model=list[str])
async def list_project_permissions(_: UserContext = Depends(get_current_user_context)):
    """The delegable permission names."""
    return list(PROJECT_PERMISSIONS)


@router.put("/projects/{project_id}/members/{user_id}/permissions", response_model=ProjectMemberRead)
async def set_member_permissions(
    user_id: uuid.UUID,
    payload: MemberPermissionsUpdate,
    context: UserContext = Depends(get_current_user_context),
    project: Project = Depends(require_project_membership_manager),
    db: AsyncSession = Depends(get_db),
):
    """Team leader / admin / delegated workspace manager only; a project member can never raise their own access.
    Replaces the member's permission set in this project."""
    forbid_self_grant(context, project.team_id, user_id)
    membership = await service.set_member_permissions(db, project.id, user_id, payload.permissions)
    user = await db.get(User, user_id)
    return ProjectMemberRead(user=UserRead.model_validate(user), permissions=list(membership.permissions))
