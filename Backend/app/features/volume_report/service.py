"""Reports, files, classification review, results, publish. Services commit themselves (project convention)."""

import asyncio
import hashlib
import json
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.features.documents.models import Document, DocumentStatus
from app.features.projects.models import Project
from app.features.volume_report import compute, jalali, memory
from app.features.volume_report.extraction.normalize import Lexicon, LexiconEntry as LexEntry, normalize_text
from app.features.volume_report.extraction.period_range import find_period_range, resolve_period
from app.features.volume_report.models import (
    Classification, ClassificationSource, Company, Conversion, Decision, EvmRow, FileStatus, EvmExclusion, IncomeTotal, ItemRule, PvPlanRow, PvOverride, DecisionSource, Disposition, Effect,
    Dimension, ExcludeReason, Item, Line, LexiconKind, LineResult, Question, QuestionStatus, Report, ReportFile, ReportStatus, Result,
    ResultScope, Role, Site, SiteKind, Snapshot, LexiconEntry,
)
from app.features.volume_report.schemas import ConfirmItem, FileSelection, ReportCreate
from app.features.volume_report.seed import bump_catalog_version, current_catalog_version, ensure_seeded

logger = logging.getLogger(__name__)
settings = get_settings()

EXCEL_SUFFIXES = {".xls", ".xlsx", ".xlsm", ".xlsb", ".pdf"}
_FROZEN = (ReportStatus.PUBLISHED, ReportStatus.PROCESSING)


# ---- access ------------------------------------------------------------------------------------------------------

async def check_project_access(db: AsyncSession, context: UserContext, project_id: uuid.UUID) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    if not (context.is_project_member(project.id) or context.leads_team(project.team_id)):
        raise ForbiddenError("You are not a member of this project")
    return project


async def get_report_for_member(db: AsyncSession, context: UserContext, report_id: uuid.UUID) -> Report:
    report = await db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found")
    await check_project_access(db, context, report.project_id)
    return report


def require_settings_editor(context: UserContext) -> None:
    if not (context.is_admin or context.led_team_ids):
        raise ForbiddenError("Team leader or admin privileges required")


def _require_editable(report: Report) -> None:
    if report.status in _FROZEN:
        raise ConflictError(f"A {report.status.value} report cannot be changed")


# ---- reports -----------------------------------------------------------------------------------------------------

async def create_report(db: AsyncSession, context: UserContext, payload: ReportCreate) -> Report:
    await check_project_access(db, context, payload.project_id)
    if payload.period_end < payload.period_start:
        raise BadRequestError("period_end is before period_start")
    await ensure_seeded(db)
    report = Report(**payload.model_dump(), created_by=context.id, progress={})
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def list_reports(db: AsyncSession, context: UserContext, project_id: uuid.UUID, status: ReportStatus | None) -> list[Report]:
    await check_project_access(db, context, project_id)
    query = select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc())
    if status is not None:
        query = query.where(Report.status == status)
    return list((await db.execute(query)).scalars())


async def delete_report(db: AsyncSession, report: Report) -> None:
    """Any report can be deleted (including published ones); children cascade in the DB, and learned decisions survive
    with `source_report_id` set to NULL. Only a report whose pipeline is running is refused."""
    if report.status == ReportStatus.PROCESSING:
        raise ConflictError("A report that is being processed cannot be deleted")
    await db.delete(report)
    await db.commit()


def resolve_document_path(document: Document) -> str:
    """The path always comes from the DB row and must stay inside UPLOAD_DIR (defence against a tampered row)."""
    root = Path(settings.upload_dir).resolve()
    path = Path(document.file_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise BadRequestError("Source file is not available")
    return str(path)


# ---- monthly forecast: spread over the days of the next period ---------------------------------------------------

def next_period(report: Report) -> tuple[date, date]:
    """The period the forecast is for: right after this one, same length."""
    length = (report.period_end - report.period_start).days + 1
    start = report.period_end + timedelta(days=1)
    return start, start + timedelta(days=length - 1)


def plan_info(report: Report, f: ReportFile) -> dict | None:
    """For a monthly file: how many days of the period it serves fall inside its month, and the resulting share of the month.
    monthly_plan (volume forecast) serves the NEXT period; monthly_pv (PV plan) serves the report's OWN period."""
    if f.kind not in ("monthly_plan", "monthly_pv") or f.plan_start is None or f.plan_end is None:
        return None
    if f.kind == "monthly_pv":
        start, end = report.period_start, report.period_end
    else:
        start, end = next_period(report)
    overlap = max(0, (min(end, f.plan_end) - max(start, f.plan_start)).days + 1)
    plan_days = (f.plan_end - f.plan_start).days + 1
    period_days = (end - start).days + 1
    return {"plan_start": f.plan_start, "plan_end": f.plan_end, "period_start": start, "period_end": end, "overlap_days": overlap,
            "plan_days": plan_days, "period_days": period_days, "factor": f"{Decimal(overlap) / Decimal(plan_days):.6f}"}


def plan_factor(report: Report, f: ReportFile) -> Decimal:
    info = plan_info(report, f)
    return Decimal(1) if info is None else Decimal(info["overlap_days"]) / Decimal(info["plan_days"])


# ---- which period is a forecast file for? ---------------------------------------------------------------------------
# A forecast file is the forecast of the report's OWN period (written the week before: it only supplies PV) or the plan of the
# period AFTER it (its volumes are "next week's plan"). Titles are often last week's copy and file names are named after the week
# they were sent, so neither is trusted alone: a hint that names neither this period nor the next one is ignored as stale, and two
# hints that disagree are reported (the user then picks `forecast_for`).

_BARE_RANGE = re.compile(r"(?<!\d)(\d{1,2})\s*(?:[-–]|الی|تا)\s*(\d{1,2})(?!\d)")
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _filename_period(report: Report, filename: str) -> tuple[date, date] | None:
    stem = Path(filename).stem.translate(_DIGITS)
    named = find_period_range(stem)
    if named is not None:
        return resolve_period(named, report.period_end)
    match = _BARE_RANGE.search(stem)  # "18-24" without the month: read it in the month of this period / the next one
    if match is None:
        return None
    first, last = int(match.group(1)), int(match.group(2))
    if not 1 <= first <= last <= 31:
        return None
    for anchor in (report.period_start, next_period(report)[0]):
        year, month, _ = jalali.to_jalali(anchor)
        try:
            span = (jalali.to_gregorian(year, month, first), jalali.to_gregorian(year, month, last))
        except ValueError:
            continue
        if span in ((report.period_start, report.period_end), next_period(report)):
            return span
    return None


def forecast_scope(report: Report, f: ReportFile, has_actual: bool = False) -> dict:
    """{"scope": "this" | "next", "source": override | title | filename | title+filename | ambiguous | mixed | unknown, ...hints}.
    this = the forecast of the report's own period (PV only); next = the plan of the period after it (also the default when nothing
    can be told, which is how every forecast was read before). A file that also carries ACTUAL sheets is a normal report whose
    planned sheets are the next period's, whatever its titles say."""
    this, following = (report.period_start, report.period_end), next_period(report)
    title = (f.title_period_start, f.title_period_end) if f.title_period_start and f.title_period_end else None
    name = _filename_period(report, f.filename)
    hints = {"title_period": title, "filename_period": name}
    if f.forecast_for in ("this_period", "next_period"):
        return {"scope": "this" if f.forecast_for == "this_period" else "next", "source": "override", **hints}
    if has_actual:
        return {"scope": "next", "source": "mixed", **hints}
    votes = {label: "this" if period == this else "next" for label, period in (("title", title), ("filename", name)) if period in (this, following)}
    if not votes:
        return {"scope": "next", "source": "unknown", **hints}
    if len(set(votes.values())) > 1:
        return {"scope": "next", "source": "ambiguous", **hints}
    return {"scope": next(iter(votes.values())), "source": "+".join(votes), **hints}


def is_this_period_forecast(report: Report, f: ReportFile, has_actual: bool = False) -> bool:
    return f.kind == "period" and forecast_scope(report, f, has_actual)["scope"] == "this"


async def _build_file_selections(
    db: AsyncSession, report: Report, selections: list[FileSelection]
) -> tuple[dict[uuid.UUID, ReportFile], dict[uuid.UUID, str | None], dict[uuid.UUID, tuple[str, int | None]]]:
    from app.features.volume_report.extraction.runner import suggest_company_for_file, suggest_kind_for_file

    _require_editable(report)
    wanted: dict[uuid.UUID, ReportFile] = {}
    suggestions: dict[uuid.UUID, str | None] = {}
    kind_suggestions: dict[uuid.UUID, tuple[str, int | None]] = {}
    for sel in selections:
        document = await db.get(Document, sel.document_id)
        if document is None or document.project_id != report.project_id:
            raise NotFoundError("Document not found")
        if document.status != DocumentStatus.READY:
            raise BadRequestError("Document is not ready")
        if Path(document.filename).suffix.lower() not in EXCEL_SUFFIXES:
            raise BadRequestError("Only .xls, .xlsx, .xlsm, .xlsb and .pdf files are supported")
        company = await db.get(Company, sel.company_id)
        if company is None or not company.is_active:
            raise NotFoundError("Company not found")
        if sel.document_id in wanted:
            raise BadRequestError("Duplicate document in the selection")
        wanted[sel.document_id] = ReportFile(
            report_id=report.id, document_id=document.id, filename=document.filename,
            content_hash=document.content_hash, company_id=company.id, kind=sel.kind, forecast_for=sel.forecast_for,
        )
        try:
            path = resolve_document_path(document)
            suggestions[document.id] = await asyncio.to_thread(suggest_company_for_file, path)
            kind_suggestions[document.id] = await asyncio.to_thread(suggest_kind_for_file, path)
        except Exception:  # a suggestion is optional; the run reports real read errors
            suggestions.setdefault(document.id, None)
            kind_suggestions.setdefault(document.id, ("period", None))
        if sel.kind in ("monthly_plan", "monthly_pv"):
            month = sel.plan_month or kind_suggestions.get(document.id, ("period", None))[1]
            if month is None:
                raise BadRequestError("plan_month is required for a monthly forecast (it is not named in the file's title)")
            start, end = jalali.month_range(sel.plan_year, month) if sel.plan_year else jalali.nearest_month_range(month, report.period_end)
            wanted[sel.document_id].plan_start, wanted[sel.document_id].plan_end = start, end
    return wanted, suggestions, kind_suggestions


def _apply_file_selection(existing_file: ReportFile, updated: ReportFile) -> None:
    existing_file.company_id = updated.company_id
    existing_file.kind = updated.kind
    existing_file.forecast_for = updated.forecast_for
    existing_file.plan_start = updated.plan_start
    existing_file.plan_end = updated.plan_end


async def _serialize_report_files(
    db: AsyncSession,
    report: Report,
    suggestions: dict[uuid.UUID, str | None] | None = None,
    kind_suggestions: dict[uuid.UUID, tuple[str, int | None]] | None = None,
) -> list[dict]:
    suggestions = suggestions or {}
    kind_suggestions = kind_suggestions or {}
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id).order_by(ReportFile.created_at))).scalars().all()
    return [
        {"id": f.id, "document_id": f.document_id, "filename": f.filename, "company_id": f.company_id,
         "status": f.status.value, "error_message": f.error_message,
         "suggested_company": suggestions.get(f.document_id) or f.suggested_company,
         "kind": f.kind, "forecast_for": f.forecast_for, "plan_start": f.plan_start, "plan_end": f.plan_end,
         "plan_month": jalali.to_jalali(f.plan_start)[1] if f.kind in ("monthly_plan", "monthly_pv") and f.plan_start else None,
         "plan": plan_info(report, f),
         "suggested_kind": kind_suggestions.get(f.document_id, ("period", None))[0],
         "suggested_plan_month": kind_suggestions.get(f.document_id, ("period", None))[1]}
        for f in files
    ]


