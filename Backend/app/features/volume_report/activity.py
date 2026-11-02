"""User-facing timeline of a report job (`vr_activity`): what the pipeline and the agent did, in Persian, with counts only.

Built by code from tool names/results, never from model prose, and never with quantities. The table is the single source;
the UI polls it with a cursor, so the history survives leaving the page."""

import re
import uuid
from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.volume_report.models import Activity


async def current_attempt(db: AsyncSession, report_id: uuid.UUID) -> int:
    return int(await db.scalar(select(func.coalesce(func.max(Activity.attempt), 1)).where(Activity.report_id == report_id)) or 1)


async def log_activity(db: AsyncSession, report_id: uuid.UUID, phase: str, title: str, *, kind: str = "info",
                       detail: dict | None = None, commit: bool = True, new_attempt: bool = False) -> None:
    """`kind`: info | step | success | warn | error | question. `commit=False` when the caller commits right after."""
    attempt = await current_attempt(db, report_id)
    if new_attempt:
        attempt = int(await db.scalar(select(func.max(Activity.attempt)).where(Activity.report_id == report_id)) or 0) + 1
    db.add(Activity(report_id=report_id, attempt=attempt, phase=phase, kind=kind, title=title[:400], detail=detail or {}))
    if commit:
        await db.commit()
    else:
        await db.flush()


async def list_activity(db: AsyncSession, report_id: uuid.UUID, after_id: int = 0, limit: int = 500) -> list[dict]:
    rows = (await db.execute(select(Activity).where(Activity.report_id == report_id, Activity.id > after_id)
                             .order_by(Activity.id).limit(limit))).scalars().all()
    return [{"id": a.id, "attempt": a.attempt, "phase": a.phase, "kind": a.kind, "title": a.title, "detail": a.detail,
             "created_at": a.created_at} for a in rows]


def _num(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def describe_tool(name: str, args: dict, result: str, ok: bool) -> tuple[str, str, dict]:
    """(title, kind, detail) for one agent tool call. Counts only."""
    if not ok:
        if result.startswith("Duplicate call"):
            return "فراخوانی تکراری نادیده گرفته شد", "info", {"tool": name}
        return f"مرحله‌ی «{_TOOL_FA.get(name, name)}» با خطا روبه‌رو شد و دوباره تلاش می‌شود", "warn", {"tool": name, "error": result[:200]}
    detail: dict[str, Any] = {"tool": name}
    if name == "list_sources":
        total, open_ = _num(r"total=(\d+)", result), _num(r"open=(\d+)", result)
        return f"بررسی منابع و کارگاه‌ها: {total} گروه، {open_} گروه هنوز بی‌تصمیم", "step", detail
    if name == "get_groups":
        return f"مرور گروه‌های {_FILTER_FA.get(args.get('filter'), '')}: {_num(r'matching=(\d+)', result)} مورد مطابق", "step", detail
    if name == "search_groups":
        return f"جستجوی گروه‌های هم‌معنی: {_num(r'matches=(\d+)', result)} مورد", "step", detail
    if name == "get_context":
        return "بررسی ردیف‌ها و سرفصل‌های اطراف یک گروه", "step", detail
    if name == "search_decisions":
        return "جستجوی تصمیم‌های مشابهِ ثبت‌شده در حافظه", "step", detail
    if name == "get_catalog":
        return "مرور فهرست آیتم‌های گزارش", "step", detail
    if name == "get_conversion_params":
        return "بررسی پارامترهای تبدیل واحد", "step", detail
    if name == "classify":
        done, rejected = _num(r"classified=(\d+)", result) or 0, _num(r"rejected=(\d+)", result) or 0
        by_item = Counter(e.get("item_key") for e in args.get("items", []) if isinstance(e, dict))
        detail["items"] = dict(by_item)
        suffix = f" ({rejected} مورد رد شد)" if rejected else ""
        return f"{done} گروه به آیتم‌ها نسبت داده شد{suffix}", "warn" if rejected and not done else "step", detail
    if name == "exclude":
        done = _num(r"excluded=(\d+)", result) or 0
        detail["reasons"] = dict(Counter(e.get("reason_code") for e in args.get("items", []) if isinstance(e, dict)))
        return f"{done} گروه از گزارش حذف شد", "step", detail
    if name == "mark_duplicate":
        return "یک گروه به‌عنوان تکراری علامت خورد", "step", detail
    if name == "mark_nonphysical":
        return "یک گروه غیرفیزیکی (مقطوع/ساعت/درصد) علامت خورد", "step", detail
    if name == "ask_user":
        detail["prompt"] = str(args.get("prompt", ""))[:300]
        return f"برای شما سؤال ثبت شد: {str(args.get('prompt', ''))[:160]}", "question", detail
    if name == "preview_totals":
        return "بررسی کلی نتایج (بدون عدد)", "step", detail
    if name == "check_coverage":
        left = _num(r"uncovered=(\d+)", result)
        return ("همه‌ی گروه‌ها تکلیف دارند" if left is None else f"{left} گروه هنوز بی‌تکلیف است"), "step", detail
    if name == "finish_pass":
        return "بررسی هوشمند به پایان رسید", "success", detail
    if name == "inspect_raw":
        return f"نگاه به ردیف‌های خام شیت «{args.get('sheet', '')}»", "step", detail
    if name == "propose_layout":
        return f"چیدمان پیشنهادی شیت «{args.get('sheet', '')}» برای تأیید شما ثبت شد", "question", detail
    return f"اجرای «{name}»", "step", detail


_FILTER_FA = {"unresolved": "باز", "unconfirmed": "تأییدنشده", "needs_input": "نیازمند تصمیم", "all": "گزارش"}
_TOOL_FA = {
    "list_sources": "بررسی منابع", "get_groups": "مرور گروه‌ها", "search_groups": "جستجوی گروه", "get_context": "بررسی زمینه",
    "search_decisions": "جستجوی تصمیم‌ها", "get_catalog": "مرور فهرست", "get_conversion_params": "پارامترهای تبدیل",
    "classify": "نسبت‌دادن به آیتم", "exclude": "حذف گروه", "mark_duplicate": "علامت تکراری", "mark_nonphysical": "علامت غیرفیزیکی",
    "ask_user": "ثبت سؤال", "preview_totals": "بررسی نتایج", "check_coverage": "بررسی پوشش", "finish_pass": "پایان بررسی",
    "inspect_raw": "بررسی ردیف خام", "propose_layout": "پیشنهاد چیدمان",
}
