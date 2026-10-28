"""file manager: folders, archive imports, cancelled/unsupported document statuses

Revision ID: 0011_file_manager
Revises: 0010_ocr_cache_rotation
Create Date: 2026-10-28

Adds `document_folders` (a project's folder tree), `documents.folder_id`, `archive_imports` (a .zip/.rar/.7z being
unpacked by the worker) and two `document_status` values. Existing documents stay at the project root (folder_id NULL).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0011_file_manager"
down_revision: Union[str, None] = "0010_ocr_cache_rotation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NIL_UUID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'cancelled'")
        op.execute("ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'unsupported'")

    op.create_table(
        "document_folders",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", pg.UUID(as_uuid=True), sa.ForeignKey("document_folders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_folders_project_id", "document_folders", ["project_id"])
    op.execute(
        f"CREATE UNIQUE INDEX uq_document_folders_name ON document_folders "
        f"(project_id, coalesce(parent_id, '{_NIL_UUID}'::uuid), lower(name))"
    )

    op.add_column(
        "documents",
        sa.Column("folder_id", pg.UUID(as_uuid=True), sa.ForeignKey("document_folders.id", ondelete="CASCADE"), nullable=True),
    )
    op.create_index("ix_documents_folder_id", "documents", ["folder_id"])

    archive_status = pg.ENUM("extracting", "done", "failed", name="archive_import_status", create_type=False)
    archive_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "archive_imports",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("folder_id", pg.UUID(as_uuid=True), sa.ForeignKey("document_folders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("status", archive_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_files", pg.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("uploaded_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_archive_imports_project_id", "archive_imports", ["project_id"])


def downgrade() -> None:
    # Postgres cannot drop enum values: 'cancelled'/'unsupported' stay in document_status (harmless when unused).
    op.drop_index("ix_archive_imports_project_id", table_name="archive_imports")
    op.drop_table("archive_imports")
    op.execute("DROP TYPE IF EXISTS archive_import_status")
    op.drop_index("ix_documents_folder_id", table_name="documents")
    op.drop_column("documents", "folder_id")
    op.execute("DROP INDEX IF EXISTS uq_document_folders_name")
    op.drop_index("ix_document_folders_project_id", table_name="document_folders")
    op.drop_table("document_folders")
