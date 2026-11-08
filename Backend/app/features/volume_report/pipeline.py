"""The report job: Probe -> Parse -> Annotate -> Hard rules -> Memory -> Resolve/Convert/Aggregate -> status.
Runs in the volume-report RQ worker (never in an API handler); file parsing happens in a thread."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory, engine
from app.features.documents.models import Document
from app.features.volume_report import activity, questions, service
from app.features.volume_report.agent import runner as agent_runner
from app.features.volume_report.extraction.normalize import group_key
from app.features.volume_report.extraction.runner import extract_file
from app.features.volume_report.models import (
    Classification, ClassificationSource, Company, Decision, Dimension, Disposition, ExcludeReason, FileStatus, Item, Line,
    Question, QuestionStatus, Report, ReportFile, ReportStatus, Role, Site, SiteKind,
)
from app.features.volume_report.seed import ensure_seeded
from app.features.usage.service import usage_scope
from app.providers.llm_provider import get_vr_llm_provider

logger = logging.getLogger(__name__)

STEPS = ["parse", "classify", "compute"]

_CLASSIFY_LABELS = [
    ("memory_exact", "با حافظه‌ی تصمیم‌ها تعیین شد"), ("hard_exclusion", "با قاعده‌ی قطعی حذف شد"), ("nonphysical_unit", "غیرفیزیکی (واحد مقطوع/ساعت)"),
    ("awaiting_classification", "در انتظار بررسی هوشمند"), ("memory_item_inactive", "با آیتم غیرفعال در حافظه"),
]


async def _progress(db: AsyncSession, report: Report, step: str, done: int, total: int, message: str = "") -> None:
    report.progress = {"step": step, "done": done, "total": total, "message": message}
    await db.commit()


async def _site_for(db: AsyncSession, company_id: uuid.UUID, name: str, name_norm: str, kind_guess: str) -> Site:
    site = (await db.execute(select(Site).where(Site.company_id == company_id, Site.name_norm == name_norm))).scalar_one_or_none()
    if site is None:
        site = Site(company_id=company_id, name=name, name_norm=name_norm, kind=SiteKind(kind_guess), kind_confirmed=False)
        db.add(site)
        await db.flush()
    return site


async def _parse_files(db: AsyncSession, report: Report, lexicon, overrides: dict[uuid.UUID, dict[str, dict]]) -> int:
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id).order_by(ReportFile.created_at))).scalars().all()
    parsed_ok = 0
    for index, rfile in enumerate(files, start=1):
        await _progress(db, report, "parse", index - 1, len(files), rfile.filename)
        await activity.log_activity(db, report.id, "parse", f"در حال خواندن فایل «{rfile.filename}» ({index} از {len(files)})", kind="step")
        rfile.sheet_log, rfile.warnings, rfile.error_message = [], [], None
        try:
            document = await db.get(Document, rfile.document_id) if rfile.document_id else None
            if document is None or document.project_id != report.project_id:
                raise ValueError("Source document is no longer available")
            path = service.resolve_document_path(document)
            extraction = await asyncio.to_thread(extract_file, path, lexicon, report.period_label, overrides.get(rfile.id))
        except Exception as exc:
            logger.warning("Volume report %s: file %s failed: %s", report.id, rfile.filename, exc)
            rfile.status = FileStatus.FAILED
            rfile.error_message = (getattr(exc, "detail", None) or str(exc))[:500]
            await activity.log_activity(db, report.id, "parse", f"فایل «{rfile.filename}» خوانده نشد: {rfile.error_message}", kind="error", commit=False)
            continue
        rfile.sheet_log, rfile.warnings, rfile.suggested_company = extraction.sheet_log, extraction.warnings, extraction.suggested_company
        ok_sheets = [sh for sh in extraction.sheets if sh.status == "ok"]
        skipped = [e["sheet"] for e in extraction.sheet_log if not e.get("used")]
        await activity.log_activity(
            db, report.id, "parse",
            f"فایل «{rfile.filename}»: {len(ok_sheets)} شیت درآمد خوانده شد"
            + (f" ({sum(1 for sh in ok_sheets if sh.basis == 'planned')} شیت برنامه/پیش‌بینی)" if any(sh.basis == "planned" for sh in ok_sheets) else "")
            + f"، {len(skipped)} شیت نادیده گرفته شد",
            kind="success" if ok_sheets else "warn", detail={"skipped_sheets": skipped[:30], "warnings": len(extraction.warnings)}, commit=False)
        for sheet in extraction.sheets:
            if sheet.status != "ok":
                continue
            site = await _site_for(db, rfile.company_id, sheet.site_name, sheet.site_name_norm, sheet.site_kind_guess)
            await activity.log_activity(db, report.id, "parse", f"کارگاه «{sheet.site_name}»: {len(sheet.lines)} ردیف خوانده شد", kind="info",
                                        detail={"sheet": sheet.sheet_name, "kind_guess": sheet.site_kind_guess}, commit=False)
            for line in sheet.lines:
                db.add(Line(
                    report_file_id=rfile.id, site_id=site.id, sheet_name=line.sheet_name, row_no=line.row_no,
                    section_heading=line.section_heading, description_raw=line.description_raw,
                    description_norm=line.description_norm, tokens=line.tokens, unit_raw=line.unit_raw,
                    unit_norm=line.unit_norm, unit_dim=Dimension(line.unit_dim), quantity=line.quantity,
                    flags={**line.flags, "role_hint": line.role_hint},
                    group_key=group_key(line.description_norm, line.unit_norm, site.kind.value), basis=sheet.basis,
                ))
        rfile.status = FileStatus.PARSED
        parsed_ok += 1
        await db.flush()
    return parsed_ok


async def _classify(db: AsyncSession, report: Report, lexicon, preserved: dict[str, Classification]) -> None:
    pairs = await service._report_lines(db, report.id)
    first: dict[str, Line] = {}
    for line, _ in pairs:
        first.setdefault(line.group_key, line)
    decisions = {d.key_hash: d for d in (await db.execute(select(Decision).where(Decision.revoked_at.is_(None)))).scalars()}
    items = {i.id: i for i in (await db.execute(select(Item))).scalars()}
    tally: dict[str, int] = {}
    for key, line in first.items():
        values: dict
        if key in preserved:
            old = preserved[key]
            values = dict(disposition=old.disposition, item_id=old.item_id, role=old.role, exclude_reason=old.exclude_reason,
                          source=old.source, confirmed=old.confirmed, decision_id=old.decision_id,
                          decided_by=old.decided_by, decided_at=old.decided_at, reason=old.reason)
        elif (reason := lexicon.hard_exclusion_reason(line.tokens)) is not None:
            values = dict(disposition=Disposition.EXCLUDED, exclude_reason=ExcludeReason(reason), source=ClassificationSource.SYSTEM,
                          confirmed=True, reason="hard_exclusion")
        elif line.unit_dim in (Dimension.NONPHYSICAL, Dimension.TIME):
            values = dict(disposition=Disposition.NONPHYSICAL, source=ClassificationSource.SYSTEM, confirmed=True, reason="nonphysical_unit")
        elif (decision := decisions.get(key)) is not None and decision.item_id is not None and not (
            items.get(decision.item_id) and items[decision.item_id].is_active
        ):
            # The remembered item was deactivated/removed: not applied automatically, flagged for a fresh decision.
            values = dict(disposition=Disposition.NEEDS_INPUT, source=ClassificationSource.SYSTEM, confirmed=False, reason="memory_item_inactive")
        elif decision is not None:
            decision.hits += 1
            values = dict(disposition=decision.disposition, item_id=decision.item_id, role=decision.role, exclude_reason=decision.exclude_reason,
                          source=ClassificationSource.MEMORY, confirmed=True, decision_id=decision.id, reason="memory_exact")
        else:
            values = dict(disposition=Disposition.NEEDS_INPUT, source=ClassificationSource.SYSTEM, confirmed=False, reason="awaiting_classification")
        values.setdefault("role", Role.NA)
        tally[values.get("reason") or "other"] = tally.get(values.get("reason") or "other", 0) + 1
        db.add(Classification(report_id=report.id, group_key=key, **values))
    await db.flush()
    parts = [f"{tally[k]} {label}" for k, label in _CLASSIFY_LABELS if tally.get(k)]
    await activity.log_activity(db, report.id, "classify", f"{len(first)} گروه یکتا از ردیف‌ها ساخته شد" + (": " + "، ".join(parts) if parts else ""),
                                kind="success", detail={"groups": len(first), "by_reason": tally}, commit=False)


async def _execute(db: AsyncSession, report: Report) -> None:
    await ensure_seeded(db)
    lexicon = await service.load_lexicon(db)
    file_ids = select(ReportFile.id).where(ReportFile.report_id == report.id)
    # Human decisions survive a re-run (group keys are stable); everything derived is rebuilt.
    preserved = {
        c.group_key: c for c in (await db.execute(select(Classification).where(
            Classification.report_id == report.id, Classification.source == ClassificationSource.HUMAN))).scalars()
    }
    snapshot = {k: Classification(**{col.name: getattr(c, col.name) for col in Classification.__table__.columns if col.name != "id"}) for k, c in preserved.items()}
    await db.execute(delete(Line).where(Line.report_file_id.in_(file_ids)))  # cascades to line results
    await db.execute(delete(Classification).where(Classification.report_id == report.id))
    await db.flush()
    overrides = {
        f.id: {e["sheet"]: e["layout_override"] for e in f.sheet_log if e.get("layout_override")}
        for f in (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars()
    }
    if not await _parse_files(db, report, lexicon, overrides):
        report.status, report.error_message = ReportStatus.FAILED, "None of the files could be read"
        await activity.log_activity(db, report.id, "done", "هیچ‌کدام از فایل‌ها خوانده نشد", kind="error", commit=False)
        await db.commit()
        return
    await _progress(db, report, "classify", 0, 1)
    await _classify(db, report, lexicon, snapshot)
    await _agent_and_finish(db, report, lexicon)


async def _agent_and_finish(db: AsyncSession, report: Report, lexicon) -> None:
    """Agent pass for the groups nobody decided yet, then deterministic resolve and the status."""
    pending = await db.scalar(
        select(func.count()).select_from(Classification).where(
            Classification.report_id == report.id, Classification.disposition == Disposition.NEEDS_INPUT, Classification.reason == "awaiting_classification")
    )
    unknown_layouts = any(
        e.get("layout_unknown")
        for f in (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars()
        for e in f.sheet_log
    ) and not await db.scalar(select(func.count()).select_from(Question).where(Question.report_id == report.id, Question.status == QuestionStatus.OPEN))
    if pending or unknown_layouts:
        await _progress(db, report, "agent", 0, 1, f"{pending} groups")
        await activity.log_activity(db, report.id, "agent", f"شروع بررسی هوشمند: {pending} گروه نیازمند تصمیم" if pending else "شروع بررسی هوشمند چیدمان شیت‌ها",
                                    kind="step", detail={"pending": pending})
        provider = None
        try:
            provider = get_vr_llm_provider()
        except Exception:  # missing configuration: leave the groups for humans
            logger.warning("Volume report %s: no LLM provider available", report.id)
        if provider is not None:
            run = await agent_runner.run_pass(db, report, provider, lexicon, get_settings().llm_vr_model or get_settings().llm_model)
            await activity.log_activity(
                db, report.id, "agent", f"بررسی هوشمند تمام شد ({run.steps} گام)", kind="error" if run.status.value == "failed" else "success",
                detail={"steps": run.steps, "model": run.model, "prompt_tokens": run.prompt_tokens, "completion_tokens": run.completion_tokens})
        else:
            await activity.log_activity(db, report.id, "agent", "مدل زبانی تنظیم نشده است؛ گروه‌ها برای تصمیم شما می‌مانند", kind="warn", commit=False)
            await db.execute(update(Classification).where(Classification.report_id == report.id, Classification.reason == "awaiting_classification").values(reason="agent_failed"))
            await db.commit()
    await _progress(db, report, "compute", 0, 1)
    await activity.log_activity(db, report.id, "compute", "محاسبه‌ی نتایج (تبدیل واحد و جمع‌بندی)", kind="step")
    await service.recompute(db, report)
    await questions.refresh_system_questions(db, report)
    await questions.trim_open_questions(db, report)
    causes = await service.gate_causes(db, report)
    report.status = service.derive_status(causes)
    report.progress = {"step": "done", "done": 1, "total": 1, "message": ""}
    open_q = await db.scalar(select(func.count()).select_from(Question).where(Question.report_id == report.id, Question.status == QuestionStatus.OPEN))
    outcome = {ReportStatus.AWAITING_USER: "در انتظار پاسخ شما", ReportStatus.NEEDS_REVIEW: "آماده‌ی بازبینی", ReportStatus.READY: "آماده‌ی انتشار"}.get(report.status, report.status.value)
    await activity.log_activity(db, report.id, "done", f"پردازش پایان یافت: {outcome}" + (f" — {open_q} سؤال باز" if open_q else ""), kind="success",
                                detail={"status": report.status.value, "open_questions": open_q or 0}, commit=False)
    await db.commit()


async def _continue(db: AsyncSession, report: Report) -> None:
    """Next pass after answers: no re-parsing, groups the agent has not decided are retried."""
    await ensure_seeded(db)
    lexicon = await service.load_lexicon(db)
    await db.execute(update(Classification).where(
        Classification.report_id == report.id, Classification.disposition == Disposition.NEEDS_INPUT,
        Classification.reason.in_(["agent_failed", "agent_incomplete", "asked"]), Classification.source != ClassificationSource.HUMAN,
    ).values(reason="awaiting_classification"))
    await db.commit()
    await _agent_and_finish(db, report, lexicon)


def _lock_key(report_id: uuid.UUID) -> int:
    return int.from_bytes(report_id.bytes[:8], "big", signed=True)


async def run_report(report_id: uuid.UUID, mode: str = "full", user_id: uuid.UUID | None = None) -> None:
    """One job per report at a time: a session-level advisory lock on its own connection (a duplicate job is skipped).
    The agent's model calls are charged to `user_id` (whoever started the run), see features/usage."""
    with usage_scope(user_id, "vr_agent"):
        await _run_report_locked_by_advisory(report_id, mode)


