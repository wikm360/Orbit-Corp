"""message artifacts: structured evidence attached to assistant replies

Revision ID: 0007_message_artifacts
Revises: 0006_accounting_db_connector
Create Date: 2026-10-09

Adds `messages.artifacts` (JSONB list). Tools can attach structured evidence to the assistant reply; the accounting-database
tool stores the exact SQL, columns and rows it ran (`{"type": "sql_result", ...}`) so the UI can show the reference next to the answer.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0007_message_artifacts"
down_revision: Union[str, None] = "0006_accounting_db_connector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("artifacts", pg.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("messages", "artifacts")