async def set_files(db: AsyncSession, report: Report, selections: list[FileSelection]) -> list[dict]:
    wanted, suggestions, kind_suggestions = await _build_file_selections(db, report, selections)
    existing = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars().all()
    keep = {f.document_id: f for f in existing if f.document_id in wanted}
    for f in existing:
        if f.document_id not in wanted:
            await db.delete(f)
    for doc_id, new in wanted.items():
        if doc_id in keep:
            _apply_file_selection(keep[doc_id], new)
        else:
            db.add(new)
    await db.commit()
    return await _serialize_report_files(db, report, suggestions, kind_suggestions)


async def add_files(db: AsyncSession, report: Report, selections: list[FileSelection]) -> list[dict]:
    """Appends new files (or updates metadata for already attached ones) without removing existing files or human work."""
    wanted, suggestions, kind_suggestions = await _build_file_selections(db, report, selections)
    existing_list = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars().all()
    existing = {f.document_id: f for f in existing_list if f.document_id is not None}
    new_count = sum(1 for doc_id in wanted if doc_id not in existing)
    if len(existing_list) + new_count > 50:
        raise BadRequestError("Maximum 50 files per report exceeded")
    for doc_id, new in wanted.items():
        if doc_id in existing:
            _apply_file_selection(existing[doc_id], new)
        else:
            db.add(new)
    await db.commit()
    return await _serialize_report_files(db, report, suggestions, kind_suggestions)


async def remove_file(db: AsyncSession, report: Report, file_id: uuid.UUID) -> None:
    _require_editable(report)
    rf = await db.get(ReportFile, file_id)
    if rf is None or rf.report_id != report.id:
        raise NotFoundError("File not found")
    await db.delete(rf)
    await db.commit()


def _enqueue(report_id: uuid.UUID, mode: str = "full", user_id: uuid.UUID | None = None) -> None:
    from redis import Redis
    from rq import Queue

    queue = Queue(settings.vr_queue_name, connection=Redis.from_url(settings.redis_url))  # lazy: never at import time
    queue.enqueue("app.features.volume_report.pipeline.run_report_sync", report_id, mode, user_id, job_timeout=settings.vr_job_timeout_seconds)


async def request_run(db: AsyncSession, report: Report, mode: str = "full", user_id: uuid.UUID | None = None) -> Report:
    if mode == "continue" and report.status not in (ReportStatus.AWAITING_USER, ReportStatus.NEEDS_REVIEW, ReportStatus.READY):
        raise ConflictError("Nothing to continue: run the report first")
    if not (await db.scalar(select(func.count()).select_from(ReportFile).where(ReportFile.report_id == report.id))):
        raise BadRequestError("Select at least one file first")
    # Atomic claim: two concurrent requests cannot both move the report into `processing`.
    # A `processing` report whose worker died (no progress update for twice the job timeout) may be claimed again.
    stale = func.now() - timedelta(seconds=settings.vr_job_timeout_seconds * 2)
    claimed = await db.execute(
        update(Report).where(
            Report.id == report.id, Report.status != ReportStatus.PUBLISHED,
            or_(Report.status != ReportStatus.PROCESSING, Report.updated_at < stale),
        )
        .values(status=ReportStatus.PROCESSING, progress={"step": "queued", "done": 0, "total": 0, "message": ""}, error_message=None)
        .returning(Report.id)
    )
    if claimed.first() is None:
        await db.rollback()
        raise ConflictError("The report is running or already published")
    await db.commit()
    try:
        _enqueue(report.id, mode, user_id)
    except Exception as exc:
        await db.execute(update(Report).where(Report.id == report.id).values(status=ReportStatus.FAILED, error_message="Could not queue the job"))
        await db.commit()
        logger.exception("Could not enqueue volume report %s", report.id)
        raise ConflictError("Could not queue the job") from exc
    await db.refresh(report)
    return report


# ---- shared loaders ----------------------------------------------------------------------------------------------

async def load_lexicon(db: AsyncSession) -> Lexicon:
    rows = (await db.execute(select(LexiconEntry).where(LexiconEntry.is_active.is_(True)))).scalars()
    return Lexicon(LexEntry(r.token, r.kind.value, tuple(r.phrases)) for r in rows)


async def _report_lines(db: AsyncSession, report_id: uuid.UUID) -> list[tuple[Line, Site]]:
    rows = await db.execute(
        select(Line, Site).join(ReportFile, ReportFile.id == Line.report_file_id).join(Site, Site.id == Line.site_id)
        .where(ReportFile.report_id == report_id).order_by(ReportFile.created_at, Line.sheet_name, Line.row_no)
    )
    return [(line, site) for line, site in rows.all()]


MAX_GROUP_LOCATIONS = 25
MAX_LOCATION_ROWS = 8


async def _report_lines_with_sources(db: AsyncSession, report_id: uuid.UUID) -> list[tuple[Line, Site, str, str]]:
    rows = await db.execute(
        select(Line, Site, ReportFile.filename, Company.name)
        .join(ReportFile, ReportFile.id == Line.report_file_id)
        .join(Site, Site.id == Line.site_id)
        .join(Company, Company.id == ReportFile.company_id)
        .where(ReportFile.report_id == report_id)
        .order_by(ReportFile.created_at, Line.sheet_name, Line.row_no)
    )
    return [(line, site, filename, company_name) for line, site, filename, company_name in rows.all()]


async def _report_file_names(db: AsyncSession, report_id: uuid.UUID) -> dict[str, tuple[str, str]]:
    rows = await db.execute(
        select(ReportFile.id, ReportFile.filename, Company.name)
        .join(Company, Company.id == ReportFile.company_id)
        .where(ReportFile.report_id == report_id)
    )
    return {str(rf_id): (filename, company_name) for rf_id, filename, company_name in rows.all()}


def summarize_locations(
    records: list[tuple[str, str | None, str | None, str | None, str | None, int | None]],
    *,
    max_locations: int = MAX_GROUP_LOCATIONS,
    max_rows: int = MAX_LOCATION_ROWS,
) -> list[dict]:
    """Deduplicates line coordinates by (filename, company, site, sheet, section) with sample row numbers."""
    buckets: dict[tuple[str, str | None, str | None, str | None, str | None], dict] = {}
    for filename, company, site, sheet, section, row_no in records:
        key = (filename, company, site, sheet, section)
        entry = buckets.get(key)
        if entry is None:
            if len(buckets) >= max_locations:
                continue
            entry = {
                "filename": filename,
                "company": company,
                "site": site,
                "sheet": sheet,
                "section": section,
                "row_nos": [],
                "_rows_seen": set(),
                "n_lines": 0,
            }
            buckets[key] = entry
        entry["n_lines"] += 1
        if row_no is not None and row_no not in entry["_rows_seen"]:
            entry["_rows_seen"].add(row_no)
            entry["row_nos"].append(row_no)
    out = []
    for entry in buckets.values():
        entry.pop("_rows_seen")
        entry["row_nos"] = sorted(entry["row_nos"])[:max_rows]
        out.append(entry)
    return out


# ---- resolve / convert / aggregate -------------------------------------------------------------------------------

