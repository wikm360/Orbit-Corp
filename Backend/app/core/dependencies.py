from dataclasses import dataclass, field
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.features.access_control.service import get_user_team_ids
from app.features.auth.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class UserContext:
    """The authenticated user plus the team ids they may access documents through.

    Bundled here (rather than re-derived per feature) since both retrieval
    access filtering and admin checks depend on it.
    """

    user: User
    team_ids: list[UUID] = field(default_factory=list)

    @property
    def id(self) -> UUID:
        return self.user.id

    @property
    def role(self) -> UserRole:
        return self.user.role


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except jwt.PyJWTError as exc:
        raise UnauthorizedError() from exc

    if user_id is None:
        raise UnauthorizedError()

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError()
    return user


async def get_current_user_context(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    team_ids = await get_user_team_ids(db, user.id)
    return UserContext(user=user, team_ids=team_ids)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin privileges required")
    return user
