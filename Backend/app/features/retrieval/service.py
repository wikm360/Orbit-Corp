from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import UserContext
from app.features.documents.models import Document, DocumentChunk
from app.features.retrieval.access_filter import accessible_documents_filter


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_filename: str
    content: str
    chunk_index: int
    score: float


class Retriever(ABC):
    """Abstract retrieval interface.

    Kept separate from `VectorRetriever` so phase 2 can introduce
    `HybridRetriever` (BM25 + vector) or wrap this with a re-ranking step,
    without changing the signature `chat.service` depends on.
    """

    @abstractmethod
    async def retrieve(
        self,
        db: AsyncSession,
        context: UserContext,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        ...


class VectorRetriever(Retriever):
    """MVP implementation: pgvector cosine similarity search with access filtering."""

    async def retrieve(
        self,
        db: AsyncSession,
        context: UserContext,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(
                DocumentChunk,
                Document.filename,
                distance.label("distance"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(accessible_documents_filter(context))
            .order_by(distance)
            .limit(top_k)
        )
        result = await db.execute(stmt)

        retrieved: list[RetrievedChunk] = []
        for chunk, filename, dist in result.all():
            similarity = 1 - dist
            retrieved.append(
                RetrievedChunk(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    document_filename=filename,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    score=similarity,
                )
            )
        return retrieved


def get_retriever() -> Retriever:
    return VectorRetriever()
