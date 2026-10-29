import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, false, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    """Global, org-wide role. Team-scoped leadership is a separate concept,
    see `TeamMembership.role` in `access_control.models`."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=UserRole.USER,
        nullable=False,
    )
    # Delegated by a super admin: lets this user use the Rahkaran accounting tools. Independent of `role` (a plain
    # user can hold it, an admin can lack it); super admins always have access whatever this says.
    accounting_access: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    accounting_access_granted_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accounting_access_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def has_accounting_access(self) -> bool:
        """Effective access: super admins always, everyone else only when explicitly granted."""
        return self.role == UserRole.SUPER_ADMIN or bool(self.accounting_access)

    team_memberships: Mapped[list["TeamMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="TeamMembership.user_id",
    )


class RefreshToken(Base):
    """A long-lived credential used to mint new access tokens without re-login.

    Only its hash is stored (never the raw token), the same way passwords
    are hashed — a DB read doesn't hand out anything usable. Rotated on
    every use (see `auth.service.refresh_tokens`): reuse of an already-
    rotated token is how theft gets detected.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
