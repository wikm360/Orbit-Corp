"""delegated workspace-management access: users.workspace_access*

Revision ID: 0031_workspace_access
Revises: 0030_user_management_access
Create Date: 2026-11-19

Additive. A super admin can delegate team/project administration (create teams and projects, manage team and project
members and project permissions) to any user without making them an org admin. Off by default; admins and super admins
always have it.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0031_workspace_access"
down_revision: Union[str, None] = "0030_user_management_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("workspace_access", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        "users",
        sa.Column("workspace_access_granted_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("users", sa.Column("workspace_access_granted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "workspace_access_granted_at")
    op.drop_column("users", "workspace_access_granted_by")
    op.drop_column("users", "workspace_access")
