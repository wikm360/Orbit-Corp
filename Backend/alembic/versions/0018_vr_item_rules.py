"""volume report: item rules (phrase-scoped fixed-factor conversion per item)

Revision ID: 0018_vr_item_rules
Revises: 0017_token_quota
Create Date: 2026-11-04

Additive: a new table only.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_vr_item_rules"
down_revision: Union[str, None] = "0017_token_quota"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vr_item_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phrases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_unit", sa.String(length=20), nullable=False),
        sa.Column("factor", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["vr_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["vr_sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vr_item_rules_item_id", "vr_item_rules", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_vr_item_rules_item_id", table_name="vr_item_rules")
    op.drop_table("vr_item_rules")
