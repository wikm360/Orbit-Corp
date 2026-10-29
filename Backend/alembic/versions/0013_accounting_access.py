"""delegated accounting access: users.accounting_access*, messages.contains_financial

Revision ID: 0013_accounting_access
Revises: 0012_ocr_cache_document_source
Create Date: 2026-10-29

A super admin can now grant or revoke the Rahkaran accounting tools per user (any role). Existing admins keep the access
they had (flag set to true); super admins always have it and ignore the flag. Replies that already carry a `sql_result`
artifact are marked `contains_financial` so users without access get a placeholder instead of the figures.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0013_accounting_access"
down_revision: Union[str, None] = "0012_ocr_cache_document_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("accounting_access", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        "users",
        sa.Column("accounting_access_granted_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("users", sa.Column("accounting_access_granted_at", sa.DateTime(timezone=True), nullable=True))
    # Behaviour is unchanged for the people who could use the tools before this migration.
    op.execute("UPDATE users SET accounting_access = true, accounting_access_granted_at = now() WHERE role = 'admin'")

    op.add_column("messages", sa.Column("contains_financial", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE messages SET contains_financial = true WHERE artifacts @> '[{\"type\": \"sql_result\"}]'::jsonb")


def downgrade() -> None:
    op.drop_column("messages", "contains_financial")
    op.drop_column("users", "accounting_access_granted_at")
    op.drop_column("users", "accounting_access_granted_by")
    op.drop_column("users", "accounting_access")