async def recompute(db: AsyncSession, report: Report) -> list[dict]:
    """Rebuilds `vr_line_results` and `vr_results` from lines + classifications. Returns the gate causes."""
    items = {i.id: i for i in (await db.execute(select(Item))).scalars()}
    item_in = {i.key: compute.ItemIn(i.key, i.output_unit, i.mining_only, i.is_rollup, list(i.rollup_of)) for i in items.values()}
    pairs = await _report_lines(db, report.id)
    files = {f.id: f for f in (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars()}
    factors = {fid: plan_factor(report, f) for fid, f in files.items()}
    # A site with a forecast of its own (a normal file) never takes the monthly one; otherwise a monthly forecast counts for the
    # days of the next period inside its month (a superseded line stays, with quantity 0, so every line keeps a result).
    # The "برنامه" shown beside the actual volumes is the forecast OF THIS period (written last week; it is also the PV source). A
    # site that has one takes no other forecast into its plan (a next-period forecast in the same report stays, with quantity 0,
    # for the next report); a site without one keeps the next-period forecast as before.
    actual_files = {l.report_file_id for l, _ in pairs if l.basis == "actual"}
    this_period_files = {fid for fid, f in files.items() if is_this_period_forecast(report, f, fid in actual_files)}
    sites_with_this = {s.id for l, s in pairs if l.basis == "planned" and l.report_file_id in this_period_files}
    own_plan_sites = {s.id for l, s in pairs if l.basis == "planned" and files[l.report_file_id].kind == "period"}

    def effective_quantity(l: Line, s: Site) -> Decimal:
        if l.basis == "planned" and files[l.report_file_id].kind == "monthly_plan":
            return Decimal(0) if s.id in own_plan_sites else l.quantity * factors[l.report_file_id]
        if l.basis == "planned" and l.report_file_id not in this_period_files and s.id in sites_with_this:
            return Decimal(0)
        return l.quantity

    lines_in = [
        compute.LineIn(str(l.id), str(s.id), s.kind.value, l.group_key, l.unit_norm, effective_quantity(l, s), bool(l.flags.get("negative_qty")), l.description_norm)
        for l, s in pairs
    ]
    basis_of = {str(l.id): l.basis for l, _ in pairs}
    classes: dict[str, compute.ClassIn] = {}
    for c in (await db.execute(select(Classification).where(Classification.report_id == report.id))).scalars():
        classes[c.group_key] = compute.ClassIn(
            c.disposition.value, items[c.item_id].key if c.item_id in items else None, c.role.value,
            c.exclude_reason.value if c.exclude_reason else None, c.confirmed,
        )
    params = [
        {"key": p.key, "item_key": items[p.item_id].key if p.item_id in items else None,
         "site_id": str(p.site_id) if p.site_id else None, "value": p.value}
        for p in (await db.execute(select(Conversion))).scalars()
    ]
    rules = [
        compute.RuleIn(str(r.id), items[r.item_id].key, [normalize_text(p) for p in r.phrases], r.source_unit, Decimal(r.factor),
                       str(r.site_id) if r.site_id else None, r.priority, r.note)
        for r in (await db.execute(select(ItemRule).where(ItemRule.is_active.is_(True)))).scalars() if r.item_id in items
    ]
    # Actual and planned lines are resolved and aggregated separately: a forecast must never feed the actual pool
    # (supply/execution pairing, rollups) or the other way round. Classifications are shared (same group keys).
    site_company = {str(s.id): str(s.company_id) for _, s in pairs}
    outs: list[compute.LineOut] = []
    results: list[tuple[str, compute.ResultOut]] = []
    for basis in ("actual", "planned"):
        subset = [l for l in lines_in if basis_of[l.id] == basis]
        if not subset:
            continue
        part = compute.resolve_lines(subset, classes, item_in, params, rules)
        if (error := compute.check_conservation(subset, part)) is not None:
            raise RuntimeError(error)
        outs.extend(part)
        results.extend((basis, r) for r in compute.aggregate(subset, part, item_in, site_company))

    key_to_id = {i.key: i.id for i in items.values()}
    line_ids = [l.id for l, _ in pairs]
    if line_ids:
        await db.execute(delete(LineResult).where(LineResult.line_id.in_(line_ids)))
    await db.execute(delete(Result).where(Result.report_id == report.id))
    for out in outs:
        db.add(LineResult(
            line_id=uuid.UUID(out.line_id), effect=Effect(out.effect), item_id=key_to_id.get(out.item_key),
            output_qty=out.output_qty, output_unit=out.output_unit, note=out.note, unconfirmed=out.unconfirmed,
        ))
    for basis, r in results:
        db.add(Result(
            report_id=report.id, basis=basis, scope=ResultScope(r.scope), company_id=uuid.UUID(r.company_id) if r.company_id else None,
            site_id=uuid.UUID(r.site_id) if r.site_id else None, item_id=key_to_id[r.item_key], qty=r.qty, unit=r.unit,
            n_lines=r.n_lines, has_unconfirmed=r.has_unconfirmed,
        ))
    report.catalog_version = await current_catalog_version(db)
    await db.flush()
    return await gate_causes(db, report)


async def gate_causes(db: AsyncSession, report: Report) -> list[dict]:
    causes: list[dict] = []

    async def count(query) -> int:
        return int(await db.scalar(query) or 0)

    line_result = select(func.count()).select_from(LineResult).join(Line, Line.id == LineResult.line_id).join(
        ReportFile, ReportFile.id == Line.report_file_id).where(ReportFile.report_id == report.id)
    pending_files = await count(select(func.count()).select_from(ReportFile).where(
        ReportFile.report_id == report.id, ReportFile.status == FileStatus.PENDING))
    if pending_files:
        causes.append({"code": "pending_files", "count": pending_files})
    open_q = await count(select(func.count()).select_from(Question).where(Question.report_id == report.id, Question.status == QuestionStatus.OPEN))
    if open_q:
        causes.append({"code": "open_questions", "count": open_q})
    unconfirmed = await count(line_result.where(LineResult.effect == Effect.COUNTED, LineResult.unconfirmed.is_(True)))
    if unconfirmed:
        causes.append({"code": "unconfirmed_counted", "count": unconfirmed})
    for code, effect in (("needs_input", Effect.NEEDS_INPUT), ("unit_mismatch", Effect.UNIT_MISMATCH), ("no_conversion", Effect.NO_CONVERSION)):
        n = await count(line_result.where(LineResult.effect == effect))
        if n:
            causes.append({"code": code, "count": n})
    sites = await count(
        select(func.count(func.distinct(Site.id))).select_from(Line).join(Site, Site.id == Line.site_id)
        .join(ReportFile, ReportFile.id == Line.report_file_id)
        .where(ReportFile.report_id == report.id, Site.kind_confirmed.is_(False))
    )
    if sites:
        causes.append({"code": "site_kind_unconfirmed", "count": sites})
    return causes


def derive_status(causes: list[dict]) -> ReportStatus:
    if any(c["code"] == "open_questions" for c in causes):
        return ReportStatus.AWAITING_USER
    return ReportStatus.NEEDS_REVIEW if causes else ReportStatus.READY


async def recompute_and_save(db: AsyncSession, report: Report) -> list[dict]:
    causes = await recompute(db, report)
    if report.status in (ReportStatus.READY, ReportStatus.NEEDS_REVIEW, ReportStatus.AWAITING_USER):
        report.status = derive_status(causes)
    await db.commit()
    return causes


# ---- review ------------------------------------------------------------------------------------------------------

async def list_groups(db: AsyncSession, report: Report, state: str) -> list[dict]:
    pairs = await _report_lines_with_sources(db, report.id)
    classes = {c.group_key: c for c in (await db.execute(select(Classification).where(Classification.report_id == report.id))).scalars()}
    item_keys = {i.id: i.key for i in (await db.execute(select(Item))).scalars()}
    groups: dict[str, dict] = {}
    raw_locs: dict[str, list[tuple[str, str | None, str | None, str | None, str | None, int | None]]] = {}
    for line, site, filename, company_name in pairs:
        g = groups.setdefault(line.group_key, {
            "group_key": line.group_key, "description": line.description_raw, "unit": line.unit_norm,
            "site_kind": site.kind.value, "n_lines": 0, "section_headings": [], "tokens": line.tokens,
            "total_quantity": Decimal(0), "planned_quantity": Decimal(0),
        })
        g["n_lines"] += 1
        g["planned_quantity" if line.basis == "planned" else "total_quantity"] += line.quantity
        if line.section_heading and line.section_heading not in g["section_headings"] and len(g["section_headings"]) < 3:
            g["section_headings"].append(line.section_heading)
        raw_locs.setdefault(line.group_key, []).append(
            (filename, company_name, site.name, line.sheet_name, line.section_heading, line.row_no)
        )
    out = []
    for key, g in groups.items():
        c = classes.get(key)
        g.update(
            disposition=c.disposition.value if c else None, item_key=item_keys.get(c.item_id) if c else None,
            role=c.role.value if c else None, exclude_reason=c.exclude_reason.value if c and c.exclude_reason else None,
            source=c.source.value if c else None, confirmed=c.confirmed if c else False, reason=c.reason if c else None,
            confidence=c.confidence if c else None,
            total_quantity=f"{g['total_quantity']:f}", planned_quantity=f"{g['planned_quantity']:f}",
            locations=summarize_locations(raw_locs.get(key, [])),
        )
        if state == "all" or (state == "unconfirmed" and not g["confirmed"]) or (
            state == "needs_input" and g["disposition"] in (None, "needs_input")
        ):
            out.append(g)
    return out


async def confirm_groups(db: AsyncSession, context: UserContext, report: Report, entries: list[ConfirmItem]) -> list[dict]:
    _require_editable(report)
    items = {i.key: i for i in (await db.execute(select(Item).where(Item.is_active.is_(True)))).scalars()}
    pairs = await _report_lines(db, report.id)
    sample: dict[str, tuple[Line, Site]] = {}
    for line, site in pairs:
        sample.setdefault(line.group_key, (line, site))
    now = datetime.now(timezone.utc)
    for entry in entries:
        if entry.group_key not in sample:
            raise NotFoundError("Group not found in this report")
        line, site = sample[entry.group_key]
        if entry.item_key:
            item = items.get(entry.item_key)
            if item is None or item.is_rollup:
                raise BadRequestError(f"Unknown or non-assignable item: {entry.item_key}")
            disposition, item_id, reason = Disposition.COUNTED, item.id, None
        elif entry.exclude_reason:
            disposition, item_id, reason = Disposition.EXCLUDED, None, entry.exclude_reason
        elif entry.disposition:
            disposition, item_id, reason = Disposition(entry.disposition), None, None
        else:
            raise BadRequestError("Give item_key, exclude_reason or disposition")
        role = Role(entry.role)
        cls = (await db.execute(select(Classification).where(
            Classification.report_id == report.id, Classification.group_key == entry.group_key))).scalar_one_or_none()
        if cls is None:
            cls = Classification(report_id=report.id, group_key=entry.group_key)
            db.add(cls)
        decision_id = None
        if entry.remember_scope == "global":
            decision = (await db.execute(select(Decision).where(Decision.key_hash == entry.group_key))).scalar_one_or_none()
            if decision is None:
                decision = Decision(
                    key_hash=entry.group_key, description_norm=line.description_norm, unit_norm=line.unit_norm,
                    site_kind=site.kind, disposition=disposition, source=DecisionSource.HUMAN,
                )
                db.add(decision)
            decision.disposition, decision.item_id, decision.role, decision.exclude_reason = disposition, item_id, role, reason
            decision.revoked_at = decision.revoked_by = None
            decision.created_by = decision.created_by or context.id
            decision.confirmed_by, decision.confirmed_at, decision.source_report_id = context.id, now, report.id
            decision.catalog_version = await bump_catalog_version(db)
            await memory.ensure_embedding(decision)
            await db.flush()
            decision_id = decision.id
        cls.disposition, cls.item_id, cls.role, cls.exclude_reason = disposition, item_id, role, reason
        cls.source, cls.confirmed, cls.confidence, cls.reason = ClassificationSource.HUMAN, True, None, None
        cls.decision_id, cls.decided_by, cls.decided_at = decision_id, context.id, now
    await db.flush()
    return await recompute_and_save(db, report)


# ---- reading results ---------------------------------------------------------------------------------------------

def _q(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:f}"


async def _names(db: AsyncSession) -> tuple[dict, dict, dict]:
    items = {i.id: i for i in (await db.execute(select(Item))).scalars()}
    sites = {s.id: s for s in (await db.execute(select(Site))).scalars()}
    companies = {c.id: c for c in (await db.execute(select(Company))).scalars()}
    return items, sites, companies


async def line_rows(db: AsyncSession, report: Report, *, site_id=None, item_key=None, effect=None, basis: str | None = None, limit=200, offset=0) -> list[dict]:
    items, sites, companies = await _names(db)
    query = (
        select(Line, LineResult, ReportFile).join(LineResult, LineResult.line_id == Line.id)
        .join(ReportFile, ReportFile.id == Line.report_file_id).where(ReportFile.report_id == report.id)
        .order_by(ReportFile.created_at, Line.sheet_name, Line.row_no).limit(limit).offset(offset)
    )
    if basis:
        query = query.where(Line.basis == basis)
    if site_id:
        query = query.where(Line.site_id == site_id)
    if effect:
        query = query.where(LineResult.effect == Effect(effect))
    if item_key:
        ids = [i.id for i in items.values() if i.key == item_key]
        query = query.where(LineResult.item_id.in_(ids))
    out = []
    for line, res, rfile in (await db.execute(query)).all():
        out.append({
            "line_id": line.id, "document_id": rfile.document_id, "filename": rfile.filename, "sheet": line.sheet_name,
            "row_no": line.row_no, "site_id": line.site_id, "site": sites[line.site_id].name,
            "company": companies[sites[line.site_id].company_id].name, "description": line.description_raw,
            "basis": line.basis, "unit": line.unit_raw, "unit_norm": line.unit_norm, "quantity": _q(line.quantity), "effect": res.effect.value,
            "item_key": items[res.item_id].key if res.item_id in items else None, "output_qty": _q(res.output_qty),
            "output_unit": res.output_unit, "note": res.note, "unconfirmed": res.unconfirmed, "flags": line.flags,
        })
    return out


async def get_results(db: AsyncSession, report: Report, group_by: str, include: set[str], basis: str = "actual") -> dict:
    items, sites, companies = await _names(db)
    rows = (await db.execute(select(Result).where(Result.report_id == report.id, Result.scope == ResultScope(group_by), Result.basis == basis))).scalars()
    result_rows = sorted(
        (
            {"scope": r.scope.value, "company_id": r.company_id, "company": companies[r.company_id].name if r.company_id else None,
             "site_id": r.site_id, "site": sites[r.site_id].name if r.site_id else None, "item_key": items[r.item_id].key,
             "item": items[r.item_id].title_fa, "decimals": items[r.item_id].decimals, "sort": items[r.item_id].sort_order,
             "qty": _q(r.qty), "unit": r.unit, "n_lines": r.n_lines, "has_unconfirmed": r.has_unconfirmed}
            for r in rows
        ),
        key=lambda r: (r["company"] or "", r["site"] or "", r["sort"]),
    )
    body: dict = {"report_id": report.id, "status": report.status.value, "group_by": group_by, "basis": basis, "rows": result_rows}
    if "other" in include:
        body["other"] = [r for r in await line_rows(db, report, effect="unmatched", basis=basis, limit=1000)] + \
                        [r for r in await line_rows(db, report, effect="site_kind_mismatch", basis=basis, limit=1000)] + \
                        [r for r in await line_rows(db, report, effect="needs_input", basis=basis, limit=1000)] + \
                        [r for r in await line_rows(db, report, effect="excluded", basis=basis, limit=1000)]  # nothing is hidden: legacy "removed" rows are "other"
    if "problems" in include:
        body["problems"] = [r for r in await line_rows(db, report, effect="unit_mismatch", basis=basis, limit=1000)] + \
                           [r for r in await line_rows(db, report, effect="no_conversion", basis=basis, limit=1000)]
    if "nonphysical" in include:
        body["nonphysical"] = await line_rows(db, report, effect="nonphysical", basis=basis, limit=1000)
    return body


def _achievement(planned: Decimal | None, actual: Decimal | None) -> str | None:
    if planned is None or actual is None or planned == 0:
        return None
    return f"{(actual / planned * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP):f}"


async def _previous_report(db: AsyncSession, report: Report) -> Report | None:
    """The report whose forecast covers this report's period: same project, latest period that ends before this one
    starts, that actually carries a forecast (planned results). Drafts that never ran are skipped."""
    candidates = (await db.execute(
        select(Report).where(Report.project_id == report.project_id, Report.id != report.id, Report.period_end < report.period_start,
                             Report.status.notin_((ReportStatus.DRAFT, ReportStatus.FAILED)))
        .order_by(Report.period_end.desc(), Report.version.desc())
    )).scalars().all()
    for cand in candidates:
        if await db.scalar(select(func.count()).select_from(Result).where(Result.report_id == cand.id, Result.basis == "planned")):
            return cand
    return None


async def plan_vs_actual(db: AsyncSession, report: Report, group_by: str) -> dict:
    """Forecast made in the previous report for this period vs this report's actuals, per item (and site/company).
    `next_plan` is this report's own forecast for the period after it."""
    previous = await _previous_report(db, report)
    actual = await get_results(db, report, group_by, set(), "actual")
    own_plan = await get_results(db, report, group_by, set(), "planned")
    monthly_files = (await db.execute(
        select(ReportFile, Company.name).join(Company, Company.id == ReportFile.company_id)
        .where(ReportFile.report_id == report.id, ReportFile.kind == "monthly_plan").order_by(ReportFile.created_at)
    )).all()
    plan_files = [{"filename": f.filename, "company": company_name, **info} for f, company_name in monthly_files if (info := plan_info(report, f))]
    body: dict = {"report_id": report.id, "group_by": group_by, "previous_report": None, "rows": [], "next_plan": own_plan["rows"], "plan_files": plan_files,
                  "plan_basis": "next"}
    if await _has_this_period_plan(db, report):
        # the plan beside the actuals IS this period's forecast (uploaded in this report): compare them directly, there is no "next" plan
        body.update(plan_basis="this", next_plan=[])
        previous, prev_plan = None, own_plan
    elif previous is None:
        return body
    else:
        prev_plan = await get_results(db, report=previous, group_by=group_by, include=set(), basis="planned")
    cell = lambda r: (r["company_id"], r["site_id"], r["item_key"])  # noqa: E731
    planned_by, actual_by = {cell(r): r for r in prev_plan["rows"]}, {cell(r): r for r in actual["rows"]}
    rows = []
    for key in sorted(set(planned_by) | set(actual_by), key=lambda k: ((planned_by.get(k) or actual_by[k])["company"] or "", (planned_by.get(k) or actual_by[k])["site"] or "", (planned_by.get(k) or actual_by[k])["sort"])):
        p, a = planned_by.get(key), actual_by.get(key)
        base = p or a
        pq, aq = (Decimal(p["qty"]) if p else None), (Decimal(a["qty"]) if a else None)
        rows.append({
            "company": base["company"], "site": base["site"], "item_key": base["item_key"], "item": base["item"], "unit": base["unit"],
            "decimals": base["decimals"], "planned": p["qty"] if p else None, "actual": a["qty"] if a else None,
            "variance": _q((aq or Decimal(0)) - (pq or Decimal(0))), "achievement_pct": _achievement(pq, aq),
        })
    if previous is not None:
        body["previous_report"] = {"id": previous.id, "title": previous.title, "period_label": previous.period_label,
                                   "period_start": previous.period_start, "period_end": previous.period_end,
                                   "adjacent": (report.period_start - previous.period_end).days <= 1}
    body["rows"] = rows
    return body


async def get_previous_actuals(db: AsyncSession, report: Report, group_by: str = "holding") -> dict:
    """Actual results of the closest preceding report in the same project for comparison."""
    candidates = (await db.execute(
        select(Report).where(
            Report.project_id == report.project_id,
            Report.id != report.id,
            Report.period_start < report.period_start,
            Report.status.notin_((ReportStatus.DRAFT, ReportStatus.FAILED, ReportStatus.PROCESSING)),
        )
        .order_by(Report.period_start.desc(), Report.version.desc())
    )).scalars().all()

    for cand in candidates:
        has_results = await db.scalar(
            select(func.count()).select_from(Result).where(
                Result.report_id == cand.id,
                Result.scope == ResultScope(group_by),
                Result.basis == "actual",
            )
        )
        if has_results:
            results = await get_results(db, report=cand, group_by=group_by, include=set(), basis="actual")
            return {
                "report_id": report.id,
                "previous_report": {
                    "id": cand.id,
                    "title": cand.title,
                    "period_label": cand.period_label,
                    "period_start": cand.period_start,
                    "period_end": cand.period_end,
                },
                "rows": results["rows"],
            }

    return {
        "report_id": report.id,
        "previous_report": None,
        "rows": [],
    }


async def _has_this_period_plan(db: AsyncSession, report: Report) -> bool:
    """True when a forecast file of this report is the forecast of the report's own period (see `forecast_scope`)."""
    files = {f.id: f for f in (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id, ReportFile.kind == "period"))).scalars()}
    if not files:
        return False
    bases = {}
    for fid, basis in (await db.execute(select(Line.report_file_id, Line.basis).where(Line.report_file_id.in_(list(files))).distinct())).all():
        bases.setdefault(fid, set()).add(basis)
    return any("planned" in b and is_this_period_forecast(report, files[fid], "actual" in b) for fid, b in bases.items())


