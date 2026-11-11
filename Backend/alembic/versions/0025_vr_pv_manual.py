"""volume report: manual PV per project

Revision ID: 0025_vr_pv_manual
Revises: 0024_vr_pv_plan
Create Date: 2026-11-11

Additive: `vr_reports.pv_mode` ('auto' | 'manual', existing rows 'auto') and `vr_pv_overrides` (the PV typed per project).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0025_vr_pv_manual"
down_revision: Union[str, None] = "0024_vr_pv_plan"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vr_reports", sa.Column("pv_mode", sa.String(length=10), nullable=False, server_default="auto"))
    op.create_table(
        "vr_pv_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vr_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vr_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_key", sa.Text(), nullable=False),
        sa.Column("project_name", sa.Text(), nullable=False),
        sa.Column("pv", sa.Numeric(24, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("report_id", "company_id", "project_key", name="uq_vr_pv_overrides_project"),
    )
    op.create_index("ix_vr_pv_overrides_report_id", "vr_pv_overrides", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_vr_pv_overrides_report_id", table_name="vr_pv_overrides")
    op.drop_table("vr_pv_overrides")
    op.drop_column("vr_reports", "pv_mode")
