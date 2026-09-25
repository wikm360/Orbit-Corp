"""project memory + documents scope index

Revision ID: 0004_project_memory
Revises: 0003_allow_personal_documents
Create Date: 2026-09-25

Adds `project_memories`: a project-scoped shared knowledge base of facts and
decisions the chat agent can recall and add to (semantic search via pgvector,
same pattern as `document_chunks`). Also adds a composite index on
`documents(project_id, conversation_id)` used by the new document-scoped
agent tools.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

from app.core.config import get_settings

revision: str = "0004_project_memory"
down_revision: Union[str, None] = "0003_allow_personal_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

settings = get_settings()

memory_category_enum = pg.ENUM(
    "technical_decision",
    "timeline",
    "business_rule",
    "convention",
    name="memory_category",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    memory_category_enum.create(bind, checkfirst=True)

    op.create_table(
        "project_memories",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fact_text", sa.Text, nullable=False),
        sa.Column("category", memory_category_enum, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("embedding", Vector(settings.embedding_dimensions), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_project_memories_project_id", "project_memories", ["project_id"])
    op.execute(
        "CREATE INDEX ix_project_memories_embedding_hnsw ON project_memories "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_index(
        "ix_documents_project_conversation", "documents", ["project_id", "conversation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_documents_project_conversation", table_name="documents")

    op.drop_index("ix_project_memories_embedding_hnsw", table_name="project_memories")
    op.drop_index("ix_project_memories_project_id", table_name="project_memories")
    op.drop_table("project_memories")

    memory_category_enum.drop(op.get_bind(), checkfirst=True)
