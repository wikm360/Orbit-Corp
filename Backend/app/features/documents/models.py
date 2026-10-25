import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Computed, DateTime, Enum, ForeignKey, Index, Integer, SmallInteger, String, Text, event, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.core.database import Base
from app.core.text_normalization import normalize

settings = get_settings()


class DocumentStatus(str, enum.Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    """A RAG source file. Belongs to exactly one of two scopes:

    - `project_id`: part of a project's shared knowledge base (visible to every
      project member).
    - `conversation_id`: uploaded ad hoc into one chat (personal or group),
      visible only there.

    There is deliberately no third "personal library" scope: `uploaded_by` is
    audit metadata only and never grants access to a document.
    """

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "(project_id IS NOT NULL AND conversation_id IS NULL) OR "
            "(project_id IS NULL AND conversation_id IS NOT NULL)",
            name="ck_document_single_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=DocumentStatus.PROCESSING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # sha256 of the raw file bytes. Lets a re-upload of the same file reuse
    # the physical copy already on disk (and, if embedded with the same
    # model, its chunks) instead of storing another copy.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # The embedding model the persisted chunks were embedded with; null
    # while still PROCESSING. Used to decide whether a content match's
    # chunks are safe to reuse as-is.
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    # Lexical side of hybrid retrieval (see features/retrieval/service.py): a GIN full-text index and a GIN trigram index,
    # both over the normalized text. The vector HNSW index lives in the migrations only.
    __table_args__ = (
        Index("ix_document_chunks_search_tsv", "search_tsv", postgresql_using="gin"),
        Index(
            "ix_document_chunks_search_text_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=False
    )
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    # `normalize(content)` (Persian letter/digit variants unified, punctuation stripped), filled on insert by the listener below.
    search_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Derived by Postgres from search_text; never written by the app.
    search_tsv = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', coalesce(search_text, ''))", persisted=True), nullable=True
    )


@event.listens_for(DocumentChunk, "before_insert")
def _fill_search_text(_mapper, _connection, chunk: DocumentChunk) -> None:
    if chunk.search_text is None:
        chunk.search_text = normalize(chunk.content or "")


class OcrCache(Base):
    """Vision-OCR text keyed by the image's bytes + the OCR model/prompt that read it.

    Lets a page/image that was already read (same scan inside another document, a re-upload that is not byte-identical
    as a whole file, ...) skip the paid vision call. Deliberately NOT scoped to a project/conversation: the text is a
    pure function of the image bytes, so anyone who can upload those bytes could produce it anyway - no document,
    chunk or access rule is involved. Only non-empty results are stored (empty = blank image or a failed call).
    """

    __tablename__ = "ocr_cache"

    cache_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    vision_model: Mapped[str] = mapped_column(String(200), nullable=False)
    # Clockwise degrees the image was turned to be upright (0/90/180/270) when OCR'd; NULL = not determined. Stored here
    # because a cache hit skips the OCR call that finds it, and the page still needs it (see `view_document_page`).
    rotation: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
