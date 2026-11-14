import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.features.auth.models import RefreshToken, User, UserRole

logger = logging.getLogger(__name__)


def can_manage(actor: User, target: User) -> bool:
    """Super admins manage everyone. A delegated manager only manages plain users who do not themselves hold the
    permission (so it cannot be used to take over an admin, or a peer manager, by resetting their password)."""
    if actor.role == UserRole.SUPER_ADMIN:
        return True
    return target.role == UserRole.USER and not target.user_management_access


async def _get_target(db: AsyncSession, actor: User, user_id: uuid.UUID, *, allow_self: bool = False) -> User:
    target = await db.get(User, user_id)
    if target is None:
        raise NotFoundError("User not found")
    if allow_self and target.id == actor.id:
        return target
    if not can_manage(actor, target):
        raise ForbiddenError("You cannot manage this user")
    return target


async def list_users(db: AsyncSession, actor: User) -> list[tuple[User, bool]]:
    users = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    return [(u, u.id != actor.id and can_manage(actor, u)) for u in users]


async def _ensure_email_free(db: AsyncSession, email: str, *, except_id: uuid.UUID | None = None) -> None:
    row = (await db.execute(select(User.id).where(User.email == email))).scalar_one_or_none()
    if row is not None and row != except_id:
        raise ConflictError("A user with this email already exists")


async def create_user(db: AsyncSession, actor: User, *, email: str, password: str, full_name: str) -> User:
    """Always a plain `user`: roles stay a super-admin decision (`PATCH /admin/users/{id}/role`)."""
    await _ensure_email_free(db, email)
    user = User(email=email, hashed_password=hash_password(password), full_name=full_name, role=UserRole.USER)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("User %s created by %s (user-management)", user.id, actor.id)
    return user


async def update_user(db: AsyncSession, actor: User, user_id: uuid.UUID, *, email: str | None, full_name: str | None) -> User:
    target = await _get_target(db, actor, user_id, allow_self=True)
    if email is not None and email != target.email:
        await _ensure_email_free(db, email, except_id=target.id)
        target.email = email
    if full_name is not None:
        target.full_name = full_name
    await db.commit()
    await db.refresh(target)
    logger.info("User %s updated by %s (user-management)", target.id, actor.id)
    return target


async def _revoke_sessions(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )


async def reset_password(db: AsyncSession, actor: User, user_id: uuid.UUID, password: str) -> None:
    """Also revokes the target's refresh tokens so an old (possibly compromised) session cannot outlive the reset;
    an already-issued access token still lives until it expires (stateless, by design)."""
    target = await _get_target(db, actor, user_id, allow_self=True)
    target.hashed_password = hash_password(password)
    await _revoke_sessions(db, target.id)
    await db.commit()
    logger.info("Password of %s reset by %s (user-management)", target.id, actor.id)


async def delete_user(db: AsyncSession, actor: User, user_id: uuid.UUID) -> None:
    if user_id == actor.id:
        raise BadRequestError("You cannot delete your own account")
    target = await _get_target(db, actor, user_id)
    # Owned rows follow the FKs (memberships, tokens, personal chats cascade; authorship columns become NULL).
    await db.execute(delete(User).where(User.id == target.id))
    await db.commit()
    logger.info("User %s deleted by %s (user-management)", user_id, actor.id)


async def set_access(db: AsyncSession, user_id: uuid.UUID, *, enabled: bool, granted_by: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.role == UserRole.SUPER_ADMIN:
        raise BadRequestError("Super admins always have user-management access; it cannot be changed")
    if user.user_management_access != enabled:
        user.user_management_access = enabled
        user.user_management_access_granted_by = granted_by if enabled else None
        user.user_management_access_granted_at = datetime.now(timezone.utc) if enabled else None
        await db.commit()
        await db.refresh(user)
        logger.info("User-management access %s for %s by %s", "granted" if enabled else "revoked", user.id, granted_by)
    return user
