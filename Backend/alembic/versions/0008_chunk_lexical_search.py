"""full-text + trigram search columns on document_chunks (hybrid retrieval)

Revision ID: 0008_chunk_lexical_search
Revises: 0007_message_artifacts
Create Date: 2026-10-19

Adds the lexical half of hybrid document retrieval:
- `search_text`: the chunk normalized with the same Python function the query side uses
  (`app.core.text_normalization.normalize`), backfilled for existing chunks in batches.
- `search_tsv`: `to_tsvector('simple', search_text)`, a stored generated column (the 'simple' config because there is
  no Persian dictionary; normalization already unified the letter variants), with a GIN index.
- a GIN trigram index on `search_text` (typo tolerance for short queries / names).
Needs the `pg_trgm` extension (ships with the stock Postgres contrib / pgvector image). Adding the generated column
rewrites the table once; run it in a quiet window on a big corpus.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.text_normalization import normalize

revision: str = "0008_chunk_lexical_search"
down_revision: Union[str, None] = "0007_message_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BATCH = 500


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.add_column("document_chunks", sa.Column("search_text", sa.Text, nullable=True))

    bind = op.get_bind()
    update = sa.text("UPDATE document_chunks SET search_text = :t WHERE id = :id")
    last_id = None
    while True:
        rows = bind.execute(
            sa.text(
                "SELECT id, content FROM document_chunks "
                "WHERE (CAST(:last AS uuid) IS NULL OR id > CAST(:last AS uuid)) ORDER BY id LIMIT :n"
            ),
            {"last": last_id, "n": _BATCH},
        ).all()
        if not rows:
            break
        bind.execute(update, [{"id": row.id, "t": normalize(row.content or "")} for row in rows])
        last_id = str(rows[-1].id)

    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN search_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', coalesce(search_text, ''))) STORED"
    )
    op.execute("CREATE INDEX ix_document_chunks_search_tsv ON document_chunks USING gin (search_tsv)")
    op.execute(
        "CREATE INDEX ix_document_chunks_search_text_trgm ON document_chunks USING gin (search_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_search_text_trgm")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_search_tsv")
    op.drop_column("document_chunks", "search_tsv")
    op.drop_column("document_chunks", "search_text")
