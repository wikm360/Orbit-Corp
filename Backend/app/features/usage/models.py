import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LlmUsage(Base):
    """One row per model call made on behalf of a user. The quota counter lives on `users`; this is the audit trail
    (it survives a quota reset, which only moves `users.token_period_start`)."""

    __tablename__ = "llm_usage"
    __table_args__ = (Index("ix_llm_usage_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)  # chat | sql | rerank | vr_agent | ocr | embedding
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # False for background work that is recorded but never limited (OCR, embeddings).
    counts_toward_quota: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
