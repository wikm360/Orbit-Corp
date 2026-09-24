"""allow personal documents scope

Revision ID: 0003_allow_personal_documents
Revises: 0002_projects_chat_roles
Create Date: 2026-09-24

Updates the documents table check constraint to allow personal documents:
(project_id IS NOT NULL AND conversation_id IS NULL) OR
(project_id IS NULL AND conversation_id IS NOT NULL) OR
(project_id IS NULL AND conversation_id IS NULL AND uploaded_by IS NOT NULL)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_allow_personal_documents"
down_revision: Union[str, None] = "0002_projects_chat_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_document_single_scope", "documents", type_="check")
    op.create_check_constraint(
        "ck_document_single_scope",
        "documents",
        "(project_id IS NOT NULL AND conversation_id IS NULL) OR "
        "(project_id IS NULL AND conversation_id IS NOT NULL) OR "
        "(project_id IS NULL AND conversation_id IS NULL AND uploaded_by IS NOT NULL)",
    )
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])


def downgrade() -> None:
    op.drop_index("ix_documents_uploaded_by", table_name="documents")
    op.drop_constraint("ck_document_single_scope", "documents", type_="check")
    op.create_check_constraint(
        "ck_document_single_scope",
        "documents",
        "(project_id IS NOT NULL AND conversation_id IS NULL) OR "
        "(project_id IS NULL AND conversation_id IS NOT NULL)",
    )

