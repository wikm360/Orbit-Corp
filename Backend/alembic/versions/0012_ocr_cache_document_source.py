"""ocr_cache: link cached OCR to document_id, source_filename, and page_number

Revision ID: 0012_ocr_cache_document_source
Revises: 0011_file_manager
Create Date: 2026-10-29

Allows users and administrators to view which document and page an OCR cache entry
belongs to, search by filename, and purge OCR cache per document or upon document deletion.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0012_ocr_cache_document_source"
down_revision: Union[str, None] = "0011_file_manager"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ocr_cache",
        sa.Column(
            "document_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column("ocr_cache", sa.Column("source_filename", sa.String(500), nullable=True))
    op.add_column("ocr_cache", sa.Column("page_number", sa.Integer(), nullable=True))

    op.create_index("ix_ocr_cache_document_id", "ocr_cache", ["document_id"])
    op.create_index("ix_ocr_cache_source_filename", "ocr_cache", ["source_filename"])


def downgrade() -> None:
    op.drop_index("ix_ocr_cache_source_filename", table_name="ocr_cache")
    op.drop_index("ix_ocr_cache_document_id", table_name="ocr_cache")
    op.drop_column("ocr_cache", "page_number")
    op.drop_column("ocr_cache", "source_filename")
    op.drop_column("ocr_cache", "document_id")
