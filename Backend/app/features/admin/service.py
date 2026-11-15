import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
)
from app.features.auth.models import RefreshToken, User, UserRole
from app.features.auth.schemas import TokenResponse
from app.features.auth.service import _issue_tokens
from app.features.documents.models import Document

logger = logging.getLogger(__name__)


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    role: UserRole = UserRole.USER,
    accounting_access_granted_by: uuid.UUID | None = None,
) -> User:
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("A user with this email already exists")
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        accounting_access=accounting_access_granted_by is not None,
        accounting_access_granted_by=accounting_access_granted_by,
        accounting_access_granted_at=datetime.now(timezone.utc) if accounting_access_granted_by is not None else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def set_user_role(db: AsyncSession, user_id: uuid.UUID, role: UserRole) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def set_accounting_access(
    db: AsyncSession, user_id: uuid.UUID, *, enabled: bool, granted_by: uuid.UUID
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.role == UserRole.SUPER_ADMIN:
        raise BadRequestError("Super admins always have accounting access; it cannot be changed")
    if user.accounting_access != enabled:
        user.accounting_access = enabled
        user.accounting_access_granted_by = granted_by if enabled else None
        user.accounting_access_granted_at = datetime.now(timezone.utc) if enabled else None
        await db.commit()
        await db.refresh(user)
        logger.info("Accounting access %s for user %s by %s", "granted" if enabled else "revoked", user.id, granted_by)
    return user


async def set_workspace_access(
    db: AsyncSession, user_id: uuid.UUID, *, enabled: bool, granted_by: uuid.UUID
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
        raise BadRequestError("Admins always have workspace access; it cannot be changed")
    if user.workspace_access != enabled:
        user.workspace_access = enabled
        user.workspace_access_granted_by = granted_by if enabled else None
        user.workspace_access_granted_at = datetime.now(timezone.utc) if enabled else None
        await db.commit()
        await db.refresh(user)
        logger.info("Workspace access %s for user %s by %s", "granted" if enabled else "revoked", user.id, granted_by)
    return user


async def list_all_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return list(result.scalars().all())


async def impersonate_user(
    db: AsyncSession,
    target_user_id: uuid.UUID,
    impersonator_id: uuid.UUID,
) -> TokenResponse:
    target_user = await db.get(User, target_user_id)
    if target_user is None:
        raise NotFoundError("User not found")

    imp_id = None if target_user.id == impersonator_id else impersonator_id
    access_token = create_access_token(
        user_id=target_user.id,
        role=target_user.role.value,
        impersonator_id=imp_id,
    )
    raw_refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=target_user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()
    logger.info("User %s impersonated by super admin %s", target_user.id, impersonator_id)
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh_token, user=target_user)


async def stop_impersonation(db: AsyncSession, impersonator_id: uuid.UUID) -> TokenResponse:
    admin_user = await db.get(User, impersonator_id)
    if admin_user is None or admin_user.role != UserRole.SUPER_ADMIN:
        raise ForbiddenError("Original impersonator not found or not a super admin")
    return await _issue_tokens(db, admin_user)
