"""volume report: income-sheet totals (statement, coefficients, adjustment, total income, cumulative)

Revision ID: 0022_vr_income_totals
Revises: 0021_vr_evm_rows
Create Date: 2026-11-11

Additive: new table `vr_income_totals`, one row per income sheet, filled by the extraction.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0022_vr_income_totals"
down_revision: Union[str, None] = "0021_vr_evm_rows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vr_income_totals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vr_report_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("basis", sa.String(length=10), nullable=False, server_default="actual"),
        sa.Column("statement_base", sa.Numeric(24, 2), nullable=True),
        sa.Column("statement_coef", sa.Numeric(24, 2), nullable=True),
        sa.Column("adjustment", sa.Numeric(24, 2), nullable=True),
        sa.Column("income_total", sa.Numeric(24, 2), nullable=True),
        sa.Column("cumulative", sa.Numeric(24, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vr_income_totals_report_file_id", "vr_income_totals", ["report_file_id"])


def downgrade() -> None:
    op.drop_index("ix_vr_income_totals_report_file_id", table_name="vr_income_totals")
    op.drop_table("vr_income_totals")
