"""Tables of the volume report module (`vr_*`). See .agents/flows/volume-report.md.

Only this module and the model registry import these; nothing else in Orbit depends on the module."""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base

settings = get_settings()

_NIL_UUID = "00000000-0000-0000-0000-000000000000"


def _enum(cls: type[enum.Enum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda enum_cls: [e.value for e in enum_cls])


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _fk(table: str, ondelete: str, *, nullable: bool = False, index: bool = False) -> Mapped[uuid.UUID]:
    return mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{table}.id", ondelete=ondelete), nullable=nullable, index=index)


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class SiteKind(str, enum.Enum):
    ROAD = "road"
    MINING = "mining"
    OTHER = "other"


class PeriodType(str, enum.Enum):
    WEEK = "week"
    MONTH = "month"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    AWAITING_USER = "awaiting_user"
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    PUBLISHED = "published"
    FAILED = "failed"


class FileStatus(str, enum.Enum):
    PENDING = "pending"
    PARSED = "parsed"
    FAILED = "failed"


class Dimension(str, enum.Enum):
    VOLUME = "volume"
    AREA = "area"
    LENGTH = "length"
    MASS = "mass"
    AREA_THICKNESS = "area_thickness"
    VOLUME_DISTANCE = "volume_distance"
    TIME = "time"
    NONPHYSICAL = "nonphysical"


class LexiconKind(str, enum.Enum):
    ITEM_HINT = "item_hint"
    ROLE = "role"
    HARD_EXCLUSION = "hard_exclusion"
    NOISE = "noise"


class Disposition(str, enum.Enum):
    COUNTED = "counted"
    EXCLUDED = "excluded"
    NONPHYSICAL = "nonphysical"
    UNMATCHED = "unmatched"
    NEEDS_INPUT = "needs_input"


class Role(str, enum.Enum):
    SUPPLY = "supply"
    EXECUTE = "execute"
    COMBINED = "combined"
    NA = "na"


class ExcludeReason(str, enum.Enum):
    SURCHARGE = "surcharge"
    DEMOLITION = "demolition"
    TRENCHING = "trenching"
    POINTING = "pointing"
    SITE_SETUP = "site_setup"
    DUPLICATE = "duplicate"
    HAUL_ONLY = "haul_only"
    NONPHYSICAL = "nonphysical"
    OTHER = "other"


class DecisionSource(str, enum.Enum):
    HUMAN = "human"
    SYSTEM = "system"
    AGENT = "agent"


class ClassificationSource(str, enum.Enum):
    MEMORY = "memory"
    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"


class Effect(str, enum.Enum):
    COUNTED = "counted"
    SUPPLY_IGNORED = "supply_ignored"
    SUPPLY_ONLY_NOT_COUNTED = "supply_only_not_counted"
    DUPLICATE_IGNORED = "duplicate_ignored"
    EXCLUDED = "excluded"
    UNMATCHED = "unmatched"
    NONPHYSICAL = "nonphysical"
    UNIT_MISMATCH = "unit_mismatch"
    NO_CONVERSION = "no_conversion"
    SITE_KIND_MISMATCH = "site_kind_mismatch"
    NEEDS_INPUT = "needs_input"


class ResultScope(str, enum.Enum):
    SITE = "site"
    COMPANY = "company"
    HOLDING = "holding"


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    AWAITING_USER = "awaiting_user"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QuestionKind(str, enum.Enum):
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    NUMBER = "number"
    TEXT = "text"
    CONFIRM_GROUP = "confirm_group"


class QuestionStatus(str, enum.Enum):
    OPEN = "open"
    ANSWERED = "answered"
    SKIPPED = "skipped"
    SUPERSEDED = "superseded"


class Company(Base):
    __tablename__ = "vr_companies"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    aliases: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = _now()


class Site(Base):
    """A workshop (کارگاه): one operational project of a company, found by name on the income sheets."""

    __tablename__ = "vr_sites"
    __table_args__ = (UniqueConstraint("company_id", "name_norm", name="uq_vr_sites_company_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    company_id: Mapped[uuid.UUID] = _fk("vr_companies", "CASCADE")
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    name_norm: Mapped[str] = mapped_column(String(500), nullable=False)
    aliases: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    kind: Mapped[SiteKind] = mapped_column(_enum(SiteKind, "vr_site_kind"), default=SiteKind.ROAD, nullable=False)
    # False until a human confirms `kind`; the publish gate (strict) refuses unconfirmed sites.
    kind_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = _now()


class Report(Base):
    __tablename__ = "vr_reports"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = _fk("projects", "CASCADE", index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    period_type: Mapped[PeriodType] = mapped_column(_enum(PeriodType, "vr_period_type"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_label: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        _enum(ReportStatus, "vr_report_status"), default=ReportStatus.DRAFT, nullable=False, index=True
    )
    progress: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    supersedes_id: Mapped[uuid.UUID | None] = _fk("vr_reports", "SET NULL", nullable=True)
    created_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalog_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReportFile(Base):
    __tablename__ = "vr_report_files"
    __table_args__ = (UniqueConstraint("report_id", "document_id", name="uq_vr_report_files_doc"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_id: Mapped[uuid.UUID] = _fk("vr_reports", "CASCADE", index=True)
    # SET NULL: deleting the source document must not break a report; filename/hash below are snapshots.
    document_id: Mapped[uuid.UUID | None] = _fk("documents", "SET NULL", nullable=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    company_id: Mapped[uuid.UUID] = _fk("vr_companies", "RESTRICT")
    status: Mapped[FileStatus] = mapped_column(_enum(FileStatus, "vr_file_status"), default=FileStatus.PENDING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sheet_log: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    suggested_company: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = _now()


class Line(Base):
    """A non-zero quantity row of an income sheet, exactly as read (no model ever sees `quantity`)."""

    __tablename__ = "vr_lines"
    __table_args__ = (UniqueConstraint("report_file_id", "sheet_name", "row_no", name="uq_vr_lines_row"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_file_id: Mapped[uuid.UUID] = _fk("vr_report_files", "CASCADE", index=True)
    site_id: Mapped[uuid.UUID] = _fk("vr_sites", "RESTRICT", index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    section_heading: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_norm: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    unit_raw: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    unit_norm: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_dim: Mapped[Dimension] = mapped_column(_enum(Dimension, "vr_dimension"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    flags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    group_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = _now()


class Item(Base):
    """Catalog entry (one of the reported activities). Editable: adding an item needs no code change."""

    __tablename__ = "vr_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title_fa: Mapped[str] = mapped_column(String(200), nullable=False)
    description_fa: Mapped[str] = mapped_column(Text, nullable=False, default="")
    dimension: Mapped[Dimension] = mapped_column(_enum(Dimension, "vr_dimension"), nullable=False)
    output_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    decimals: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_rollup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rollup_of: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    mining_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LexiconEntry(Base):
    __tablename__ = "vr_lexicon"

    id: Mapped[uuid.UUID] = _uuid_pk()
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    phrases: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    kind: Mapped[LexiconKind] = mapped_column(_enum(LexiconKind, "vr_lexicon_kind"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Decision(Base):
    """Memory of human-confirmed classifications. Only confirmed decisions or system rules are ever stored here."""

    __tablename__ = "vr_decisions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description_norm: Mapped[str] = mapped_column(Text, nullable=False)
    unit_norm: Mapped[str] = mapped_column(String(20), nullable=False)
    site_kind: Mapped[SiteKind] = mapped_column(_enum(SiteKind, "vr_site_kind"), nullable=False)
    disposition: Mapped[Disposition] = mapped_column(_enum(Disposition, "vr_disposition"), nullable=False)
    item_id: Mapped[uuid.UUID | None] = _fk("vr_items", "SET NULL", nullable=True)
    role: Mapped[Role] = mapped_column(_enum(Role, "vr_role"), default=Role.NA, nullable=False)
    exclude_reason: Mapped[ExcludeReason | None] = mapped_column(_enum(ExcludeReason, "vr_exclude_reason"), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dimensions), nullable=True)
    hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[DecisionSource] = mapped_column(_enum(DecisionSource, "vr_decision_source"), nullable=False)
    created_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_report_id: Mapped[uuid.UUID | None] = _fk("vr_reports", "SET NULL", nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    catalog_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = _now()


class Classification(Base):
    """The decision for one unique group (description + unit + site kind) within one report."""

    __tablename__ = "vr_classifications"
    __table_args__ = (UniqueConstraint("report_id", "group_key", name="uq_vr_classifications_group"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_id: Mapped[uuid.UUID] = _fk("vr_reports", "CASCADE", index=True)
    group_key: Mapped[str] = mapped_column(String(64), nullable=False)
    disposition: Mapped[Disposition] = mapped_column(_enum(Disposition, "vr_disposition"), nullable=False)
    item_id: Mapped[uuid.UUID | None] = _fk("vr_items", "SET NULL", nullable=True)
    role: Mapped[Role] = mapped_column(_enum(Role, "vr_role"), default=Role.NA, nullable=False)
    exclude_reason: Mapped[ExcludeReason | None] = mapped_column(_enum(ExcludeReason, "vr_exclude_reason"), nullable=True)
    source: Mapped[ClassificationSource] = mapped_column(_enum(ClassificationSource, "vr_class_source"), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_id: Mapped[uuid.UUID | None] = _fk("vr_decisions", "SET NULL", nullable=True)
    decided_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LineResult(Base):
    """Computed outcome of each line; rebuilt on every resolve (never edited by hand)."""

    __tablename__ = "vr_line_results"

    line_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("vr_lines.id", ondelete="CASCADE"), primary_key=True
    )
    effect: Mapped[Effect] = mapped_column(_enum(Effect, "vr_effect"), nullable=False)
    item_id: Mapped[uuid.UUID | None] = _fk("vr_items", "SET NULL", nullable=True)
    output_qty: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    output_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    unconfirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Conversion(Base):
    """Unit-conversion parameter (density, thickness, cross-section). Priority: site+item > item > global."""

    __tablename__ = "vr_conversions"
    __table_args__ = (
        Index(
            "uq_vr_conversions_scope",
            "key",
            text(f"coalesce(item_id, '{_NIL_UUID}'::uuid)"),
            text(f"coalesce(site_id, '{_NIL_UUID}'::uuid)"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    item_id: Mapped[uuid.UUID | None] = _fk("vr_items", "CASCADE", nullable=True)
    site_id: Mapped[uuid.UUID | None] = _fk("vr_sites", "CASCADE", nullable=True)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Result(Base):
    __tablename__ = "vr_results"
    __table_args__ = (
        Index(
            "uq_vr_results_cell",
            "report_id",
            "scope",
            text(f"coalesce(company_id, '{_NIL_UUID}'::uuid)"),
            text(f"coalesce(site_id, '{_NIL_UUID}'::uuid)"),
            "item_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_id: Mapped[uuid.UUID] = _fk("vr_reports", "CASCADE", index=True)
    scope: Mapped[ResultScope] = mapped_column(_enum(ResultScope, "vr_result_scope"), nullable=False)
    company_id: Mapped[uuid.UUID | None] = _fk("vr_companies", "CASCADE", nullable=True)
    site_id: Mapped[uuid.UUID | None] = _fk("vr_sites", "CASCADE", nullable=True)
    item_id: Mapped[uuid.UUID] = _fk("vr_items", "CASCADE")
    qty: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    n_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_unconfirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Snapshot(Base):
    __tablename__ = "vr_snapshots"

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_id: Mapped[uuid.UUID] = _fk("vr_reports", "CASCADE")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    catalog_version: Mapped[int] = mapped_column(Integer, nullable=False)
    catalog_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (UniqueConstraint("report_id", name="uq_vr_snapshots_report"),)


class AgentRun(Base):
    __tablename__ = "vr_agent_runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_id: Mapped[uuid.UUID] = _fk("vr_reports", "CASCADE", index=True)
    pass_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RunStatus] = mapped_column(_enum(RunStatus, "vr_run_status"), default=RunStatus.RUNNING, nullable=False)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    steps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentStep(Base):
    """Audit trail of tool calls. Never holds quantities."""

    __tablename__ = "vr_agent_steps"

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = _fk("vr_agent_runs", "CASCADE", index=True)
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = _now()


class Question(Base):
    __tablename__ = "vr_questions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_id: Mapped[uuid.UUID] = _fk("vr_reports", "CASCADE", index=True)
    run_id: Mapped[uuid.UUID | None] = _fk("vr_agent_runs", "SET NULL", nullable=True)
    kind: Mapped[QuestionKind] = mapped_column(_enum(QuestionKind, "vr_question_kind"), nullable=False)
    spec: Mapped[dict] = mapped_column(JSONB, nullable=False)
    group_keys: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    status: Mapped[QuestionStatus] = mapped_column(
        _enum(QuestionStatus, "vr_question_status"), default=QuestionStatus.OPEN, nullable=False
    )
    answer: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    answered_by: Mapped[uuid.UUID | None] = _fk("users", "SET NULL", nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = _now()


class Setting(Base):
    __tablename__ = "vr_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | int | str | list] = mapped_column(JSONB, nullable=False)
