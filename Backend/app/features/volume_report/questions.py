"""Question cards: validation of model-made specs, impact ranking (by code), answers and skips.

A question never blocks the agent; answering applies the same human classification path as `review/confirm`."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.features.volume_report import service
from app.features.volume_report.agent.index import GroupIndex
from app.features.volume_report.models import (
    Conversion, Item, Question, QuestionKind, QuestionStatus, Report, ReportFile, ReportStatus, Site, SiteKind,
)
from app.features.volume_report.schemas import ConfirmItem
from app.features.volume_report.seed import bump_catalog_version

settings = get_settings()

# There is no "remove from report": whatever is not counted is "other" and stays visible. "exclude" is kept as an alias
# of "other" so questions stored earlier (or proposed by the agent) keep working.
FIXED_OPTIONS = {"exclude": "سایر (نامنطبق)", "unknown": "نمی‌دانم", "other": "سایر (نامنطبق)"}
SITE_KIND_LABELS = {"road": "راهسازی", "mining": "معدن", "other": "سایر"}
PARAMS = {"density_t_per_m3", "thickness_m", "cross_section_m2"}


class QuestionOption(BaseModel):
    key: str
    label: str = ""


class NumberSpec(BaseModel):
    param_key: Literal["density_t_per_m3", "thickness_m", "cross_section_m2"]
    unit: str = Field(max_length=32)
    min: float = 0
    max: float = 1_000_000


class QuestionSpec(BaseModel):
    kind: Literal["choice", "multi_choice", "number", "text", "confirm_group"]
    prompt: str = Field(min_length=1, max_length=300)
    group_ids: list[str] = Field(min_length=1, max_length=50)
    options: list[QuestionOption] = []
    number: NumberSpec | None = None
    remember_scopes: list[Literal["global", "line"]] = ["global", "line"]
    default_remember: Literal["global", "line"] = "global"

    @field_validator("options")
    @classmethod
    def _max_four(cls, v):
        if len(v) > 4:
            raise ValueError("at most 4 options")
        return v


class AnswerRequest(BaseModel):
    choice_keys: list[str] = []
    number: float | None = None
    text: str | None = Field(default=None, max_length=1000)
    remember_scope: Literal["global", "line"] = "global"


def _read(q: Question, locations: list[dict] | None = None) -> dict:
    return {
        "id": q.id, "kind": q.kind.value, "spec": q.spec, "group_keys": q.group_keys, "impact_score": q.impact_score,
        "status": q.status.value, "answer": q.answer, "answered_at": q.answered_at, "created_at": q.created_at,
        "locations": locations if locations is not None else [],
    }


async def _enrich_questions(db: AsyncSession, report: Report, qs: list[Question]) -> list[dict]:
    """Attaches source file/sheet/section/row provenance so reviewers know where each item or parameter came from."""
    if not qs:
        return []
    line_rows = await service._report_lines_with_sources(db, report.id)
    file_names = await service._report_file_names(db, report.id)
    by_group: dict[str, list[tuple]] = {}
    by_site: dict[str, list[tuple]] = {}
    for line, site, filename, company_name in line_rows:
        coord = (filename, company_name, site.name, line.sheet_name, line.section_heading, line.row_no)
        by_group.setdefault(line.group_key, []).append(coord)
        by_site.setdefault(str(site.id), []).append(coord)

    out: list[dict] = []
    for q in qs:
        spec = q.spec or {}
        if q.group_keys:
            raw: list[tuple] = []
            for gk in q.group_keys:
                raw.extend(by_group.get(gk, []))
            if not raw and spec.get("site_id"):
                raw = by_site.get(str(spec["site_id"]), [])
            locs = service.summarize_locations(raw)
        elif spec.get("system") == "site_kind" and spec.get("site_id"):
            locs = service.summarize_locations(by_site.get(str(spec["site_id"]), []))
        elif spec.get("system") == "layout":
            file_id = str(spec.get("file_id") or "")
            file_info = file_names.get(file_id)
            sheet = spec.get("sheet")
            if file_info or sheet:
                locs = [{
                    "filename": file_info[0] if file_info else "",
                    "company": file_info[1] if file_info else None,
                    "site": None,
                    "sheet": sheet,
                    "section": None,
                    "row_nos": [],
                    "n_lines": 0,
                }]
            else:
                locs = []
        else:
            locs = []
        out.append(_read(q, locs))
    return out


async def create_from_spec(db: AsyncSession, report: Report, index: GroupIndex, raw: dict, run_id: uuid.UUID | None) -> Question:
    """Validates a model-made spec against this report (group ids, catalog keys). Raises BadRequest/NotFound with a reason."""
    try:
        spec = QuestionSpec.model_validate(raw)
    except Exception as exc:
        raise BadRequestError(f"Invalid question spec: {str(exc)[:300]}") from exc
    groups = [index.resolve(gid) for gid in spec.group_ids]
    if any(g.asked for g in groups):
        raise ConflictError("A question is already open for one of these groups")
    if any(g.locked for g in groups):
        raise ConflictError("One of these groups is already confirmed")
    if spec.kind in ("choice", "confirm_group", "multi_choice"):
        keys = [o.key for o in spec.options]
        if spec.kind == "choice" and not 2 <= len(keys) <= 4:
            raise BadRequestError("A choice question needs 2 to 4 options")
        bad = [k for k in keys if k not in index.items and k not in FIXED_OPTIONS]
        if bad:
            raise BadRequestError(f"Unknown option keys: {bad}. Use catalog item keys, exclude, unknown or other.")
        # Labels come from code, never from the model.
        keys = ["other" if k == "exclude" else k for k in keys]
        options = [{"key": k, "label": index.items[k].title_fa if k in index.items else FIXED_OPTIONS[k]} for k in dict.fromkeys(keys)]
        for k in ("other", "unknown"):
            if k not in keys:
                options.append({"key": k, "label": FIXED_OPTIONS[k]})
    else:
        options = []
    if spec.kind == "number" and spec.number is None:
        raise BadRequestError("A number question needs a number spec")
    data = spec.model_dump()
    data.update(options=options, group_ids=[g.id for g in groups])
    question = Question(
        report_id=report.id, run_id=run_id, kind=QuestionKind(spec.kind), spec=data,
        group_keys=[g.key for g in groups], impact_score=impact_score(index, [g.key for g in groups]),
    )
    db.add(question)
    await db.flush()
    return question


def impact_score(index: GroupIndex, keys: list[str]) -> float:
    """Share of the groups' quantity within the total of the same unit across the report (computed by code, not the model)."""
    totals: dict[str, Decimal] = {}
    for g in index.groups:
        totals[g.unit] = totals.get(g.unit, Decimal(0)) + abs(g.quantity)
    score = Decimal(0)
    for key in keys:
        g = index.by_key.get(key)
        if g is not None and totals.get(g.unit):
            score += abs(g.quantity) / totals[g.unit]
    return float(score)


