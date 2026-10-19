"""Re-embed everything that was embedded with a different model than the one configured now.

Vectors from different embedding models are not comparable, so after changing `EMBEDDING_MODEL` (or its dimensions /
`EMBEDDING_SEND_DIMENSIONS`) the stored chunks and project memories must be re-embedded, otherwise search silently returns
nonsense. Run:  python -m app.features.documents.reembed [--dry-run] [--only documents|memories]
(schema hints are refreshed by `python -m app.features.db_connector.ingest`, which re-embeds a hint whenever the model changed).

Documents are tracked by `documents.embedding_model`; project memories have no such column, so they are always re-embedded.
Each document is committed on its own, so an interrupted run can simply be started again.
"""

import argparse
import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import model_registry  # noqa: F401 - registers all models
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.features.documents.ingestion.embedder import embed_chunks
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.features.memory.models import ProjectMemory
from app.providers.embedding_provider import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


async def reembed_documents(db: AsyncSession, provider: EmbeddingProvider, *, dry_run: bool = False) -> dict:
    model = get_settings().embedding_model
    document_ids = (
        await db.execute(
            select(Document.id).where(
                Document.status == DocumentStatus.READY,
                Document.embedding_model.is_distinct_from(model),
            )
        )
    ).scalars().all()
    stats = {"documents": len(document_ids), "chunks": 0}
    for document_id in document_ids:
        chunks = (
            await db.execute(
                select(DocumentChunk.id, DocumentChunk.content)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
            )
        ).all()
        stats["chunks"] += len(chunks)
        if dry_run:
            continue
        vectors = await embed_chunks(provider, [content for _, content in chunks])
        for (chunk_id, _), vector in zip(chunks, vectors, strict=True):
            await db.execute(update(DocumentChunk).where(DocumentChunk.id == chunk_id).values(embedding=vector))
        await db.execute(update(Document).where(Document.id == document_id).values(embedding_model=model))
        await db.commit()
        logger.info("re-embedded document %s (%d chunks)", document_id, len(chunks))
    return stats


async def reembed_memories(db: AsyncSession, provider: EmbeddingProvider, *, dry_run: bool = False) -> dict:
    memories = (await db.execute(select(ProjectMemory.id, ProjectMemory.fact_text))).all()
    if not dry_run:
        for start in range(0, len(memories), 64):
            batch = memories[start : start + 64]
            vectors = await provider.embed([fact for _, fact in batch])
            for (memory_id, _), vector in zip(batch, vectors, strict=True):
                await db.execute(update(ProjectMemory).where(ProjectMemory.id == memory_id).values(embedding=vector))
        await db.commit()
    return {"memories": len(memories)}


async def main(only: str | None, dry_run: bool) -> None:
    provider = get_embedding_provider()
    async with async_session_factory() as db:
        if only in (None, "documents"):
            logger.info("documents: %s", await reembed_documents(db, provider, dry_run=dry_run))
        if only in (None, "memories"):
            logger.info("memories: %s", await reembed_memories(db, provider, dry_run=dry_run))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="only count what would be re-embedded")
    parser.add_argument("--only", choices=["documents", "memories"])
    args = parser.parse_args()
    asyncio.run(main(args.only, args.dry_run))
