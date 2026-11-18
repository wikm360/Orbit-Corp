"""volume report: projects removed from a report's EVM

Revision ID: 0033_vr_evm_exclusions
Revises: 0032_vr_forecast_period
Create Date: 2026-11-19

Additive: `vr_evm_exclusions` (report, company, normalized project name).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033_vr_evm_exclusions"
down_revision: Union[str, None] = "0032_vr_forecast_period"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vr_evm_exclusions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vr_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vr_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_key", sa.Text(), nullable=False),
        sa.Column("project_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("report_id", "company_id", "project_key", name="uq_vr_evm_exclusions_project"),
    )
    op.create_index("ix_vr_evm_exclusions_report_id", "vr_evm_exclusions", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_vr_evm_exclusions_report_id", table_name="vr_evm_exclusions")
    op.drop_table("vr_evm_exclusions")
