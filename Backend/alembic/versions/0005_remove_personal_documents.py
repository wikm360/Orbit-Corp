"""remove the personal documents library

Revision ID: 0005_remove_personal_documents
Revises: 0004_project_memory
Create Date: 2026-09-25

Every document now belongs to exactly one project or exactly one
conversation. The floating "personal library" scope (project_id and
conversation_id both NULL, matched by `uploaded_by`) is gone: its access
rule leaked every file a user had ever uploaded into every other chat they
opened.

DATA LOSS: existing personal-library rows have no project or conversation to
move to, so they (and, via ON DELETE CASCADE, their chunks) are deleted here.
The uploaded files on disk are not touched. Not reversible for those rows -
downgrade only restores the old constraint, not the deleted documents.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005_remove_personal_documents"
down_revision: Union[str, None] = "0004_project_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM documents WHERE project_id IS NULL AND conversation_id IS NULL")

    op.drop_constraint("ck_document_single_scope", "documents", type_="check")
    op.create_check_constraint(
        "ck_document_single_scope",
        "documents",
        "(project_id IS NOT NULL AND conversation_id IS NULL) OR "
        "(project_id IS NULL AND conversation_id IS NOT NULL)",
    )
    op.drop_index("ix_documents_uploaded_by", table_name="documents")


def downgrade() -> None:
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])
    op.drop_constraint("ck_document_single_scope", "documents", type_="check")
    op.create_check_constraint(
        "ck_document_single_scope",
        "documents",
        "(project_id IS NOT NULL AND conversation_id IS NULL) OR "
        "(project_id IS NULL AND conversation_id IS NOT NULL) OR "
        "(project_id IS NULL AND conversation_id IS NULL AND uploaded_by IS NOT NULL)",
    )
