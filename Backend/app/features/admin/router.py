import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user_context,
    require_admin,
    require_super_admin,
    UserContext,
)
from app.core.exceptions import ForbiddenError
from app.features.admin import service
from app.features.auth.models import UserRole
from app.features.auth.schemas import UserRead
from app.features.documents.schemas import DocumentRead

# Org-wide oversight only. Team/project creation and membership management
# live under /teams and /projects, with their own per-team/per-project
# permission checks (team leaders can manage their own team/projects without
# being global admins).
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole = UserRole.USER


@router.get("/users", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db)):
    return await service.list_users(db)


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    if payload.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN) and not context.is_super_admin:
        raise ForbiddenError("Only super admins can create admin users")
    return await service.create_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=UserRead,
    dependencies=[Depends(require_super_admin)],
)
async def set_user_role(user_id: uuid.UUID, payload: UserRoleUpdate, db: AsyncSession = Depends(get_db)):
    """Granting ADMIN/SUPER_ADMIN is reserved for super admins, to avoid a
    plain admin escalating themselves or others."""
    return await service.set_user_role(db, user_id, payload.role)


@router.get("/documents", response_model=list[DocumentRead])
async def list_all_documents(db: AsyncSession = Depends(get_db)):
    return await service.list_all_documents(db)
