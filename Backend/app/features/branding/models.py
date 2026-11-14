import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrgBranding(Base):
    """The organisation's identity (name, texts, three brand colours, logo). One row (id = 1) per deployment: every
    organisation runs its own deployment, so there is no tenant key. A missing row means the defaults in `service.DEFAULTS`."""

    __tablename__ = "org_branding"
    __table_args__ = (CheckConstraint("id = 1", name="ck_org_branding_single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_name: Mapped[str] = mapped_column(String(60), nullable=False)
    app_title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    tagline: Mapped[str] = mapped_column(String(120), nullable=False)
    product_label: Mapped[str] = mapped_column(String(40), nullable=False)
    login_headline: Mapped[str] = mapped_column(String(200), nullable=False)
    login_footer: Mapped[str] = mapped_column(String(200), nullable=False)
    color_brand: Mapped[str] = mapped_column(String(7), nullable=False)
    color_accent: Mapped[str] = mapped_column(String(7), nullable=False)
    color_highlight: Mapped[str] = mapped_column(String(7), nullable=False)
    logo_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    logo_content_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    logo_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