# ---- EVM (PV / EV / AC / CPI / SPI) ----------------------------------------------------------------------------

_EVM_SUMS = ("contract_amount", "bcws", "pv", "ev", "ev_net", "ac")


def _evm_row_read(r: EvmRow) -> dict:
    return {"project": r.project_name, "contract_amount": _opt(r.contract_amount), "bcws": _opt(r.bcws), "pv": _opt(r.pv), "ev": _opt(r.ev),
            "ev_net": _opt(r.ev_net), "ac": _opt(r.ac), "cpi": _opt(r.cpi, "0.01"), "spi": _opt(r.spi, "0.01")}


def _opt(value: Decimal | None, step: str = "0.01") -> str | None:
    return None if value is None else f"{value.quantize(Decimal(step)):f}"


def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return (numerator / denominator).quantize(Decimal("0.01"))


def _evm_total(rows: list[Any]) -> dict:
    """Sum of the projects; CPI/SPI are ratios of sums (ev / AC, EV / PV) over the projects that carry both operands,
    so a project with no cost or no programme yet does not drag the ratio."""
    total: dict = {}
    for field in _EVM_SUMS:
        values = [getattr(r, field) for r in rows if getattr(r, field) is not None]
        total[field] = _opt(sum(values, Decimal(0))) if values else None
    cost = [r for r in rows if r.ev_net is not None and r.ac is not None and r.ac > 0]
    plan = [r for r in rows if r.ev is not None and r.pv is not None and r.pv > 0]
    total["cpi"] = _opt(sum(r.ev_net for r in cost) / sum(r.ac for r in cost)) if cost else None
    total["spi"] = _opt(sum(r.ev for r in plan) / sum(r.pv for r in plan)) if plan else None
    total["projects"] = len(rows)
    return total


