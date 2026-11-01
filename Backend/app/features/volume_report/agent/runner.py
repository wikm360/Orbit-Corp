"""One agent pass. Own simple loop (not the chat AgentEngine): fresh prompt + DB state each pass, no transcript kept
for resume (steps are stored only for audit), fixed step budget, last step forbids tools. The model never sees quantities."""

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.features.volume_report import questions
from app.features.volume_report.agent.index import GroupIndex
from app.features.volume_report.agent.playbook import build_system_prompt
from app.features.volume_report.agent.tools import ToolContext, VrToolRegistry
from app.features.volume_report.models import (
    AgentRun, AgentStep, Classification, ClassificationSource, Disposition, Question, QuestionStatus, Report, ReportFile, RunStatus,
)
from app.providers.llm_provider import LLMProvider

logger = logging.getLogger(__name__)
settings = get_settings()


def _canonical(name: str, raw: str) -> str:
    try:
        payload = json.dumps(json.loads(raw or "{}"), sort_keys=True, ensure_ascii=False)
    except ValueError:
        payload = raw or ""
    return hashlib.sha256(f"{name}:{payload}".encode()).hexdigest()


async def next_pass_no(db: AsyncSession, report: Report) -> int:
    return int(await db.scalar(select(func.coalesce(func.max(AgentRun.pass_no), 0)).where(AgentRun.report_id == report.id)) or 0) + 1


def _run_state(index: GroupIndex, pass_no: int) -> str:
    return (f"pass #{pass_no}. groups total={len(index.groups)} unresolved={len(index.unresolved())}. "
            f"Start with list_sources, then get_groups(filter=unresolved). Finish with check_coverage then finish_pass.")


def _mark_leftovers(db: AsyncSession, report_id: uuid.UUID, index: GroupIndex, reason: str) -> None:
    """Groups nobody decided stay needs_input and say why; they hold back publishing in strict mode."""
    for g in index.unresolved():
        if g.classification is not None:
            g.classification.reason = reason
        else:
            db.add(Classification(report_id=report_id, group_key=g.key, disposition=Disposition.NEEDS_INPUT, confirmed=False,
                                  source=ClassificationSource.SYSTEM, reason=reason))


async def run_pass(db: AsyncSession, report: Report, provider: LLMProvider, lexicon, model_name: str = "") -> AgentRun:
    run = AgentRun(report_id=report.id, pass_no=await next_pass_no(db, report), model=model_name or None)
    db.add(run)
    await db.commit()
    index = await GroupIndex.load(db, report)
    files = (await db.execute(select(ReportFile).where(ReportFile.report_id == report.id))).scalars().all()
    layout_sheets = {e["sheet"]: f for f in files for e in f.sheet_log if e.get("layout_unknown")}
    registry = VrToolRegistry(with_layout=bool(layout_sheets))
    ctx = ToolContext(db=db, report=report, run_id=run.id, index=index, lexicon=lexicon, layout_sheets=layout_sheets)
    messages = [{"role": "system", "content": await build_system_prompt(db)}, {"role": "user", "content": _run_state(index, run.pass_no)}]
    seen: dict[str, str] = {}
    finished = False
    try:
        for step in range(1, settings.vr_agent_max_steps + 1):
            last = step == settings.vr_agent_max_steps
            result = await provider.complete(messages, tools=registry.specs(), tool_choice="none" if last else "auto")
            run.prompt_tokens += result["usage"]["prompt_tokens"]
            run.completion_tokens += result["usage"]["completion_tokens"]
            run.steps = step
            calls = result["tool_calls"]
            if not calls:
                break  # the model answered in prose without finishing: leftovers stay open below
            messages.append({
                "role": "assistant", "content": result["content"] or None,
                "tool_calls": [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls],
            })
            for call in calls:
                canonical = _canonical(call["name"], call["arguments"])
                started = time.monotonic()
                if canonical in seen:
                    text, ok = "Duplicate call in this pass; earlier result: " + seen[canonical][:300], False
                else:
                    text, ok = await registry.dispatch(ctx, call["name"], call["arguments"])
                    seen[canonical] = text
                try:
                    arguments = json.loads(call["arguments"] or "{}")
                except ValueError:
                    arguments = {"raw": call["arguments"][:200]}
                db.add(AgentStep(run_id=run.id, step_no=step, tool_name=call["name"], arguments=arguments if isinstance(arguments, dict) else {},
                                 result_summary=text[:300], duration_ms=int((time.monotonic() - started) * 1000)))
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": text[:6000]})
                if call["name"] == "finish_pass" and ok:
                    finished = True
            await db.commit()
            if finished:
                break
        await questions.trim_open_questions(db, report)
        open_q = await db.scalar(select(func.count()).select_from(Question).where(Question.report_id == report.id, Question.status == QuestionStatus.OPEN))
        # Groups the pass never reached stay needs_input and say why (they hold back publishing in strict mode).
        _mark_leftovers(db, report.id, index, "agent_incomplete")
        run.status = RunStatus.AWAITING_USER if open_q else RunStatus.COMPLETED
    except Exception as exc:  # provider outage, malformed completion...: never fail the report for this
        logger.exception("Volume report %s agent pass failed", report.id)
        run_id, report_id = run.id, report.id
        await db.rollback()
        await db.refresh(report)  # rollback expires every loaded object
        run = await db.get(AgentRun, run_id)
        run.status, run.error_message = RunStatus.FAILED, f"{type(exc).__name__}"
        _mark_leftovers(db, report_id, await GroupIndex.load(db, report), "agent_failed")
    run.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return run