async def trim_open_questions(db: AsyncSession, report: Report) -> int:
    """Keeps the highest-impact open questions up to VR_MAX_QUESTIONS_PER_PASS; the dropped ones disappear and their
    groups stay `needs_input` (they still hold back publishing in strict mode)."""
    open_q = (await db.execute(select(Question).where(Question.report_id == report.id, Question.status == QuestionStatus.OPEN)
                               .order_by(Question.impact_score.desc(), Question.created_at))).scalars().all()
    dropped = open_q[settings.vr_max_questions_per_pass:]
    for q in dropped:
        await db.delete(q)
    await db.flush()
    return len(dropped)


async def list_questions(db: AsyncSession, report: Report, status: str | None) -> list[dict]:
    query = select(Question).where(Question.report_id == report.id).order_by(Question.impact_score.desc(), Question.created_at)
    if status:
        query = query.where(Question.status == QuestionStatus(status))
    rows = (await db.execute(query)).scalars().all()
    return await _enrich_questions(db, report, rows)


async def _get_open(db: AsyncSession, report: Report, question_id: uuid.UUID) -> Question:
    q = await db.get(Question, question_id)
    if q is None or q.report_id != report.id:  # ownership: the question must belong to this report
        raise NotFoundError("Question not found")
    if q.status != QuestionStatus.OPEN:
        raise ConflictError("The question is not open")
    return q


