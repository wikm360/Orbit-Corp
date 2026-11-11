"""volume report: EVM summary rows (PV / EV / ev / AC / CPI / SPI per project and per sheet total)

Revision ID: 0021_vr_evm_rows
Revises: 0020_vr_narratives
Create Date: 2026-11-11

Additive: new table `vr_evm_rows`, filled by the extraction from the EVM summary sheet/page of each report file.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0021_vr_evm_rows"
down_revision: Union[str, None] = "0020_vr_narratives"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vr_evm_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vr_report_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("basis", sa.String(length=10), nullable=False, server_default="actual"),
        sa.Column("project_name", sa.Text(), nullable=True),
        sa.Column("is_total", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("contract_amount", sa.Numeric(24, 2), nullable=True),
        sa.Column("bcws", sa.Numeric(24, 2), nullable=True),
        sa.Column("pv", sa.Numeric(24, 2), nullable=True),
        sa.Column("ev", sa.Numeric(24, 2), nullable=True),
        sa.Column("ev_net", sa.Numeric(24, 2), nullable=True),
        sa.Column("ac", sa.Numeric(24, 2), nullable=True),
        sa.Column("cpi", sa.Numeric(10, 3), nullable=True),
        sa.Column("spi", sa.Numeric(10, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vr_evm_rows_report_file_id", "vr_evm_rows", ["report_file_id"])


def downgrade() -> None:
    op.drop_index("ix_vr_evm_rows_report_file_id", table_name="vr_evm_rows")
    op.drop_table("vr_evm_rows")