def _sum_all(values: list[Decimal | None]) -> str | None:
    """A sum is only honest when every sheet printed the figure; otherwise NULL (the UI then skips the step)."""
    return _opt(sum(values, Decimal(0))) if values and all(v is not None for v in values) else None


def _income_read(rows: list[IncomeTotal]) -> dict | None:
    """Company-level sum of the income sheets' totals blocks (the chain statement -> coefficients -> adjustment -> total income)."""
    if not rows:
        return None
    known = [r.cumulative for r in rows if r.cumulative is not None]
    return {
        "sheets": len(rows), "statement_base": _sum_all([r.statement_base for r in rows]), "statement_coef": _sum_all([r.statement_coef for r in rows]),
        "adjustment": _sum_all([r.adjustment for r in rows]), "income_total": _sum_all([r.income_total for r in rows]),
        "cumulative": _opt(sum(known, Decimal(0))) if known else None,
    }


_PV_SOURCE_LABELS = {"manual": "ورود دستی", "file": "فایل گزارش", "forecast_file": "پیش‌بینیِ همین دوره (EV پیش‌بینی)", "previous_report": "پیش‌بینیِ گزارش قبلی (EV پیش‌بینی)",
                     "forecast_income": "پیش‌بینیِ همین دوره (جمع کل درآمد)", "previous_income": "پیش‌بینیِ گزارش قبلی (جمع کل درآمد)",
                     "monthly_pv": "برنامه‌ی PV ماهانه"}
_SPI_EXTREME = Decimal(3)  # an SPI above this is almost always a placeholder PV, not a project three times ahead of its programme


def _name_tokens(name: str | None) -> set[str]:
    return {w for w in normalize_text(name or "").split() if len(w) > 1 and w not in {"پروژه", "عملیات", "اجرایی"}}


def _match_project(name: str | None, candidates: list[str | None]) -> tuple[int, str] | None:
    """Index of the candidate that is the same project: identical normalized name, else a unique best word overlap >= 0.7."""
    key = normalize_text(name or "")
    if not key:
        return None
    for index, candidate in enumerate(candidates):
        if normalize_text(candidate or "") == key:
            return index, "exact"
    tokens = _name_tokens(name)
    scored = sorted(((len(tokens & _name_tokens(c)) / len(tokens | _name_tokens(c)), i) for i, c in enumerate(candidates) if tokens and _name_tokens(c)), reverse=True)
    if scored and scored[0][0] >= 0.7 and (len(scored) == 1 or scored[1][0] < scored[0][0]):
        return scored[0][1], "fuzzy"
    return None


async def _adjacent_previous_planned_rows(db: AsyncSession, report: Report) -> list[tuple[Any, uuid.UUID]]:
    """Forecast EVM rows (with the company id) of the report that ends right before this one: its next-period forecast is this period's."""
    candidates = (await db.execute(
        select(Report).where(Report.project_id == report.project_id, Report.id != report.id, Report.period_end < report.period_start,
                             Report.status.notin_((ReportStatus.DRAFT, ReportStatus.FAILED)))
        .order_by(Report.period_end.desc(), Report.version.desc())
    )).scalars().all()
    for cand in candidates:
        if (report.period_start - cand.period_end).days > 1:
            break  # not adjacent: its forecast is for another week
        rows = (await db.execute(
            select(EvmRow, ReportFile.company_id).join(ReportFile, ReportFile.id == EvmRow.report_file_id)
            .where(ReportFile.report_id == cand.id, EvmRow.basis == "planned", EvmRow.is_total.is_(False))
        )).all()
        if rows:
            return [(r, cid) for r, cid in rows if r.period_start is None or (r.period_start, r.period_end) == (report.period_start, report.period_end)]
    return []


async def _adjacent_previous_forecast_income(db: AsyncSession, report: Report) -> list[tuple[Any, uuid.UUID, uuid.UUID | None]]:
    """(income totals, company id, site id) of the forecast pages of the report that ends right before this one. Its forecast is for
    this period unless it says otherwise; used when the forecast has no EVM page (the totals block "جمع کل درآمد" is its EV)."""
    candidates = (await db.execute(
        select(Report).where(Report.project_id == report.project_id, Report.id != report.id, Report.period_end < report.period_start,
                             Report.status.notin_((ReportStatus.DRAFT, ReportStatus.FAILED)))
        .order_by(Report.period_end.desc(), Report.version.desc())
    )).scalars().all()
    for cand in candidates:
        if (report.period_start - cand.period_end).days > 1:
            break
        files = {f.id: f for f in (await db.execute(select(ReportFile).where(ReportFile.report_id == cand.id, ReportFile.kind == "period"))).scalars()}
        if not files:
            continue
        totals = (await db.execute(select(IncomeTotal).where(IncomeTotal.report_file_id.in_(list(files)), IncomeTotal.basis == "planned"))).scalars().all()
        if not totals:
            continue
        actual_ids = set((await db.execute(select(IncomeTotal.report_file_id).where(IncomeTotal.report_file_id.in_(list(files)), IncomeTotal.basis == "actual"))).scalars())
        sites = await _sheet_sites(db, list(files))
        out = []
        for t in totals:
            f = files[t.report_file_id]
            if forecast_scope(cand, f, f.id in actual_ids)["scope"] == "next" and t.income_total is not None:  # relative to ITS report: it is for the period after
                out.append((t, f.company_id, sites.get((f.id, t.sheet_name))))
        return out
    return []


async def _sheet_sites(db: AsyncSession, file_ids: list[uuid.UUID]) -> dict[tuple[uuid.UUID, str], uuid.UUID]:
    """(file, sheet) -> the site its lines belong to: what ties an income sheet's totals to a project without trusting its name."""
    rows = (await db.execute(select(Line.report_file_id, Line.sheet_name, Line.site_id).where(Line.report_file_id.in_(file_ids)).distinct())).all()
    return {(fid, sheet): site for fid, sheet, site in rows}


async def store_evm_extraction(db: AsyncSession, report: Report, rfile: ReportFile, extraction) -> None:
    """Stores the EVM rows, income totals and PV-plan rows an extraction found in one file (the run and the EVM re-read share it)."""
    from app.features.volume_report import activity

    span = resolve_period(extraction.title_period, report.period_end) if getattr(extraction, "title_period", None) is not None else None
    rfile.title_period_start, rfile.title_period_end = span if span else (None, None)
    if extraction.pv_plan is not None:
        for pv_row in extraction.pv_plan.rows:
            db.add(PvPlanRow(report_file_id=rfile.id, row_no=pv_row.row_no, project_name=pv_row.project_name, pv_month=pv_row.pv_month))
        await activity.log_activity(db, report.id, "parse", f"فایل «{rfile.filename}»: برنامه‌ی PV ماهانه‌ی {len(extraction.pv_plan.rows)} پروژه خوانده شد",
                                    kind="success", commit=False)
    for evm in extraction.evm_sheets:
        period = resolve_period(evm.period, report.period_end) if evm.period is not None else None
        for row in evm.rows:
            db.add(EvmRow(
                report_file_id=rfile.id, sheet_name=evm.sheet_name, row_no=row.row_no, basis=evm.basis, project_name=row.project_name,
                is_total=row.is_total, contract_amount=row.contract_amount, bcws=row.bcws, pv=row.pv, ev=row.ev, ev_net=row.ev_net,
                ac=row.ac, cpi=row.cpi, spi=row.spi, period_start=period[0] if period else None, period_end=period[1] if period else None,
            ))
    for sheet_name, basis, totals in extraction.income_totals:
        db.add(IncomeTotal(report_file_id=rfile.id, sheet_name=sheet_name, basis=basis, statement_base=totals.statement_base,
                           statement_coef=totals.statement_coef, adjustment=totals.adjustment, income_total=totals.income_total,
                           cumulative=totals.cumulative))
    if extraction.evm_sheets:
        n = sum(len(e.rows) for e in extraction.evm_sheets)
        await activity.log_activity(db, report.id, "parse", f"فایل «{rfile.filename}»: {n} ردیف EVM (PV/EV/AC/CPI/SPI) خوانده شد", kind="success", commit=False)


async def reparse_evm(db: AsyncSession, report: Report) -> dict:
    """Reads the EVM rows, income totals and PV plan of every file again, without a new run: the lines, the review and the PV the
    user typed are untouched. Typed PVs are matched by project name, so they survive as long as the name is read the same."""
    from app.features.volume_report.extraction.normalize import Lexicon
    from app.features.volume_report.extraction.runner import extract_file

    _require_editable(report)
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id).order_by(ReportFile.created_at))).scalars().all()
    fresh: list[tuple[ReportFile, Any]] = []
    for rfile in files:
        document = await db.get(Document, rfile.document_id) if rfile.document_id else None
        if document is None or document.project_id != report.project_id:
            raise BadRequestError(f"The source document of «{rfile.filename}» is no longer available")
        try:
            extraction = await asyncio.to_thread(
                extract_file, resolve_document_path(document), Lexicon([]), None, None, rfile.kind == "monthly_plan" or rfile.forecast_for != "auto", rfile.kind == "monthly_pv", True, file_name=rfile.filename)
        except Exception as exc:  # noqa: BLE001 - a file that cannot be read must not wipe the rows we already have
            raise BadRequestError(f"«{rfile.filename}» could not be read: {getattr(exc, 'detail', None) or exc}") from exc
        fresh.append((rfile, extraction))
    ids = [f.id for f in files]
    if ids:
        await db.execute(delete(EvmRow).where(EvmRow.report_file_id.in_(ids)))
        await db.execute(delete(IncomeTotal).where(IncomeTotal.report_file_id.in_(ids)))
        await db.execute(delete(PvPlanRow).where(PvPlanRow.report_file_id.in_(ids)))
    for rfile, extraction in fresh:
        await store_evm_extraction(db, report, rfile, extraction)
    await db.commit()
    return await get_evm(db, report)


