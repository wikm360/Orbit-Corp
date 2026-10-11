import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base

settings = get_settings()


class SchemaHint(Base):
    """One retrievable chunk of knowledge about the accounting database (view description, example
    question -> SQL, glossary term, domain note), loaded from `sql/rahkaran/hints/out/hints.jsonl`.
    Global (not per project): it describes the company database, not user documents."""

    __tablename__ = "schema_hints"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Stable id from the corpus ("view:ledger_lines:1", "example:012", "note:fiscal_year", ...).
    hint_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    views: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # sha256 of the embedded text + embedding model: unchanged hints are not re-embedded on re-ingest.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dimensions), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class QueryStatus(str, enum.Enum):
    OK = "ok"
    REJECTED = "rejected"  # the generated SQL never passed validation
    ERROR = "error"  # execution failed (or no SQL could be generated)


class DbQueryLog(Base):
    """Every question asked through the connector: what was retrieved, the SQL that ran, the outcome
    and the user's feedback. This is the raw material for improving hints and views after launch."""

    __tablename__ = "db_query_logs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    hint_keys: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    sql_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[QueryStatus] = mapped_column(
        Enum(QueryStatus, name="db_query_status", values_callable=lambda e: [m.value for m in e]), nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # +1 helpful, -1 wrong/unhelpful, null = no feedback yet.
    feedback: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    feedback_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
