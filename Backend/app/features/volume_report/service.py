"""Reports, files, classification review, results, publish. Services commit themselves (project convention)."""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.features.documents.models import Document, DocumentStatus
from app.features.projects.models import Project
from app.features.volume_report import compute, memory
from app.features.volume_report.extraction.normalize import Lexicon, LexiconEntry as LexEntry, normalize_text
from app.features.volume_report.models import (
    Classification, ClassificationSource, Company, Conversion, Decision, ItemRule, DecisionSource, Disposition, Effect,
    Dimension, ExcludeReason, Item, Line, LexiconKind, LineResult, Question, QuestionStatus, Report, ReportFile, ReportStatus, Result,
    ResultScope, Role, Site, SiteKind, Snapshot, LexiconEntry,
)
from app.features.volume_report.schemas import ConfirmItem, FileSelection, ReportCreate
from app.features.volume_report.seed import bump_catalog_version, current_catalog_version, ensure_seeded

logger = logging.getLogger(__name__)
settings = get_settings()

EXCEL_SUFFIXES = {".xls", ".xlsx", ".xlsm", ".pdf"}
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


async def set_files(db: AsyncSession, report: Report, selections: list[FileSelection]) -> list[dict]:
    from app.features.volume_report.extraction.runner import suggest_company_for_file

    _require_editable(report)
    wanted: dict[uuid.UUID, ReportFile] = {}
    suggestions: dict[uuid.UUID, str | None] = {}
    for sel in selections:
        document = await db.get(Document, sel.document_id)
        if document is None or document.project_id != report.project_id:
            raise NotFoundError("Document not found")
        if document.status != DocumentStatus.READY:
            raise BadRequestError("Document is not ready")
        if Path(document.filename).suffix.lower() not in EXCEL_SUFFIXES:
            raise BadRequestError("Only .xls, .xlsx, .xlsm and .pdf files are supported")
        company = await db.get(Company, sel.company_id)
        if company is None or not company.is_active:
            raise NotFoundError("Company not found")
        if sel.document_id in wanted:
            raise BadRequestError("Duplicate document in the selection")
        wanted[sel.document_id] = ReportFile(
            report_id=report.id, document_id=document.id, filename=document.filename,
            content_hash=document.content_hash, company_id=company.id,
        )
        try:
            suggestions[document.id] = await asyncio.to_thread(suggest_company_for_file, resolve_document_path(document))
        except Exception:  # a suggestion is optional; the run reports real read errors
            suggestions[document.id] = None

    existing = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars().all()
    keep = {f.document_id: f for f in existing if f.document_id in wanted}
    for f in existing:
        if f.document_id not in wanted:
            await db.delete(f)
    for doc_id, new in wanted.items():
        if doc_id in keep:
            keep[doc_id].company_id = new.company_id
        else:
            db.add(new)
    await db.commit()
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars().all()
    return [
        {"id": f.id, "document_id": f.document_id, "filename": f.filename, "company_id": f.company_id,
         "status": f.status.value, "suggested_company": suggestions.get(f.document_id) or f.suggested_company}
        for f in files
    ]


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


# ---- resolve / convert / aggregate -------------------------------------------------------------------------------

async def recompute(db: AsyncSession, report: Report) -> list[dict]:
    """Rebuilds `vr_line_results` and `vr_results` from lines + classifications. Returns the gate causes."""
    items = {i.id: i for i in (await db.execute(select(Item))).scalars()}
    item_in = {i.key: compute.ItemIn(i.key, i.output_unit, i.mining_only, i.is_rollup, list(i.rollup_of)) for i in items.values()}
    pairs = await _report_lines(db, report.id)
    lines_in = [
        compute.LineIn(str(l.id), str(s.id), s.kind.value, l.group_key, l.unit_norm, l.quantity, bool(l.flags.get("negative_qty")), l.description_norm)
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
    pairs = await _report_lines(db, report.id)
    classes = {c.group_key: c for c in (await db.execute(select(Classification).where(Classification.report_id == report.id))).scalars()}
    item_keys = {i.id: i.key for i in (await db.execute(select(Item))).scalars()}
    groups: dict[str, dict] = {}
    for line, site in pairs:
        g = groups.setdefault(line.group_key, {
            "group_key": line.group_key, "description": line.description_raw, "unit": line.unit_norm,
            "site_kind": site.kind.value, "n_lines": 0, "section_headings": [], "tokens": line.tokens,
            "total_quantity": Decimal(0), "planned_quantity": Decimal(0),
        })
        g["n_lines"] += 1
        g["planned_quantity" if line.basis == "planned" else "total_quantity"] += line.quantity
        if line.section_heading and line.section_heading not in g["section_headings"] and len(g["section_headings"]) < 3:
            g["section_headings"].append(line.section_heading)
    out = []
    for key, g in groups.items():
        c = classes.get(key)
        g.update(
            disposition=c.disposition.value if c else None, item_key=item_keys.get(c.item_id) if c else None,
            role=c.role.value if c else None, exclude_reason=c.exclude_reason.value if c and c.exclude_reason else None,
            source=c.source.value if c else None, confirmed=c.confirmed if c else False, reason=c.reason if c else None,
            confidence=c.confidence if c else None,
            total_quantity=f"{g['total_quantity']:f}", planned_quantity=f"{g['planned_quantity']:f}",
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
    body: dict = {"report_id": report.id, "group_by": group_by, "previous_report": None, "rows": [], "next_plan": own_plan["rows"]}
    if previous is None:
        return body
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
    body["previous_report"] = {"id": previous.id, "title": previous.title, "period_label": previous.period_label,
                               "period_start": previous.period_start, "period_end": previous.period_end,
                               "adjacent": (report.period_start - previous.period_end).days <= 1}
    body["rows"] = rows
    return body


async def report_detail(db: AsyncSession, report: Report) -> dict:
    causes = await gate_causes(db, report) if report.status != ReportStatus.PUBLISHED else []
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars().all()
    return {
        "id": report.id, "project_id": report.project_id, "title": report.title, "period_type": report.period_type.value,
        "period_start": report.period_start, "period_end": report.period_end, "period_label": report.period_label,
        "status": report.status.value, "progress": report.progress, "version": report.version,
        "narratives": report.narratives or {},
        "supersedes_id": report.supersedes_id, "published_at": report.published_at, "error_message": report.error_message,
        "files": [{"id": f.id, "document_id": f.document_id, "filename": f.filename, "company_id": f.company_id,
                   "status": f.status.value, "error_message": f.error_message} for f in files],
        "issues": causes,
    }


async def sources(db: AsyncSession, report: Report) -> list[dict]:
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars().all()
    return [{"id": f.id, "filename": f.filename, "status": f.status.value, "error_message": f.error_message,
             "suggested_company": f.suggested_company, "sheet_log": f.sheet_log, "warnings": f.warnings} for f in files]


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
        supersedes_id=report.id, created_by=context.id, progress={},
    )
    db.add(fresh)
    await db.flush()
    for f in (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars():
        db.add(ReportFile(report_id=fresh.id, document_id=f.document_id, filename=f.filename, content_hash=f.content_hash, company_id=f.company_id))
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
