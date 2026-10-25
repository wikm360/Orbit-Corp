"""ocr_cache.rotation: the clockwise rotation found for an OCR'd image

Revision ID: 0010_ocr_cache_rotation
Revises: 0009_ocr_cache
Create Date: 2026-10-24

Finding an image's orientation costs 1-4 model calls; a cache hit skips the OCR call that finds it, so the result is
stored with the cached text. NULL = unknown (rows written before this column existed).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_ocr_cache_rotation"
down_revision: Union[str, None] = "0009_ocr_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ocr_cache", sa.Column("rotation", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("ocr_cache", "rotation")