async def get_evm(db: AsyncSession, report: Report) -> dict:
    """The period's EVM per company: projects, company total, holding total. Everything but PV comes from the project's own
    report file. PV (and so SPI = EV / PV) comes from, in this order: the EV of the project's forecast for this very period
    (a forecast file of this report whose title names this period, else the previous report's forecast), the monthly PV plan
    (its share by days), else what the file itself prints. No forecast EVM is reported: forecasts only supply PV."""
    rows = (await db.execute(
        select(EvmRow, ReportFile, Company.name)
        .join(ReportFile, ReportFile.id == EvmRow.report_file_id).join(Company, Company.id == ReportFile.company_id)
        .where(ReportFile.report_id == report.id).order_by(Company.name, ReportFile.created_at, EvmRow.sheet_name, EvmRow.row_no)
    )).all()
    income_rows = (await db.execute(
        select(IncomeTotal, ReportFile).join(ReportFile, ReportFile.id == IncomeTotal.report_file_id).where(ReportFile.report_id == report.id, IncomeTotal.basis == "actual")
    )).all()
    pv_rows = (await db.execute(
        select(PvPlanRow, ReportFile).join(ReportFile, ReportFile.id == PvPlanRow.report_file_id).where(ReportFile.report_id == report.id)
        .order_by(ReportFile.created_at, PvPlanRow.row_no)
    )).all()
    override_rows = (await db.execute(select(PvOverride).where(PvOverride.report_id == report.id))).scalars().all()
    excluded_rows = (await db.execute(
        select(EvmExclusion, Company.name).join(Company, Company.id == EvmExclusion.company_id).where(EvmExclusion.report_id == report.id)
        .order_by(Company.name, EvmExclusion.project_name)
    )).all()
    excluded = {(e.company_id, e.project_key) for e, _ in excluded_rows}
    all_income = (await db.execute(
        select(IncomeTotal, ReportFile).join(ReportFile, ReportFile.id == IncomeTotal.report_file_id).where(ReportFile.report_id == report.id)
    )).all()
    sheet_site = await _sheet_sites(db, list({f.id for _, f, _ in rows} | {f.id for _, f in all_income})) if (rows or all_income) else {}
    overrides = {(o.company_id, o.project_key): o.pv for o in override_rows}
    overrides_named = {(o.company_id, o.project_key): (o.project_name, o.pv) for o in override_rows}
    manual_mode = report.pv_mode == "manual"
    period = (report.period_start, report.period_end)
    actual_files = {f.id for r, f, _ in rows if r.basis == "actual"} | {f.id for t, f in all_income if t.basis == "actual"}
    scope_of = {f.id: forecast_scope(report, f, f.id in actual_files) for _, f, _ in rows} | {f.id: forecast_scope(report, f, f.id in actual_files) for _, f in all_income}

    def forecast_row_is_for_this_period(r: EvmRow, f: ReportFile) -> bool:
        """A forecast row is the PV of this period when the file is (the user's choice, else the title/file name); a row that names its
        own period is judged by that period unless the user decided."""
        if f.kind != "period":
            return False
        if f.forecast_for != "auto":
            return f.forecast_for == "this_period"
        if r.period_start is not None:
            return (r.period_start, r.period_end) == period
        return scope_of[f.id]["scope"] == "this"

    same_period_forecast = [(r, f.company_id) for r, f, _ in rows if r.basis == "planned" and not r.is_total and forecast_row_is_for_this_period(r, f)]
    previous_forecast = await _adjacent_previous_planned_rows(db, report)
    # Forecast pages with no EVM page ("جمع کل درآمد" of the project's forecast income sheet = its EV), summed per (company, site)
    forecast_income: dict[tuple[uuid.UUID, uuid.UUID], Decimal] = {}
    for t, f in all_income:
        site_id = sheet_site.get((f.id, t.sheet_name))
        if t.basis == "planned" and t.income_total is not None and f.kind == "period" and scope_of[f.id]["scope"] == "this" and site_id is not None:
            forecast_income[(f.company_id, site_id)] = forecast_income.get((f.company_id, site_id), Decimal(0)) + t.income_total
    previous_income: dict[tuple[uuid.UUID, uuid.UUID], Decimal] = {}
    for t, company_id, site_id in await _adjacent_previous_forecast_income(db, report):
        if site_id is not None:
            previous_income[(company_id, site_id)] = previous_income.get((company_id, site_id), Decimal(0)) + t.income_total

    def site_of(row: EvmRow, f: ReportFile) -> uuid.UUID | None:
        """The site whose income sheet totals to this row's EV, so the project is tied to its forecast by value, not by a name the two
        files may spell differently. EV is that sheet's "جمع کل درآمد" exactly in most templates; in some it leaves a small part out (a
        deduction): then the nearest sheet within 12% is taken when it is clearly nearer than any other (not one that another row of
        the file matches exactly)."""
        if row.ev is None or row.ev <= 0:
            return None
        sheets = [t for t, f2 in all_income if f2.id == f.id and t.basis == "actual" and t.income_total is not None]
        tolerance = max(Decimal(2), abs(row.ev) / 100000)
        exact = [t for t in sheets if abs(t.income_total - row.ev) <= tolerance]
        if len(exact) == 1:
            return sheet_site.get((f.id, exact[0].sheet_name))
        if exact:
            return None
        taken = {t.sheet_name for r2, f2, _ in rows if f2.id == f.id and r2.basis == "actual" and r2.ev for t in sheets if abs(t.income_total - r2.ev) <= max(Decimal(2), abs(r2.ev) / 100000)}
        near = sorted((abs(t.income_total - row.ev) / row.ev, t) for t in sheets if t.sheet_name not in taken)
        near = [(err, t) for err, t in near if err <= Decimal("0.12")]
        if len(near) == 1 or (len(near) > 1 and near[0][0] * 3 < near[1][0]):
            return sheet_site.get((f.id, near[0][1].sheet_name))
        return None

    def pv_for(row: EvmRow, f: ReportFile) -> tuple[Decimal | None, str, str | None, str | None]:
        """(pv, source, match kind, note)"""
        company_id = f.company_id
        for source, candidates in (("forecast_file", same_period_forecast), ("previous_report", previous_forecast)):
            mine = [(r, c) for r, c in candidates if c == company_id and r.ev is not None]
            hit = _match_project(row.project_name, [r.project_name for r, _ in mine])
            if hit:
                return mine[hit[0]][0].ev, source, hit[1], None
        site_id = site_of(row, f)
        if site_id is not None:
            for source, amounts in (("forecast_income", forecast_income), ("previous_income", previous_income)):
                if amounts.get((company_id, site_id)):
                    return amounts[(company_id, site_id)], source, "value", None
        monthly = [(r, f) for r, f in pv_rows if plan_factor(report, f) > 0]
        hit = _match_project(row.project_name, [r.project_name for r, _ in monthly])
        if hit:
            plan_row, plan_file = monthly[hit[0]]
            info = plan_info(report, plan_file)
            return plan_row.pv_month * plan_factor(report, plan_file), "monthly_pv", hit[1], f"{info['overlap_days']}/{info['plan_days']}" if info else None
        return row.pv, "file", None, None

    companies: dict[uuid.UUID, dict] = {}
    overridden: set[uuid.UUID] = set()
    # One project can appear in several files of a company (a shared EVM sheet lists the sibling projects too): keep the row that
    # carries the most figures, so its cost is not counted twice.
    best: dict[tuple[uuid.UUID, str], EvmRow] = {}
    for row, f, _ in rows:
        if row.basis == "actual" and not row.is_total and row.project_name and (f.company_id, normalize_text(row.project_name)) not in excluded:
            key = (f.company_id, normalize_text(row.project_name))
            figures = lambda r: sum(v is not None for v in (r.pv, r.ev, r.ev_net, r.ac))  # noqa: E731
            if key not in best or figures(row) > figures(best[key]):
                best[key] = row
    for row, f, company_name in rows:
        if row.basis != "actual":
            continue
        if not row.is_total and row.project_name and (f.company_id, normalize_text(row.project_name)) in excluded:
            continue  # removed from this report by the user
        if not row.is_total and row.project_name and best[(f.company_id, normalize_text(row.project_name))] is not row:
            continue
        company = companies.setdefault(f.company_id, {"company_id": f.company_id, "company": company_name, "projects": [], "_rows": [], "_reported": []})
        if row.is_total:
            company["_reported"].append(row)
            continue
        auto_pv, auto_source, auto_match, auto_note = pv_for(row, f)
        manual = overrides.get((f.company_id, normalize_text(row.project_name or "")))
        # manual mode: a typed value wins for its project; every other project keeps the automatic PV (forecast, plan, else the file's own)
        pv, source, match, note = (manual, "manual", None, None) if manual_mode and manual is not None else (auto_pv, auto_source, auto_match, auto_note)
        item = SimpleNamespace(**{c.name: getattr(row, c.name) for c in row.__table__.columns})
        if source != "file":
            overridden.add(f.company_id)
            item.pv = pv
            item.spi = _ratio(item.ev, pv)
        notes = []
        if source == "file":
            notes.append("pv_from_file" if item.pv is not None else "pv_missing")
        if item.spi is not None and item.spi > _SPI_EXTREME:
            notes.append("spi_extreme")
        company["projects"].append({**_evm_row_read(item), "filename": f.filename, "notes": notes,
                                    "pv_source": source, "pv_source_label": _PV_SOURCE_LABELS[source],
                                    "pv_match": match, "pv_share": note,
                                    "pv_auto": _opt(auto_pv) if auto_source != "file" else None, "pv_manual": _opt(manual)})
        company["_rows"].append(item)
    out = []
    for company in companies.values():
        project_rows, reported = company.pop("_rows"), company.pop("_reported")
        company["total"] = _evm_total(project_rows)
        company["income"] = _income_read([r for r, f in income_rows if f.company_id == company["company_id"]])
        # the file's own "جمع" row carries the file's own PV / SPI: it is only shown while those are still the ones in use
        company["reported_total"] = ({**_evm_total(reported), **_evm_row_read(reported[0])}
                                     if len(reported) == 1 and company["company_id"] not in overridden else None)
        out.append(company)
    all_rows = [SimpleNamespace(**{k: p[k] and Decimal(p[k]) for k in ("pv", "ev", "ev_net", "ac", "contract_amount", "bcws")}) for c in out for p in c["projects"]]
    known = {(c["company_id"], normalize_text(p["project"] or "")) for c in out for p in c["projects"]}
    unmatched = [{"company_id": cid, "project": o_name, "pv": _opt(pv)} for (cid, key), (o_name, pv) in overrides_named.items() if (cid, key) not in known]
    return {"report_id": report.id, "pv_mode": report.pv_mode, "pv_manual_unmatched": unmatched,
            "excluded": [{"company_id": e.company_id, "company": company_name, "project": e.project_name} for e, company_name in excluded_rows],
            "actual": {"companies": out, "holding": _evm_total(all_rows) if all_rows else None}}


