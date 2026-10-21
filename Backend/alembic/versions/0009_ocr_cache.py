"""ocr_cache: vision-OCR results keyed by image hash + model/prompt

Revision ID: 0009_ocr_cache
Revises: 0008_chunk_lexical_search
Create Date: 2026-10-21

A repeated image/page (same scan in another document, repeated logo/stamp, a retry) reuses the stored text instead of
paying for another vision call. See `OcrCache` in app/features/documents/models.py.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_ocr_cache"
down_revision: Union[str, None] = "0008_chunk_lexical_search"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ocr_cache",
        sa.Column("cache_key", sa.String(length=128), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("vision_model", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ocr_cache")
