import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.features.admin import service
from app.features.auth.schemas import UserRead
from app.features.documents.schemas import DocumentRead

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class TeamCreate(BaseModel):
    name: str


class TeamRead(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class TeamMembershipCreate(BaseModel):
    user_id: uuid.UUID
    team_id: uuid.UUID


class UserWithTeamsRead(UserRead):
    teams: list[TeamRead]


@router.get("/users", response_model=list[UserWithTeamsRead])
async def list_users(db: AsyncSession = Depends(get_db)):
    rows = await service.list_users_with_teams(db)
    return [
        UserWithTeamsRead(**UserRead.model_validate(user).model_dump(), teams=teams)
        for user, teams in rows
    ]


@router.get("/teams", response_model=list[TeamRead])
async def list_teams(db: AsyncSession = Depends(get_db)):
    return await service.list_teams(db)


@router.post("/teams", response_model=TeamRead)
async def create_team(payload: TeamCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_team(db, payload.name)


@router.post("/team-memberships", status_code=204)
async def assign_user_to_team(payload: TeamMembershipCreate, db: AsyncSession = Depends(get_db)):
    await service.assign_user_to_team(db, payload.user_id, payload.team_id)


@router.get("/documents", response_model=list[DocumentRead])
async def list_all_documents(db: AsyncSession = Depends(get_db)):
    return await service.list_all_documents(db)
