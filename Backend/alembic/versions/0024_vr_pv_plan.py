"""volume report: monthly PV plan rows + the period a forecast EVM sheet names

Revision ID: 0024_vr_pv_plan
Revises: 0023_vr_monthly_plan
Create Date: 2026-11-11

Additive: `vr_pv_plan_rows` (per project monthly PV, from a "PVF"-shaped sheet) and `vr_evm_rows.period_start/period_end`
(the period a forecast sheet's title names). `vr_report_files.kind` also takes the value 'monthly_pv' (no schema change).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0024_vr_pv_plan"
down_revision: Union[str, None] = "0023_vr_monthly_plan"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vr_evm_rows", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("vr_evm_rows", sa.Column("period_end", sa.Date(), nullable=True))
    op.create_table(
        "vr_pv_plan_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vr_report_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("project_name", sa.Text(), nullable=False),
        sa.Column("pv_month", sa.Numeric(24, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vr_pv_plan_rows_report_file_id", "vr_pv_plan_rows", ["report_file_id"])


def downgrade() -> None:
    op.drop_index("ix_vr_pv_plan_rows_report_file_id", table_name="vr_pv_plan_rows")
    op.drop_table("vr_pv_plan_rows")
    op.drop_column("vr_evm_rows", "period_end")
    op.drop_column("vr_evm_rows", "period_start")