async def set_pv(db: AsyncSession, report: Report, payload) -> dict:
    """Choose where PV comes from (auto | manual) and store the PV typed per project (rial; a missing value is deleted)."""
    _require_editable(report)
    known = {(c.id) for c in (await db.execute(select(Company))).scalars()}
    await db.execute(delete(PvOverride).where(PvOverride.report_id == report.id))
    for entry in payload.values:
        if entry.pv is None:
            continue
        if entry.company_id not in known:
            raise NotFoundError("Company not found")
        key = normalize_text(entry.project)
        if not key:
            raise BadRequestError("Project name is empty")
        db.add(PvOverride(report_id=report.id, company_id=entry.company_id, project_key=key, project_name=entry.project.strip(), pv=entry.pv))
    report.pv_mode = payload.mode
    await db.commit()
    return await get_evm(db, report)


async def set_evm_exclusions(db: AsyncSession, report: Report, payload) -> dict:
    """Replaces the list of projects removed from this report's EVM. Nothing is deleted from the files or the stored rows: a removed
    project can be put back, and it stays removed through a new run (it is matched by its normalized name)."""
    _require_editable(report)
    known = {c.id for c in (await db.execute(select(Company))).scalars()}
    await db.execute(delete(EvmExclusion).where(EvmExclusion.report_id == report.id))
    seen: set[tuple[uuid.UUID, str]] = set()
    for entry in payload.excluded:
        if entry.company_id not in known:
            raise NotFoundError("Company not found")
        key = normalize_text(entry.project)
        if not key:
            raise BadRequestError("Project name is empty")
        if (entry.company_id, key) in seen:
            continue
        seen.add((entry.company_id, key))
        db.add(EvmExclusion(report_id=report.id, company_id=entry.company_id, project_key=key, project_name=entry.project.strip()))
    await db.commit()
    return await get_evm(db, report)


async def report_detail(db: AsyncSession, report: Report) -> dict:
    causes = await gate_causes(db, report) if report.status != ReportStatus.PUBLISHED else []
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id).order_by(ReportFile.created_at))).scalars().all()
    return {
        "id": report.id, "project_id": report.project_id, "title": report.title, "period_type": report.period_type.value,
        "period_start": report.period_start, "period_end": report.period_end, "period_label": report.period_label,
        "status": report.status.value, "progress": report.progress, "version": report.version,
        "narratives": report.narratives or {},
        "supersedes_id": report.supersedes_id, "published_at": report.published_at, "error_message": report.error_message,
        "files": [{"id": f.id, "document_id": f.document_id, "filename": f.filename, "company_id": f.company_id,
                   "status": f.status.value, "error_message": f.error_message, "kind": f.kind, "plan_start": f.plan_start,
                   "plan_end": f.plan_end,
                   "plan_month": jalali.to_jalali(f.plan_start)[1] if f.kind in ("monthly_plan", "monthly_pv") and f.plan_start else None} for f in files],
        "issues": causes,
    }


def _span(period: tuple[date, date] | None) -> dict | None:
    return None if period is None else {"start": period[0], "end": period[1]}


async def sources(db: AsyncSession, report: Report) -> list[dict]:
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars().all()
    ids = [f.id for f in files]
    evm: dict[tuple, int] = {}
    for fid, basis, is_total, n in (await db.execute(
        select(EvmRow.report_file_id, EvmRow.basis, EvmRow.is_total, func.count()).where(EvmRow.report_file_id.in_(ids)).group_by(EvmRow.report_file_id, EvmRow.basis, EvmRow.is_total)
    )).all():
        evm[(fid, basis, is_total)] = n
    totals: dict[tuple, int] = {}
    for fid, basis, n in (await db.execute(
        select(IncomeTotal.report_file_id, IncomeTotal.basis, func.count()).where(IncomeTotal.report_file_id.in_(ids)).group_by(IncomeTotal.report_file_id, IncomeTotal.basis)
    )).all():
        totals[(fid, basis)] = n
    pv_counts = {fid: n for fid, n in (await db.execute(
        select(PvPlanRow.report_file_id, func.count()).where(PvPlanRow.report_file_id.in_(ids)).group_by(PvPlanRow.report_file_id)
    )).all()}
    forecast_periods = {fid: (a, b) for fid, a, b in (await db.execute(
        select(EvmRow.report_file_id, func.min(EvmRow.period_start), func.min(EvmRow.period_end))
        .where(EvmRow.report_file_id.in_(ids), EvmRow.basis == "planned").group_by(EvmRow.report_file_id)
    )).all()}
    out = []
    for f in files:
        # Projects, not pages: a project's table (and its totals block) may run over several pages with the same site name.
        income = {b: len({e.get("site_name") or e.get("sheet") for e in f.sheet_log
                          if e.get("used") and e.get("kind") in ("income", "planned") and (e.get("basis") or "actual") == b}) for b in ("actual", "planned")}
        reads = {
            "income": income,
            "income_totals": {b: totals.get((f.id, b), 0) for b in ("actual", "planned")},
            "evm": {b: {"projects": evm.get((f.id, b, False), 0), "has_total": bool(evm.get((f.id, b, True)))} for b in ("actual", "planned")},
            "pv_plan": pv_counts.get(f.id, 0),
            # the period a forecast EVM sheet names, and whether it is this report's own period (then its EV is the PV)
            "forecast_period": ({"start": forecast_periods[f.id][0], "end": forecast_periods[f.id][1],
                                 "is_this_period": (forecast_periods[f.id][0], forecast_periods[f.id][1]) == (report.period_start, report.period_end)}
                                if forecast_periods.get(f.id) and forecast_periods[f.id][0] else None),
        }
        has_planned = bool(evm.get((f.id, "planned", False)) or totals.get((f.id, "planned")) or income["planned"])
        has_actual = bool(evm.get((f.id, "actual", False)) or totals.get((f.id, "actual")) or income["actual"])
        forecast = None
        if f.kind == "period" and has_planned:
            forecast = forecast_scope(report, f, has_actual)
            forecast = {**forecast, "title_period": _span(forecast["title_period"]), "filename_period": _span(forecast["filename_period"])}
        out.append({"id": f.id, "filename": f.filename, "status": f.status.value, "error_message": f.error_message,
                    "suggested_company": f.suggested_company, "sheet_log": f.sheet_log, "warnings": f.warnings, "reads": reads,
                    "kind": f.kind, "forecast_for": f.forecast_for, "forecast": forecast, "plan": plan_info(report, f)})
    return out


async def export_rows(db: AsyncSession, report: Report) -> tuple[list[list], list[list]]:
    data = await get_results(db, report, "site", {"other", "problems"})
    rows = [[r["company"], r["site"], r["item"], float(r["qty"]), r["unit"], r["n_lines"], "بله" if r["has_unconfirmed"] else ""] for r in data["rows"]]
    extra = [[l["effect"], l["company"], l["site"], l["description"], l["unit"], float(l["quantity"]), l["filename"], l["sheet"], l["row_no"]]
             for l in data["other"] + data["problems"]]
    return rows, extra


# ---- publish / reopen --------------------------------------------------------------------------------------------

async def publish(db: AsyncSession, context: UserContext, report: Report) -> Report:
    await db.refresh(report, with_for_update=True)  # two simultaneous publishes: the second sees `published` and stops
    if report.status == ReportStatus.PUBLISHED:
        raise ConflictError("The report is already published")
    if report.status not in (ReportStatus.READY, ReportStatus.NEEDS_REVIEW, ReportStatus.AWAITING_USER):
        raise ConflictError("Run the report before publishing")
    if not await db.scalar(select(func.count()).select_from(ReportFile).where(ReportFile.report_id == report.id)):
        raise ConflictError("Select at least one file before publishing")
    causes = await recompute(db, report)
    if causes and settings.vr_publish_gate == "strict":
        await db.commit()
        raise ConflictError("Publish blocked: " + json.dumps(causes))
    results = await get_results(db, report, "site", {"other", "problems", "nonphysical"})
    company = await get_results(db, report, "company", set())
    holding = await get_results(db, report, "holding", set())
    planned = {g: (await get_results(db, report, g, set(), "planned"))["rows"] for g in ("site", "company", "holding")}
    classes = await list_groups(db, report, "all")
    items = (await db.execute(select(Item).order_by(Item.sort_order))).scalars().all()
    files = await sources(db, report)
    payload = json.loads(json.dumps({
        "report": {"id": report.id, "title": report.title, "period_type": report.period_type.value,
                   "period_label": report.period_label, "period_start": report.period_start, "period_end": report.period_end,
                   "version": report.version, "project_id": report.project_id},
        "results": {"site": results["rows"], "company": company["rows"], "holding": holding["rows"]},
        "planned_results": planned,
        "evm": await get_evm(db, report),
        "other": results["other"], "problems": results["problems"], "nonphysical": results["nonphysical"],
        "classifications": classes, "warnings": {"gate": causes, "files": [{"filename": f["filename"], "warnings": f["warnings"]} for f in files]},
        "catalog": [{"key": i.key, "title_fa": i.title_fa, "output_unit": i.output_unit, "decimals": i.decimals} for i in items],
    }, default=str))
    catalog_version = await current_catalog_version(db)
    catalog_hash = hashlib.sha256(json.dumps(payload["catalog"], sort_keys=True).encode()).hexdigest()
    db.add(Snapshot(report_id=report.id, payload=payload, catalog_version=catalog_version, catalog_hash=catalog_hash, created_by=context.id))
    report.status = ReportStatus.PUBLISHED
    report.published_at, report.published_by = datetime.now(timezone.utc), context.id
    await db.commit()
    await db.refresh(report)
    return report


