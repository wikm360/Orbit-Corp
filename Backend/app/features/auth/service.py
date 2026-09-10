from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
)
from app.features.auth.models import RefreshToken, User, UserRole
from app.features.auth.schemas import TokenResponse, UserLogin, UserRegister


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, payload: UserRegister) -> TokenResponse:
    existing = await get_user_by_email(db, payload.email)
    if existing is not None:
        raise ConflictError("A user with this email already exists")

    is_first_user = (await db.execute(select(User.id).limit(1))).first() is None

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        # The very first account on a fresh deployment becomes the org's
        # super admin; everyone after that starts as a plain user and is
        # promoted explicitly (by an admin) or assigned into teams/projects.
        role=UserRole.SUPER_ADMIN if is_first_user else UserRole.USER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return await _issue_tokens(db, user)


async def login_user(db: AsyncSession, payload: UserLogin) -> TokenResponse:
    user = await get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    return await _issue_tokens(db, user)


async def refresh_tokens(db: AsyncSession, raw_refresh_token: str) -> TokenResponse:
    """Exchanges a valid, unexpired, unrevoked refresh token for a new access
    token — and rotates the refresh token itself (old one revoked, new one
    issued), so a reused/stolen token is detectable: it'll already show as
    revoked the moment the real owner's client refreshes next."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token))
    )
    stored = result.scalar_one_or_none()

    if (
        stored is None
        or stored.revoked_at is not None
        or stored.expires_at < datetime.now(timezone.utc)
    ):
        raise UnauthorizedError("Invalid or expired refresh token")

    user = await db.get(User, stored.user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired refresh token")

    stored.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    return await _issue_tokens(db, user)


async def logout_user(db: AsyncSession, raw_refresh_token: str) -> None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token))
    )
    stored = result.scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        await db.commit()


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    access_token = create_access_token(user_id=user.id, role=user.role.value)
    raw_refresh_token = generate_refresh_token()

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh_token, user=user)
