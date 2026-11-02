"""project member permissions: project_memberships.permissions

Revision ID: 0016_project_member_permissions
Revises: 0015_vr_activity
Create Date: 2026-11-02

Additive: delegated per-project permissions (empty by default, so existing behaviour is unchanged).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_project_member_permissions"
down_revision: Union[str, None] = "0015_vr_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_memberships",
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("project_memberships", "permissions")