async def reopen(db: AsyncSession, context: UserContext, report: Report) -> Report:
    await db.refresh(report, with_for_update=True)
    if report.status != ReportStatus.PUBLISHED:
        raise ConflictError("Only a published report can be reopened")
    newer = await db.scalar(select(func.count()).select_from(Report).where(Report.supersedes_id == report.id))
    if newer:
        raise ConflictError("This report was already reopened")
    fresh = Report(
        project_id=report.project_id, title=report.title, period_type=report.period_type, period_start=report.period_start,
        period_end=report.period_end, period_label=report.period_label, version=report.version + 1,
        supersedes_id=report.id, created_by=context.id, progress={}, pv_mode=report.pv_mode,
    )
    db.add(fresh)
    await db.flush()
    for o in (await db.execute(select(PvOverride).where(PvOverride.report_id == report.id))).scalars():
        db.add(PvOverride(report_id=fresh.id, company_id=o.company_id, project_key=o.project_key, project_name=o.project_name, pv=o.pv))
    for e in (await db.execute(select(EvmExclusion).where(EvmExclusion.report_id == report.id))).scalars():
        db.add(EvmExclusion(report_id=fresh.id, company_id=e.company_id, project_key=e.project_key, project_name=e.project_name))
    for f in (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars():
        db.add(ReportFile(report_id=fresh.id, document_id=f.document_id, filename=f.filename, content_hash=f.content_hash, company_id=f.company_id,
                          kind=f.kind, forecast_for=f.forecast_for, plan_start=f.plan_start, plan_end=f.plan_end))
    # Human decisions carry over so the new draft starts where the old one ended.
    for c in (await db.execute(select(Classification).where(Classification.report_id == report.id, Classification.source == ClassificationSource.HUMAN))).scalars():
        db.add(Classification(
            report_id=fresh.id, group_key=c.group_key, disposition=c.disposition, item_id=c.item_id, role=c.role,
            exclude_reason=c.exclude_reason, source=c.source, confirmed=True, decided_by=c.decided_by, decided_at=c.decided_at,
        ))
    await db.commit()
    await db.refresh(fresh)
    return fresh


async def latest_snapshot_payload(db: AsyncSession, report: Report) -> dict:
    snap = (await db.execute(select(Snapshot).where(Snapshot.report_id == report.id))).scalar_one_or_none()
    if snap is None:
        raise NotFoundError("No snapshot")
    return snap.payload


# ---- settings: catalog & lexicon --------------------------------------------------------------------------------

def _item_read(i: Item) -> dict:
    return {"id": i.id, "key": i.key, "title_fa": i.title_fa, "description_fa": i.description_fa, "dimension": i.dimension.value,
            "output_unit": i.output_unit, "decimals": i.decimals, "sort_order": i.sort_order, "is_rollup": i.is_rollup,
            "rollup_of": i.rollup_of, "mining_only": i.mining_only, "is_active": i.is_active}


async def _validate_item(db: AsyncSession, payload, existing_key: str | None) -> None:
    from app.features.volume_report.extraction.units import UNIT_DIMENSIONS

    if UNIT_DIMENSIONS.get(payload.output_unit) != payload.dimension:
        raise BadRequestError(f"output_unit '{payload.output_unit}' does not match dimension '{payload.dimension}'")
    if payload.is_rollup:
        if not payload.rollup_of:
            raise BadRequestError("A rollup needs rollup_of")
        keys = set((await db.execute(select(Item.key).where(Item.is_active.is_(True)))).scalars())
        missing = [k for k in payload.rollup_of if k not in keys or k == payload.key]
        if missing:
            raise BadRequestError(f"Unknown rollup members: {missing}")
    elif payload.rollup_of:
        raise BadRequestError("rollup_of is only for rollup items")


async def list_items(db: AsyncSession) -> list[dict]:
    await ensure_seeded(db)
    return [_item_read(i) for i in (await db.execute(select(Item).order_by(Item.sort_order))).scalars()]


async def upsert_item(db: AsyncSession, payload, key_in_path: str | None = None) -> dict:
    """Create (key_in_path None) or update an item. Deactivating keeps old data; memory pointing at it stops auto-applying."""
    await ensure_seeded(db)
    item = (await db.execute(select(Item).where(Item.key == (key_in_path or payload.key)))).scalar_one_or_none()
    if key_in_path is None and item is not None:
        raise ConflictError("An item with this key already exists")
    if key_in_path is not None and item is None:
        raise NotFoundError("Item not found")
    if key_in_path is not None and payload.key != key_in_path:
        raise BadRequestError("The key of an item cannot be changed")
    await _validate_item(db, payload, key_in_path)
    if item is None:
        item = Item(key=payload.key, dimension=Dimension(payload.dimension))
        db.add(item)
    item.title_fa, item.description_fa, item.dimension = payload.title_fa, payload.description_fa, Dimension(payload.dimension)
    item.output_unit, item.decimals, item.sort_order = payload.output_unit, payload.decimals, payload.sort_order
    item.is_rollup, item.rollup_of, item.mining_only, item.is_active = payload.is_rollup, payload.rollup_of, payload.mining_only, payload.is_active
    await bump_catalog_version(db)
    await db.commit()
    await db.refresh(item)
    return _item_read(item)


def _lexicon_read(e: LexiconEntry) -> dict:
    return {"id": e.id, "token": e.token, "kind": e.kind.value, "phrases": e.phrases, "is_active": e.is_active}


async def list_lexicon(db: AsyncSession) -> list[dict]:
    await ensure_seeded(db)
    return [_lexicon_read(e) for e in (await db.execute(select(LexiconEntry).order_by(LexiconEntry.token))).scalars()]


async def upsert_lexicon(db: AsyncSession, payload, token_in_path: str | None = None) -> dict:
    await ensure_seeded(db)
    entry = (await db.execute(select(LexiconEntry).where(LexiconEntry.token == (token_in_path or payload.token)))).scalar_one_or_none()
    if token_in_path is None and entry is not None:
        raise ConflictError("This token already exists")
    if token_in_path is not None and entry is None:
        raise NotFoundError("Token not found")
    if token_in_path is not None and payload.token != token_in_path:
        raise BadRequestError("The token cannot be renamed")
    if entry is None:
        entry = LexiconEntry(token=payload.token)
        db.add(entry)
    entry.kind, entry.phrases, entry.is_active = LexiconKind(payload.kind), payload.phrases, payload.is_active
    await bump_catalog_version(db)
    await db.commit()
    await db.refresh(entry)
    return _lexicon_read(entry)


async def get_narratives(db: AsyncSession, report: Report) -> dict:
    return report.narratives or {}


async def update_narratives(db: AsyncSession, report: Report, narratives_data: dict) -> dict:
    cleaned: dict[str, dict] = {}
    for key, val in narratives_data.items():
        if isinstance(val, dict):
            cleaned[key] = val
        elif hasattr(val, "model_dump"):
            cleaned[key] = val.model_dump()
        else:
            cleaned[key] = dict(val)
    report.narratives = cleaned
    await db.commit()
    await db.refresh(report)
    return report.narratives


async def generate_company_narrative(
    company_name: str,
    raw_text: str,
) -> dict:
    from app.providers.llm_provider import get_vr_llm_provider
    provider = get_vr_llm_provider()

    system_prompt = (
        "شما یک دستیار هوشمند سازمانی برای تدوین «گزارش عملکرد پروژه‌های عمرانی» هلدینگ جهاد نصر کرمان هستید.\n"
        "وظیفه شما این است که یادداشت‌های خام دریافتی از مدیران پروژه را تمیز، ویرایش و ساختاردهی کنید تا دقیقاً با سبک، لحن و قالب گزارش‌های مدیریتی هلدینگ همخوان باشد.\n\n"
        "قواعد ساختاری و نگارشی:\n"
        "۱. خروجی باید فهرستی از بندهای مهم عملکرد (Bullet points) باشد. هر بند باید یک اقدام، رویداد یا پیشرفت کلیدی را بیان کند.\n"
        "۲. موضوعات مهم شامل موارد زیر است:\n"
        "   - پروژه‌های اجرایی و پیشرفت احجام و لایه‌ها (مثلاً: اتمام لایه اساس، عملیات خاکریزی/خاکبرداری، لوله‌گذاری، پیشرفت فیزیکی).\n"
        "   - مناقصات و مزایدات (اخذ اسناد مناقصه، شرکت در مناقصه، ارسال اسناد ارزیابی کیفی، تکمیل پیشنهاد قیمت).\n"
        "   - تحویل‌ها و قراردادها (تحویل موقت یا قطعی، ابلاغ ماده ۴۸، آزادسازی ضمانت‌نامه‌ها، تنظیم یا ابلاغ قراردادهای جدید).\n"
        "۳. اگر یک بند دارای چند زیرمجموعه (مثلاً چند فقره مناقصه یا قرارداد) است، از عنوان کلی به همراه شماره‌گذاری ۱، ۲، ۳ در خطوط بعد استفاده کنید. مثال:\n"
        "اخذ اسناد چهار فقره مناقصه:\n"
        "۱- گردنه خرمافروشان\n"
        "۲- نیوجرسی محور زرند بافق\n"
        "۳- نیوجرسی محور راهور دیهوک\n"
        "۴- تامین نیوجرسی در ۴ قطعه ۵ کیلومتری در محور زاهدان خاش\n"
        "۴. لحن باید کاملاً رسمی، مدیریتی، فاقد حواشی، کوتاه، گویا و دقیق باشد.\n"
        "۵. هیچ توضیح اضافه، مقدمه یا موخره‌ای ننویسید. فقط بندهای متن را بنویسید (بین هر بند اصلی یک خط خالی بگذارید)."
    )

    user_prompt = f"نام شرکت: {company_name}\n\nیادداشت‌های خام:\n{raw_text}"

    res = await provider.complete([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])

    content = (res.get("content") or "").strip()
    raw_blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
    items: list[str] = []
    for block in raw_blocks:
        lines = block.splitlines()
        first_line = lines[0].lstrip("-•* ").strip()
        cleaned_block = "\n".join([first_line, *lines[1:]]).strip()
        if cleaned_block:
            items.append(cleaned_block)

    if not items and content:
        items = [content]

    return {
        "company_name": company_name,
        "raw_text": raw_text,
        "cleaned_text": content,
        "items": items,
    }