async def _run_report_locked_by_advisory(report_id: uuid.UUID, mode: str) -> None:
    async with engine.connect() as lock_conn:
        if not await lock_conn.scalar(select(func.pg_try_advisory_lock(_lock_key(report_id)))):
            logger.info("Volume report %s skipped: another job holds the lock", report_id)
            return
        try:
            await _run_locked(report_id, mode)
        finally:
            await lock_conn.scalar(select(func.pg_advisory_unlock(_lock_key(report_id))))


async def _run_locked(report_id: uuid.UUID, mode: str) -> None:
    async with async_session_factory() as db:
        report = await db.get(Report, report_id)
        if report is None or report.status != ReportStatus.PROCESSING:
            logger.info("Volume report %s skipped: not in processing state", report_id)
            return
        try:
            await activity.log_activity(db, report_id, "start", "ادامه‌ی پردازش پس از پاسخ‌های شما" if mode == "continue" else "پردازش گزارش شروع شد",
                                        kind="info", detail={"mode": mode}, new_attempt=True)
            await (_continue(db, report) if mode == "continue" else _execute(db, report))
        except Exception as exc:
            logger.exception("Volume report %s failed", report_id)
            await db.rollback()
            await db.execute(update(Report).where(Report.id == report_id).values(
                status=ReportStatus.FAILED, error_message=f"Processing failed: {type(exc).__name__}"))
            await activity.log_activity(db, report_id, "done", "پردازش با خطا متوقف شد", kind="error", detail={"error": type(exc).__name__})


def run_report_sync(report_id: uuid.UUID, mode: str = "full", user_id: uuid.UUID | None = None) -> None:
    """RQ entry point."""
    asyncio.run(run_report(report_id, mode, user_id))
