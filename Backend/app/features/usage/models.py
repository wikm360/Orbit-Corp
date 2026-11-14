import uuid
from datetime import datetime

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, func, text
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
    # Cost of the call in micro-USD (1e-6 USD), snapshotted at record time from `model_prices` (a later price change never
    # rewrites history). tokens x USD-per-million-tokens is exactly micro-USD.
    cost_micro_usd: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"), nullable=False)
    # `user` = charged to the user's own quota; reserved for a future shared setup pool.
    billed_to: Mapped[str] = mapped_column(String(12), default="user", server_default=text("'user'"), nullable=False)  # user | org_setup
    # Pages for per-page priced calls (Mistral OCR); 0 for token-priced calls.
    pages: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelPrice(Base):
    """USD per one million tokens, keyed by the exact model name the gateway reports (the `model` column of `llm_usage`).
    Editable by super admins; unknown models are charged at the most expensive row (see `usage/pricing.py`)."""

    __tablename__ = "model_prices"

    model: Mapped[str] = mapped_column(String(200), primary_key=True)
    input_per_m: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    output_per_m: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    per_page_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)  # per-page priced models (Mistral OCR)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuotaPlan(Base):
    """Dollar caps of one role (`user` / `admin`), micro-USD. Super admins have no plan: they are never limited."""

    __tablename__ = "quota_plans"

    role: Mapped[str] = mapped_column(String(20), primary_key=True)
    five_hour_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    weekly_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monthly_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuotaConfig(Base):
    """Single row (id = 1). `enforced` false = shadow mode: cost is recorded and shown but nothing is blocked by it."""

    __tablename__ = "quota_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    # Shared setup pool: OCR/embedding of project uploads is charged here (billed_to='org_setup') instead of the uploader's quota.
    setup_pool_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    setup_pool_micro: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default=text("0"))
    # Whole-organisation cap per Jalali month (micro-USD, all users + pool); NULL = none.
    org_monthly_cap_micro: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
