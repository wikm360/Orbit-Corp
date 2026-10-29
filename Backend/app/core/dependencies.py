from dataclasses import dataclass, field
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.features.access_control.service import get_user_led_team_ids, get_user_team_ids
from app.features.auth.models import User, UserRole
from app.features.projects.models import Project
from app.features.projects.service import get_user_project_ids

bearer_scheme = HTTPBearer()

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.ADMIN)


@dataclass
class UserContext:
    """The authenticated user plus the org-membership info access checks need.

    Bundled here (rather than re-derived per feature) since retrieval
    filtering, chat access, and management endpoints all depend on it.
    """

    user: User
    team_ids: list[UUID] = field(default_factory=list)
    led_team_ids: list[UUID] = field(default_factory=list)
    project_ids: list[UUID] = field(default_factory=list)

    @property
    def id(self) -> UUID:
        return self.user.id

    @property
    def role(self) -> UserRole:
        return self.user.role

    @property
    def is_admin(self) -> bool:
        """SUPER_ADMIN or ADMIN (CEO) — org-wide privileges."""
        return self.role in ADMIN_ROLES

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def can_use_accounting(self) -> bool:
        """The Rahkaran accounting tools: super admins always, anyone else only when a super admin granted it."""
        return self.user.has_accounting_access

    def leads_team(self, team_id: UUID) -> bool:
        return self.is_admin or team_id in self.led_team_ids

    def is_project_member(self, project_id: UUID) -> bool:
        return self.is_admin or project_id in self.project_ids


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
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
    led_team_ids = await get_user_led_team_ids(db, user.id)
    project_ids = await get_user_project_ids(db, user.id)
    return UserContext(
        user=user, team_ids=team_ids, led_team_ids=led_team_ids, project_ids=project_ids
    )


def require_role(*roles: UserRole):
    """Dependency factory: only users whose global role is one of `roles`."""

    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action")
        return user

    return _dependency


require_super_admin = require_role(UserRole.SUPER_ADMIN)
require_admin = require_role(*ADMIN_ROLES)


async def require_accounting_access(user: User = Depends(get_current_user)) -> User:
    """Holders of the delegated accounting permission (and super admins)."""
    if not user.has_accounting_access:
        raise ForbiddenError("Accounting access is required for this action")
    return user


async def require_accounting_admin(user: User = Depends(get_current_user)) -> User:
    """Organisation oversight of accounting activity: an admin who also holds the accounting permission."""
    if user.role not in ADMIN_ROLES or not user.has_accounting_access:
        raise ForbiddenError("Admin role with accounting access is required for this action")
    return user


async def require_team_manager(
    team_id: UUID,
    context: UserContext = Depends(get_current_user_context),
) -> UserContext:
    """Team leader (of this team) or org admin — can manage team membership/projects."""
    if not context.leads_team(team_id):
        raise ForbiddenError("Team leader or admin privileges required")
    return context


async def require_project_manager(
    project_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Leader of the project's parent team, or org admin — can manage project membership/documents."""
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    if not context.leads_team(project.team_id):
        raise ForbiddenError("Team leader or admin privileges required")
    return project


async def require_project_access(
    project_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Any project member, the parent team's leader(s), or an org admin — read access."""
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    if not (context.is_project_member(project.id) or context.leads_team(project.team_id)):
        raise ForbiddenError("You are not a member of this project")
    return project
