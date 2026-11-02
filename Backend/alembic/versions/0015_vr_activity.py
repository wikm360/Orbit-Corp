"""volume report: vr_activity (user-facing timeline of a report job)

Revision ID: 0015_vr_activity
Revises: 0014_volume_report
Create Date: 2026-11-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_vr_activity"
down_revision: Union[str, None] = "0014_volume_report"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('vr_activity',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('attempt', sa.Integer(), nullable=False),
    sa.Column('phase', sa.String(length=20), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=400), nullable=False),
    sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['report_id'], ['vr_reports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vr_activity_report_id'), 'vr_activity', ['report_id'], unique=False)


def downgrade() -> None:
    op.drop_table('vr_activity')
