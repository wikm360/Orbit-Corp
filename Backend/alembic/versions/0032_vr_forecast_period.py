"""volume report: which period a forecast file is for

Revision ID: 0032_vr_forecast_period
Revises: 0031_workspace_access
Create Date: 2026-11-19

Additive. `vr_report_files.forecast_for` (auto | this_period | next_period): a forecast file is either the forecast of the
report's own period (it only supplies PV) or the plan of the period after it. `title_period_*` is the period most of the file's
sheet titles name, one of the hints `auto` reads (the file name is the other; titles are often last week's copy).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0032_vr_forecast_period"
down_revision: Union[str, None] = "0031_workspace_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vr_report_files", sa.Column("forecast_for", sa.String(12), nullable=False, server_default="auto"))
    op.add_column("vr_report_files", sa.Column("title_period_start", sa.Date(), nullable=True))
    op.add_column("vr_report_files", sa.Column("title_period_end", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("vr_report_files", "title_period_end")
    op.drop_column("vr_report_files", "title_period_start")
    op.drop_column("vr_report_files", "forecast_for")
