import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.features.volume_report.models import ExcludeReason, PeriodType, ReportStatus, SiteKind


class ReportCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    period_type: PeriodType
    period_start: date
    period_end: date
    period_label: str = Field(min_length=1, max_length=100)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    period_type: PeriodType
    period_start: date
    period_end: date
    period_label: str
    status: ReportStatus
    progress: dict
    version: int
    supersedes_id: uuid.UUID | None
    published_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class PvEntry(BaseModel):
    company_id: uuid.UUID
    project: str = Field(min_length=1, max_length=1000)
    pv: Decimal | None = Field(default=None, ge=0)  # rial; None / omitted = no value for this project


class PvUpdate(BaseModel):
    mode: Literal["auto", "manual"]
    values: list[PvEntry] = Field(default_factory=list, max_length=500)


class FileSelection(BaseModel):
    document_id: uuid.UUID
    company_id: uuid.UUID
    kind: Literal["period", "monthly_plan", "monthly_pv"] = "period"
    plan_month: int | None = Field(default=None, ge=1, le=12)  # Jalali month of a monthly forecast; detected from the title when omitted
    plan_year: int | None = Field(default=None, ge=1300, le=1500)  # default: the occurrence closest to the report period


class FilesUpdate(BaseModel):
    files: list[FileSelection] = Field(max_length=50)


class FilesAdd(BaseModel):
    files: list[FileSelection] = Field(min_length=1, max_length=50)


class ConfirmItem(BaseModel):
    group_key: str = Field(min_length=64, max_length=64)
    item_key: str | None = None
    exclude_reason: ExcludeReason | None = None
    # Only needed to mark a group nonphysical/unmatched explicitly; implied by item_key / exclude_reason otherwise.
    disposition: Literal["unmatched", "nonphysical"] | None = None
    role: Literal["supply", "execute", "combined", "na"] = "na"
    remember_scope: Literal["global", "line"] = "global"


class ConfirmRequest(BaseModel):
    items: list[ConfirmItem] = Field(min_length=1, max_length=200)


class CompanyWrite(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    aliases: list[str] = []
    is_active: bool = True


class SiteUpdate(BaseModel):
    kind: SiteKind | None = None
    kind_confirmed: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=500)
    aliases: list[str] | None = None
    is_active: bool | None = None


class ConversionWrite(BaseModel):
    key: Literal["density_t_per_m3", "thickness_m", "cross_section_m2"]
    item_key: str | None = None
    site_id: uuid.UUID | None = None
    value: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=32)
    note: str | None = None


class ItemRuleWrite(BaseModel):
    item_key: str
    site_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    phrases: list[str] = Field(min_length=1, max_length=50)
    source_unit: str = Field(min_length=1, max_length=20)
    factor: float = Field(gt=0)
    priority: int = 0
    note: str | None = None
    is_active: bool = True

    @field_validator("phrases")
    @classmethod
    def _clean_phrases(cls, v):
        cleaned = [p.strip() for p in v if p.strip()]
        if not cleaned or any(len(p) > 80 for p in cleaned):
            raise ValueError("phrases must be non-empty and at most 80 characters")
        return cleaned


class ItemWrite(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    title_fa: str = Field(min_length=1, max_length=200)
    description_fa: str = Field(default="", max_length=2000)
    dimension: Literal["volume", "area", "length", "mass", "area_thickness", "volume_distance", "time", "nonphysical"]
    output_unit: str = Field(min_length=1, max_length=20)
    decimals: int = Field(default=2, ge=0, le=6)
    sort_order: int = 0
    is_rollup: bool = False
    rollup_of: list[str] = []
    mining_only: bool = False
    is_active: bool = True


class LexiconWrite(BaseModel):
    token: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    kind: Literal["item_hint", "role", "hard_exclusion", "noise"]
    phrases: list[str] = Field(min_length=1, max_length=100)
    is_active: bool = True

    @field_validator("phrases")
    @classmethod
    def _clean(cls, v):
        cleaned = [p.strip() for p in v if p.strip()]
        if not cleaned or any(len(p) > 80 for p in cleaned):
            raise ValueError("phrases must be non-empty and at most 80 characters")
        return cleaned


class CompanyNarrativeEntry(BaseModel):
    company_name: str | None = None
    raw_text: str = ""
    items: list[str] = []
    updated_at: str | None = None


class NarrativesUpdate(BaseModel):
    narratives: dict[str, CompanyNarrativeEntry]


class GenerateNarrativeRequest(BaseModel):
    company_id: str | None = None
    company_name: str
    raw_text: str
