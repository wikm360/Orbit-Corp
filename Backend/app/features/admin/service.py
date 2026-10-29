import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.features.auth.models import User, UserRole
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


async def list_all_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return list(result.scalars().all())