async def answer_question(db: AsyncSession, context: UserContext, report: Report, question_id: uuid.UUID, answer: AnswerRequest) -> dict:
    service._require_editable(report)
    q = await _get_open(db, report, question_id)
    spec = q.spec
    system = spec.get("system")
    if system == "site_kind":
        key = answer.choice_keys[0] if len(answer.choice_keys) == 1 else None
        if key not in SITE_KIND_LABELS:
            raise BadRequestError("Choose road, mining or other")
        site = await db.get(Site, uuid.UUID(spec["site_id"]))
        if site is None:
            raise NotFoundError("Site not found")
        service.require_settings_editor(context)
        site.kind, site.kind_confirmed = SiteKind(key), True
        await bump_catalog_version(db)
    elif system == "layout":
        if answer.choice_keys != ["confirm"]:
            q.status, q.answered_by, q.answered_at = QuestionStatus.SKIPPED, context.id, datetime.now(timezone.utc)
            await db.commit()
            return _read(q)
        rfile = await db.get(ReportFile, uuid.UUID(spec["file_id"]))
        if rfile is None or rfile.report_id != report.id:  # ownership
            raise NotFoundError("File not found")
        rfile.sheet_log = [({**e, "layout_override": spec["layout"]} if e.get("sheet") == spec["sheet"] else e) for e in rfile.sheet_log]
        # The confirmed layout takes effect on the next full run (POST /run).
    elif q.kind == QuestionKind.NUMBER:
        number = spec.get("number") or {}
        if answer.number is None or not (number.get("min", 0) <= answer.number <= number.get("max", 1e12)) or answer.number <= 0:
            raise BadRequestError("The number is missing or outside the allowed range")
        item_id = site_id = None
        if spec.get("item_key"):
            item_id = (await db.execute(select(Item.id).where(Item.key == spec["item_key"]))).scalar_one_or_none()
        if answer.remember_scope == "line" and spec.get("site_id"):
            site_id = uuid.UUID(spec["site_id"])
        existing = (await db.execute(select(Conversion).where(
            Conversion.key == number["param_key"],
            Conversion.item_id.is_(None) if item_id is None else Conversion.item_id == item_id,
            Conversion.site_id.is_(None) if site_id is None else Conversion.site_id == site_id))).scalar_one_or_none()
        if existing is None:
            existing = Conversion(key=number["param_key"], item_id=item_id, site_id=site_id, value=Decimal(str(answer.number)), unit=number["unit"])
            db.add(existing)
        existing.value, existing.unit, existing.updated_by = Decimal(str(answer.number)), number["unit"], context.id
        await bump_catalog_version(db)
    elif q.kind == QuestionKind.TEXT:
        pass  # a note only; never changes a decision directly
    else:
        if len(answer.choice_keys) > 1:
            raise BadRequestError("Only one option can be applied to a group")
        entries = await _entries_for(db, report, q, answer.choice_keys[0] if answer.choice_keys else None, answer.remember_scope)
        await service.confirm_groups(db, context, report, entries)
    q.status, q.answer = QuestionStatus.ANSWERED, answer.model_dump()
    q.answered_by, q.answered_at = context.id, datetime.now(timezone.utc)
    await db.flush()
    await _supersede_resolved(db, report)
    await service.recompute_and_save(db, report)
    await refresh_system_questions(db, report)
    await db.commit()
    return _read(q)


async def _entries_for(db: AsyncSession, report: Report, q: Question, key: str | None, scope: str) -> list[ConfirmItem]:
    index = await GroupIndex.load(db, report)
    entries: list[ConfirmItem] = []
    for gk in q.group_keys:
        g = index.by_key.get(gk)
        if g is None:
            continue
        current = g.classification
        if key is None:  # confirm_group without a choice: accept the agent's proposal as it stands
            if current is None or current.item_id is None and current.exclude_reason is None:
                raise BadRequestError("Choose an option")
            item_key = next((i.key for i in index.items.values() if i.id == current.item_id), None)
            entries.append(ConfirmItem(group_key=gk, item_key=item_key, exclude_reason=current.exclude_reason, role=current.role.value, remember_scope=scope))
            continue
        role = current.role.value if current is not None and current.role.value != "na" else ("supply" if g.role_hint == "supply" else "na")
        if key in index.items:
            entries.append(ConfirmItem(group_key=gk, item_key=key, role=role, remember_scope=scope))
        elif key in ("exclude", "other"):  # "other" is remembered like any item when the user asks for it
            entries.append(ConfirmItem(group_key=gk, disposition="unmatched", role=role, remember_scope=scope))
        elif key == "unknown":  # not decided yet: kept visible, deliberately not remembered
            entries.append(ConfirmItem(group_key=gk, disposition="unmatched", remember_scope="line"))
        else:
            raise BadRequestError(f"Unknown option: {key}")
    if not entries:
        raise BadRequestError("The question's groups no longer exist")
    return entries


async def skip_question(db: AsyncSession, context: UserContext, report: Report, question_id: uuid.UUID) -> dict:
    """The user declines to decide: the groups are kept visibly as `unmatched` and the question closes."""
    service._require_editable(report)
    q = await _get_open(db, report, question_id)
    if q.spec.get("system") or q.kind == QuestionKind.NUMBER:
        q.status, q.answered_by, q.answered_at = QuestionStatus.SKIPPED, context.id, datetime.now(timezone.utc)
        await db.flush()
    else:
        await service.confirm_groups(
            db, context, report, [ConfirmItem(group_key=gk, disposition="unmatched", remember_scope="line") for gk in q.group_keys]
        )
        q.status, q.answered_by, q.answered_at = QuestionStatus.SKIPPED, context.id, datetime.now(timezone.utc)
    await db.flush()
    await _supersede_resolved(db, report)
    await service.recompute_and_save(db, report)
    await db.commit()
    return _read(q)


async def _supersede_resolved(db: AsyncSession, report: Report) -> None:
    index = await GroupIndex.load(db, report)
    for q in (await db.execute(select(Question).where(Question.report_id == report.id, Question.status == QuestionStatus.OPEN))).scalars():
        if q.group_keys and all(index.by_key.get(k) is None or index.by_key[k].locked for k in q.group_keys):
            q.status = QuestionStatus.SUPERSEDED


