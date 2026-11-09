"""volume report: company project performance narratives

Revision ID: 0020_vr_narratives
Revises: 0019_vr_plan_basis
Create Date: 2026-11-08

Adds `narratives` JSONB column to `vr_reports` to store executive project status & action items per company.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0020_vr_narratives"
down_revision: Union[str, None] = "0019_vr_plan_basis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vr_reports",
        sa.Column(
            "narratives",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("vr_reports", "narratives")
