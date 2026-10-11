"""accounting db connector: schema_hints and db_query_logs

Revision ID: 0006_accounting_db_connector
Revises: 0005_remove_personal_documents
Create Date: 2026-10-09

Adds tables for the Rahkaran enterprise accounting database connector:
- `schema_hints`: global knowledge corpus (view schemas, descriptions, query examples)
  retrieved via hybrid vector + lexical search to ground SQL generation.
- `db_query_logs`: records every question, retrieved hints, executed SQL, execution
  status/duration, row counts, and user feedback (+1 / -1) for audit and continuous improvement.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

from app.core.config import get_settings

revision: str = "0006_accounting_db_connector"
down_revision: Union[str, None] = "0005_remove_personal_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

settings = get_settings()

query_status_enum = pg.ENUM(
    "ok",
    "rejected",
    "error",
    name="db_query_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    query_status_enum.create(bind, checkfirst=True)

    # 1. schema_hints
    op.create_table(
        "schema_hints",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("hint_key", sa.String(200), nullable=False, unique=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("views", pg.JSONB, nullable=False, server_default="[]"),
        sa.Column("keywords", pg.JSONB, nullable=False, server_default="[]"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding_model", sa.String(255), nullable=True),
        sa.Column("embedding", Vector(settings.embedding_dimensions), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_schema_hints_kind", "schema_hints", ["kind"])
    op.create_index("ix_schema_hints_hint_key", "schema_hints", ["hint_key"], unique=True)
    op.execute(
        "CREATE INDEX ix_schema_hints_embedding_hnsw ON schema_hints "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # 2. db_query_logs
    op.create_table(
        "db_query_logs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "conversation_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("hint_keys", pg.JSONB, nullable=False, server_default="[]"),
        sa.Column("sql_text", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", query_status_enum, nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("truncated", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("feedback", sa.SmallInteger, nullable=True),
        sa.Column("feedback_note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_db_query_logs_user_id", "db_query_logs", ["user_id"])
    op.create_index("ix_db_query_logs_conversation_id", "db_query_logs", ["conversation_id"])
    op.create_index("ix_db_query_logs_status", "db_query_logs", ["status"])
    op.create_index("ix_db_query_logs_created_at", "db_query_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_db_query_logs_created_at", table_name="db_query_logs")
    op.drop_index("ix_db_query_logs_status", table_name="db_query_logs")
    op.drop_index("ix_db_query_logs_conversation_id", table_name="db_query_logs")
    op.drop_index("ix_db_query_logs_user_id", table_name="db_query_logs")
    op.drop_table("db_query_logs")

    op.drop_index("ix_schema_hints_embedding_hnsw", table_name="schema_hints")
    op.drop_index("ix_schema_hints_hint_key", table_name="schema_hints")
    op.drop_index("ix_schema_hints_kind", table_name="schema_hints")
    op.drop_table("schema_hints")

    query_status_enum.drop(op.get_bind(), checkfirst=True)