async def refresh_system_questions(db: AsyncSession, report: Report) -> None:
    """Questions that need no model: unconfirmed site kinds, missing conversion parameters, unit mismatches."""
    from app.features.volume_report.models import Effect, Line, LineResult, ReportFile

    existing = (await db.execute(select(Question).where(Question.report_id == report.id, Question.status == QuestionStatus.OPEN))).scalars().all()
    seen = {(q.spec.get("system"), q.spec.get("site_id"), q.spec.get("param_key"), tuple(q.group_keys)) for q in existing if q.spec.get("system")}

    sites = (await db.execute(
        select(Site).join(Line, Line.site_id == Site.id).join(ReportFile, ReportFile.id == Line.report_file_id)
        .where(ReportFile.report_id == report.id, Site.kind_confirmed.is_(False)).distinct())).scalars().all()
    for site in sites:
        if ("site_kind", str(site.id), None, ()) in seen:
            continue
        db.add(Question(
            report_id=report.id, kind=QuestionKind.CHOICE, impact_score=1.0,
            spec={"system": "site_kind", "kind": "choice", "prompt": f"نوع کارگاه «{site.name}» چیست؟", "site_id": str(site.id), "group_ids": [],
                  "options": [{"key": k, "label": v} for k, v in SITE_KIND_LABELS.items()], "remember_scopes": ["global"], "default_remember": "global"},
        ))

    index = await GroupIndex.load(db, report)
    rows = (await db.execute(
        select(Line.group_key, Line.site_id, LineResult.effect, LineResult.note, LineResult.item_id)
        .join(LineResult, LineResult.line_id == Line.id).join(ReportFile, ReportFile.id == Line.report_file_id)
        .where(ReportFile.report_id == report.id, LineResult.effect.in_([Effect.NO_CONVERSION, Effect.UNIT_MISMATCH])))).all()
    items = {i.id: i for i in (await db.execute(select(Item))).scalars()}
    grouped: dict[tuple, set[str]] = {}
    for gk, site_id, effect, note, item_id in rows:
        grouped.setdefault((effect, note if effect == Effect.NO_CONVERSION else None, str(site_id), item_id), set()).add(gk)
    for (effect, param, site_id, item_id), keys in grouped.items():
        keys_t = tuple(sorted(keys))
        item = items.get(item_id)
        title = item.title_fa if item else ""
        if effect == Effect.NO_CONVERSION:
            if ("no_conversion", site_id, param, keys_t) in seen:
                continue
            unit = {"density_t_per_m3": "t/m3", "thickness_m": "m", "cross_section_m2": "m2"}[param]
            param_label = {"density_t_per_m3": "چگالی", "thickness_m": "ضخامت", "cross_section_m2": "سطح مقطع"}.get(param, param)
            db.add(Question(
                report_id=report.id, kind=QuestionKind.NUMBER, group_keys=list(keys_t), impact_score=impact_score(index, list(keys_t)),
                spec={"system": "no_conversion", "kind": "number", "prompt": f"برای تبدیل واحد «{title}» مقدار {param_label} ({unit}) را وارد کنید.",
                      "site_id": site_id, "item_key": item.key if item else None, "group_ids": [k[:10] for k in keys_t], "options": [],
                      "number": {"param_key": param, "unit": unit, "min": 0, "max": 1_000_000}, "remember_scopes": ["global", "line"], "default_remember": "global"},
            ))
        else:
            if ("unit_mismatch", site_id, None, keys_t) in seen:
                continue
            db.add(Question(
                report_id=report.id, kind=QuestionKind.CHOICE, group_keys=list(keys_t), impact_score=impact_score(index, list(keys_t)),
                spec={"system": "unit_mismatch", "kind": "choice", "prompt": f"واحد این ردیف‌ها با آیتم «{title}» سازگار نیست؛ چه کنیم؟",
                      "site_id": site_id, "group_ids": [k[:10] for k in keys_t],
                      "options": [{"key": "other", "label": FIXED_OPTIONS["other"]}, {"key": "unknown", "label": FIXED_OPTIONS["unknown"]}],
                      "remember_scopes": ["global", "line"], "default_remember": "line"},
            ))
    await db.flush()


async def supersede_site_questions(db: AsyncSession, site_id: uuid.UUID) -> None:
    """The site's kind was settled elsewhere (settings API): its open "what kind is this site" cards are moot."""
    for q in (await db.execute(select(Question).where(Question.status == QuestionStatus.OPEN))).scalars():
        if q.spec.get("system") == "site_kind" and q.spec.get("site_id") == str(site_id):
            q.status = QuestionStatus.SUPERSEDED
