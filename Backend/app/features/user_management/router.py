import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_user_management_access
from app.features.auth.models import User
from app.features.user_management import service
from app.features.user_management.schemas import (
    ManagedUserCreate,
    ManagedUserRead,
    ManagedUserUpdate,
    PasswordReset,
)

# Delegated account management: separate from /admin so an organisation's IT team can hold it without any other admin
# power. Granting the permission is a super-admin action (`PUT /admin/users/{id}/user-management-access`).
router = APIRouter(prefix="/user-management", tags=["user-management"])


def _read(user: User, manageable: bool) -> ManagedUserRead:
    out = ManagedUserRead.model_validate(user)
    out.manageable = manageable
    return out


@router.get("/users", response_model=list[ManagedUserRead])
async def list_users(actor: User = Depends(require_user_management_access), db: AsyncSession = Depends(get_db)):
    return [_read(u, m) for u, m in await service.list_users(db, actor)]


@router.post("/users", response_model=ManagedUserRead, status_code=201)
async def create_user(payload: ManagedUserCreate, actor: User = Depends(require_user_management_access), db: AsyncSession = Depends(get_db)):
    user = await service.create_user(db, actor, email=payload.email, password=payload.password, full_name=payload.full_name)
    return _read(user, True)


@router.patch("/users/{user_id}", response_model=ManagedUserRead)
async def update_user(user_id: uuid.UUID, payload: ManagedUserUpdate, actor: User = Depends(require_user_management_access), db: AsyncSession = Depends(get_db)):
    user = await service.update_user(db, actor, user_id, email=payload.email, full_name=payload.full_name)
    return _read(user, user.id != actor.id)


@router.post("/users/{user_id}/reset-password", status_code=204)
async def reset_password(user_id: uuid.UUID, payload: PasswordReset, actor: User = Depends(require_user_management_access), db: AsyncSession = Depends(get_db)):
    await service.reset_password(db, actor, user_id, payload.password)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, actor: User = Depends(require_user_management_access), db: AsyncSession = Depends(get_db)):
    await service.delete_user(db, actor, user_id)
