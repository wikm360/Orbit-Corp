"""volume report: monthly forecast files (kind + the month they cover)

Revision ID: 0023_vr_monthly_plan
Revises: 0022_vr_income_totals
Create Date: 2026-11-11

Additive: `vr_report_files.kind` ('period' | 'monthly_plan', existing rows are 'period') and the date range of the month a
monthly forecast covers. Its quantities are stored raw and scaled by (days of the next period inside the month / days of the month).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_vr_monthly_plan"
down_revision: Union[str, None] = "0022_vr_income_totals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vr_report_files", sa.Column("kind", sa.String(length=16), nullable=False, server_default="period"))
    op.add_column("vr_report_files", sa.Column("plan_start", sa.Date(), nullable=True))
    op.add_column("vr_report_files", sa.Column("plan_end", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("vr_report_files", "plan_end")
    op.drop_column("vr_report_files", "plan_start")
    op.drop_column("vr_report_files", "kind")
