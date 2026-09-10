import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context, require_admin
from app.core.exceptions import ForbiddenError
from app.features.access_control import service
from app.features.access_control.models import TeamRole
from app.features.auth.schemas import UserRead

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str
    description: str | None = None


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None


class TeamMembershipRead(BaseModel):
    user: UserRead
    role: TeamRole


class TeamMembershipUpsert(BaseModel):
    user_id: uuid.UUID
    role: TeamRole = TeamRole.MEMBER


@router.post("", response_model=TeamRead, dependencies=[Depends(require_admin)])
async def create_team(
    payload: TeamCreate,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_team(db, payload.name, payload.description, context.id)


@router.get("", response_model=list[TeamRead], dependencies=[Depends(require_admin)])
async def list_all_teams(db: AsyncSession = Depends(get_db)):
    return await service.list_teams(db)


@router.get("/mine", response_model=list[TeamRead])
async def list_my_teams(
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_user_teams(db, context.id)


@router.get("/{team_id}/members", response_model=list[TeamMembershipRead])
async def list_team_members(
    team_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    if team_id not in context.team_ids and not context.is_admin:
        raise ForbiddenError("You are not a member of this team")
    rows = await service.list_team_members(db, team_id)
    return [
        TeamMembershipRead(user=UserRead.model_validate(user), role=membership.role)
        for user, membership in rows
    ]


@router.post("/{team_id}/members", status_code=204)
async def add_team_member(
    team_id: uuid.UUID,
    payload: TeamMembershipUpsert,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    # Appointing a leader is reserved for org admins; a leader may only add
    # or manage plain members of their own team.
    if payload.role == TeamRole.LEADER and not context.is_admin:
        raise ForbiddenError("Only an admin can appoint a team leader")
    if not context.leads_team(team_id):
        raise ForbiddenError("Team leader or admin privileges required")
    await service.add_user_to_team(db, payload.user_id, team_id, payload.role, context.id)


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    if not context.leads_team(team_id):
        raise ForbiddenError("Team leader or admin privileges required")
    roles = await service.get_user_team_roles(db, user_id)
    if roles.get(team_id) == TeamRole.LEADER and not context.is_admin:
        raise ForbiddenError("Only an admin can remove a team leader")
    await service.remove_user_from_team(db, user_id, team_id)
