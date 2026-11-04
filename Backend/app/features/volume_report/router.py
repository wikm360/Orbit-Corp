import asyncio
import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.features.usage.service import ensure_quota
from app.features.volume_report import activity, export, memory, questions, service
from app.features.volume_report.models import Company, Conversion, Item, Report, ReportStatus, Site
from app.features.volume_report.schemas import (
    CompanyWrite, ConfirmRequest, ConversionWrite, FilesUpdate, ItemWrite, LexiconWrite, ReportCreate, ReportRead, SiteUpdate,
)
from app.features.volume_report.seed import bump_catalog_version, ensure_seeded

router = APIRouter(prefix="/volume-reports", tags=["volume-reports"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def get_report_for_member(
    report_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
) -> Report:
    """404 when the report does not exist, 403 when the caller is not in its project."""
    return await service.get_report_for_member(db, context, report_id)


# ---- catalog & settings (static paths first, before /{report_id}) ----------------------------------------------

@router.get("/catalog")
async def catalog(context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    await ensure_seeded(db)
    rows = (await db.execute(select(Item).where(Item.is_active.is_(True)).order_by(Item.sort_order))).scalars()
    return [{"key": i.key, "title_fa": i.title_fa, "description_fa": i.description_fa, "dimension": i.dimension.value,
             "output_unit": i.output_unit, "decimals": i.decimals, "is_rollup": i.is_rollup, "rollup_of": i.rollup_of,
             "mining_only": i.mining_only} for i in rows]


@router.get("/settings/items")
async def settings_items(context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await service.list_items(db)


@router.post("/settings/items", status_code=201)
async def create_item(payload: ItemWrite, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    return await service.upsert_item(db, payload)


@router.put("/settings/items/{key}")
async def update_item(key: str, payload: ItemWrite, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    return await service.upsert_item(db, payload, key)


@router.get("/settings/lexicon")
async def settings_lexicon(context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await service.list_lexicon(db)


@router.post("/settings/lexicon", status_code=201)
async def create_lexicon(payload: LexiconWrite, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    return await service.upsert_lexicon(db, payload)


@router.put("/settings/lexicon/{token}")
async def update_lexicon(token: str, payload: LexiconWrite, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    return await service.upsert_lexicon(db, payload, token)


@router.get("/settings/companies")
async def list_companies(context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Company).order_by(Company.name))).scalars()
    return [{"id": c.id, "name": c.name, "aliases": c.aliases, "is_active": c.is_active} for c in rows]


@router.post("/settings/companies", status_code=201)
async def create_company(payload: CompanyWrite, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    if await db.scalar(select(Company.id).where(Company.name == payload.name)):
        raise ConflictError("A company with this name already exists")
    company = Company(**payload.model_dump())
    db.add(company)
    await db.commit()
    return {"id": company.id, "name": company.name, "aliases": company.aliases, "is_active": company.is_active}


@router.put("/settings/companies/{company_id}")
async def update_company(company_id: uuid.UUID, payload: CompanyWrite, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    company = await db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found")
    company.name, company.aliases, company.is_active = payload.name, payload.aliases, payload.is_active
    await db.commit()
    return {"id": company.id, "name": company.name, "aliases": company.aliases, "is_active": company.is_active}


def _site_read(s: Site) -> dict:
    return {"id": s.id, "company_id": s.company_id, "name": s.name, "kind": s.kind.value, "kind_confirmed": s.kind_confirmed,
            "aliases": s.aliases, "is_active": s.is_active}


@router.get("/settings/sites")
async def list_sites(company_id: uuid.UUID | None = None, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    query = select(Site).order_by(Site.name)
    if company_id:
        query = query.where(Site.company_id == company_id)
    return [_site_read(s) for s in (await db.execute(query)).scalars()]


@router.put("/settings/sites/{site_id}")
async def update_site(site_id: uuid.UUID, payload: SiteUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    site = await db.get(Site, site_id)
    if site is None:
        raise NotFoundError("Site not found")
    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "aliases", "is_active"):
        if data.get(field) is not None:
            setattr(site, field, data[field])
    if payload.kind is not None:
        site.kind = payload.kind
        site.kind_confirmed = True  # choosing a kind is the confirmation; re-run reports for new group keys
    if payload.kind_confirmed is not None:
        site.kind_confirmed = payload.kind_confirmed
    if site.kind_confirmed:
        await questions.supersede_site_questions(db, site.id)
    await bump_catalog_version(db)
    await db.commit()
    return _site_read(site)


def _conversion_read(c: Conversion, item_keys: dict) -> dict:
    return {"id": c.id, "key": c.key, "item_key": item_keys.get(c.item_id), "site_id": c.site_id, "value": f"{c.value:f}", "unit": c.unit, "note": c.note}


@router.get("/settings/conversions")
async def list_conversions(context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    await ensure_seeded(db)
    item_keys = {i.id: i.key for i in (await db.execute(select(Item))).scalars()}
    return [_conversion_read(c, item_keys) for c in (await db.execute(select(Conversion).order_by(Conversion.key))).scalars()]


@router.put("/settings/conversions")
async def upsert_conversion(payload: ConversionWrite, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    items = {i.key: i for i in (await db.execute(select(Item))).scalars()}
    item = items.get(payload.item_key) if payload.item_key else None
    if payload.item_key and item is None:
        raise NotFoundError("Item not found")
    if payload.site_id and await db.get(Site, payload.site_id) is None:
        raise NotFoundError("Site not found")
    existing = (await db.execute(select(Conversion).where(
        Conversion.key == payload.key,
        Conversion.item_id.is_(None) if item is None else Conversion.item_id == item.id,
        Conversion.site_id.is_(None) if payload.site_id is None else Conversion.site_id == payload.site_id,
    ))).scalar_one_or_none()
    if existing is None:
        existing = Conversion(key=payload.key, item_id=item.id if item else None, site_id=payload.site_id, value=payload.value, unit=payload.unit)
        db.add(existing)
    existing.value, existing.unit, existing.note, existing.updated_by = payload.value, payload.unit, payload.note, context.id
    await bump_catalog_version(db)
    await db.commit()
    await db.refresh(existing)
    return _conversion_read(existing, {i.id: i.key for i in items.values()})


@router.delete("/settings/conversions/{conversion_id}", status_code=204)
async def delete_conversion(
    conversion_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    service.require_settings_editor(context)
    c = await db.get(Conversion, conversion_id)
    if c is None:
        raise NotFoundError("Conversion not found")
    await db.delete(c)
    await bump_catalog_version(db)
    await db.commit()


@router.get("/settings/decisions")
async def list_decisions(q: str | None = None, include_revoked: bool = False, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                         context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    return await memory.list_decisions(db, q, include_revoked, limit, offset)


@router.get("/settings/decisions/similar")
async def similar_decisions(text: str = Query(..., min_length=1, max_length=500), unit: str | None = None, site_kind: str | None = None,
                            context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    return await memory.search_similar(db, text, unit, site_kind)


@router.post("/settings/decisions/{decision_id}/revoke")
async def revoke_decision(decision_id: uuid.UUID, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    service.require_settings_editor(context)
    decision = await memory.revoke_decision(db, decision_id, context.id)
    return {"id": decision.id, "revoked_at": decision.revoked_at}


# ---- reports -----------------------------------------------------------------------------------------------------

@router.post("", response_model=ReportRead, status_code=201)
async def create(payload: ReportCreate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await service.create_report(db, context, payload)


@router.get("", response_model=list[ReportRead])
async def list_(project_id: uuid.UUID, status: ReportStatus | None = None, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await service.list_reports(db, context, project_id, status)


@router.get("/{report_id}")
async def detail(report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    return await service.report_detail(db, report)


@router.delete("/{report_id}", status_code=204)
async def remove(report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    await service.delete_report(db, report)


@router.put("/{report_id}/files")
async def put_files(payload: FilesUpdate, report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    return await service.set_files(db, report, payload.files)


@router.post("/{report_id}/run", response_model=ReportRead, status_code=202)
async def run(report: Report = Depends(get_report_for_member), context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    ensure_quota(context.user)
    return await service.request_run(db, report, user_id=context.id)


@router.post("/{report_id}/continue", response_model=ReportRead, status_code=202)
async def continue_run(report: Report = Depends(get_report_for_member), context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    """Next agent pass after answers (no re-parsing)."""
    ensure_quota(context.user)
    return await service.request_run(db, report, mode="continue", user_id=context.id)


@router.get("/{report_id}/questions")
async def list_questions(status: str | None = Query(None, pattern="^(open|answered|skipped|superseded)$"),
                         report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    return await questions.list_questions(db, report, status)


@router.post("/{report_id}/questions/{question_id}/answer")
async def answer_question(question_id: uuid.UUID, payload: questions.AnswerRequest, report: Report = Depends(get_report_for_member),
                          context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await questions.answer_question(db, context, report, question_id, payload)


@router.post("/{report_id}/questions/{question_id}/skip")
async def skip_question(question_id: uuid.UUID, report: Report = Depends(get_report_for_member),
                        context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await questions.skip_question(db, context, report, question_id)


@router.post("/{report_id}/recompute")
async def recompute(report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    """Re-applies classifications/parameters without re-reading the files."""
    service._require_editable(report)
    return {"issues": await service.recompute_and_save(db, report)}


@router.get("/{report_id}/progress")
async def progress(report: Report = Depends(get_report_for_member)):
    return {"status": report.status.value, "progress": report.progress, "error_message": report.error_message}


@router.get("/{report_id}/activity")
async def report_activity(after_id: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000), report: Report = Depends(get_report_for_member),
                          db: AsyncSession = Depends(get_db)):
    """Timeline of what the jobs did (oldest first). Poll with `after_id` = the last `id` received."""
    return {"status": report.status.value, "progress": report.progress, "items": await activity.list_activity(db, report.id, after_id, limit)}


@router.get("/{report_id}/sources")
async def sources(report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    return await service.sources(db, report)


@router.get("/{report_id}/review/groups")
async def review_groups(state: str = Query("unconfirmed", pattern="^(unconfirmed|needs_input|all)$"),
                        report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    return await service.list_groups(db, report, state)


@router.post("/{report_id}/review/confirm")
async def review_confirm(payload: ConfirmRequest, report: Report = Depends(get_report_for_member),
                         context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return {"issues": await service.confirm_groups(db, context, report, payload.items)}


@router.get("/{report_id}/results")
async def results(group_by: str = Query("holding", pattern="^(holding|company|site)$"), include: str = "",
                  report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    return await service.get_results(db, report, group_by, {p for p in include.split(",") if p})


@router.get("/{report_id}/lines")
async def lines(site_id: uuid.UUID | None = None, item_key: str | None = None, effect: str | None = None,
                limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
                report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    try:
        return await service.line_rows(db, report, site_id=site_id, item_key=item_key, effect=effect, limit=limit, offset=offset)
    except ValueError as exc:
        raise BadRequestError("Unknown effect") from exc


@router.get("/{report_id}/trace")
async def trace(site_id: uuid.UUID | None = None, item_key: str = Query(...),
                report: Report = Depends(get_report_for_member), db: AsyncSession = Depends(get_db)):
    return await service.line_rows(db, report, site_id=site_id, item_key=item_key, effect="counted", limit=1000)


@router.post("/{report_id}/publish", response_model=ReportRead)
async def publish(report: Report = Depends(get_report_for_member), context: UserContext = Depends(get_current_user_context),
                  db: AsyncSession = Depends(get_db)):
    return await service.publish(db, context, report)


@router.post("/{report_id}/reopen", response_model=ReportRead, status_code=201)
async def reopen(report: Report = Depends(get_report_for_member), context: UserContext = Depends(get_current_user_context),
                 db: AsyncSession = Depends(get_db)):
    return await service.reopen(db, context, report)


@router.get("/{report_id}/export")
async def export_report(format: str = Query("xlsx", pattern="^(xlsx|csv)$"), report: Report = Depends(get_report_for_member),
                        db: AsyncSession = Depends(get_db)):
    rows, extra = await service.export_rows(db, report)
    if format == "csv":
        body, media = export.build_csv(rows), "text/csv; charset=utf-8"
    else:
        columns = ["وضعیت", "شرکت", "کارگاه", "شرح", "واحد", "مقدار", "فایل", "شیت", "ردیف"]
        body = await asyncio.to_thread(export.build_xlsx, rows, "سایر و مشکل‌دار", columns, extra)
        media = _XLSX
    return Response(content=body, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="volume-report-{str(report.id)[:8]}.{format}"', "Cache-Control": "no-store"})
