"""delegated user-management access: users.user_management_access*

Revision ID: 0030_user_management_access
Revises: 0029_org_branding
Create Date: 2026-11-18

Additive. A super admin can delegate account management (create / change email / reset password / delete plain users) to
any user without handing over the rest of the admin panel. Off for everyone by default; super admins always have it.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0030_user_management_access"
down_revision: Union[str, None] = "0029_org_branding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("user_management_access", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        "users",
        sa.Column("user_management_access_granted_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("users", sa.Column("user_management_access_granted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "user_management_access_granted_at")
    op.drop_column("users", "user_management_access_granted_by")
    op.drop_column("users", "user_management_access")
