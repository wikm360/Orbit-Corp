"""Dollar quota: three windows per user (5 hours and 7 days rolling, the current Jalali month), caps from the role's plan with
optional per-user overrides. Everything that is a number lives in the DB (`quota_plans`, `users.quota_*`, `quota_config`) and is
edited by super admins only; the window lengths and the Jalali month rule are fixed here.

Usage = sum of `llm_usage.cost_micro_usd` of the user (chat, SQL, rerank, volume reports, OCR, embeddings), counted from the
later of the window start and the user's last reset (`users.token_period_start`). The check is soft, like the token one."""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User, UserRole
from app.features.usage.models import LlmUsage, QuotaConfig, QuotaPlan

logger = logging.getLogger(__name__)

TEHRAN = ZoneInfo("Asia/Tehran")
FIVE_HOURS = timedelta(hours=5)
WEEK = timedelta(days=7)
WINDOWS = ("five_hour", "weekly", "monthly")
MAX_MICRO = 10**12


# ---- Jalali calendar (the monthly window starts on the 1st of a Jalali month, Tehran time) ----------------------------

def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        return jy, 1 + days // 31, 1 + days % 31
    return jy, 7 + (days - 186) // 30, 1 + (days - 186) % 30


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    jy += 1595
    days = -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    month_days = (0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gm = 1
    while gm < 13 and gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return gy, gm, gd


def _jalali_month_start(jy: int, jm: int) -> datetime:
    gy, gm, gd = jalali_to_gregorian(jy, jm, 1)
    return datetime(gy, gm, gd, tzinfo=TEHRAN).astimezone(timezone.utc)


def month_bounds(now: datetime) -> tuple[datetime, datetime]:
    """(start of the current Jalali month, start of the next one) in UTC; midnight Tehran time."""
    local = now.astimezone(TEHRAN)
    jy, jm, _ = gregorian_to_jalali(local.year, local.month, local.day)
    ny, nm = (jy + 1, 1) if jm == 12 else (jy, jm + 1)
    return _jalali_month_start(jy, jm), _jalali_month_start(ny, nm)


# ---- configuration (cached a few seconds; local writes invalidate) --------------------------------------------------

@dataclass(frozen=True)
class Plan:
    five_hour: int
    weekly: int
    monthly: int


_TTL = 10.0
_cfg_cache: tuple[float, bool, dict[str, Plan], int | None] | None = None
_org_cache: tuple[float, int] | None = None


def invalidate_cache() -> None:
    global _cfg_cache, _org_cache
    _cfg_cache = _org_cache = None


async def load_config(db: AsyncSession) -> tuple[bool, dict[str, Plan]]:
    enforced, plans, _ = await _load_all(db)
    return enforced, plans


async def _load_all(db: AsyncSession) -> tuple[bool, dict[str, Plan], int | None]:
    global _cfg_cache
    now = time.monotonic()
    if _cfg_cache is not None and now - _cfg_cache[0] < _TTL:
        return _cfg_cache[1], _cfg_cache[2], _cfg_cache[3]
    config = await db.get(QuotaConfig, 1, populate_existing=True)
    plans = {p.role: Plan(p.five_hour_micro, p.weekly_micro, p.monthly_micro) for p in (await db.execute(select(QuotaPlan))).scalars()}
    enforced = bool(config and config.enforced)
    cap = config.org_monthly_cap_micro if config else None
    _cfg_cache = (now, enforced, plans, cap)
    return enforced, plans, cap


async def org_month_used(db: AsyncSession, *, fresh: bool = False) -> int:
    """Everything the organisation spent this Jalali month (all users, pool included), micro-USD. Cached a few seconds."""
    global _org_cache
    now = time.monotonic()
    if not fresh and _org_cache is not None and now - _org_cache[0] < _TTL:
        return _org_cache[1]
    start, _ = month_bounds(datetime.now(timezone.utc))
    used = int(await db.scalar(select(func.coalesce(func.sum(LlmUsage.cost_micro_usd), 0)).where(LlmUsage.created_at >= start)) or 0)
    _org_cache = (now, used)
    return used


async def org_cap_block(db: AsyncSession) -> "WindowStatus | None":
    """The organisation cap as an exhausted window (name `org_monthly`), or None when there is no cap or it is not reached."""
    _, _, cap = await _load_all(db)
    if cap is None:
        return None
    used = await org_month_used(db)
    if used < cap:
        return None
    start, nxt = month_bounds(datetime.now(timezone.utc))
    return WindowStatus("org_monthly", cap, used, start, nxt)


def effective_limits(user: User, plans: dict[str, Plan]) -> dict[str, int | None]:
    """micro-USD cap per window; None = no cap (super admin, `quota_unlimited`, or a role without a plan)."""
    if user.role == UserRole.SUPER_ADMIN or user.quota_unlimited:
        return dict.fromkeys(WINDOWS)
    plan = plans.get(user.role.value)
    overrides = {"five_hour": user.quota_five_hour_override, "weekly": user.quota_weekly_override, "monthly": user.quota_monthly_override}
    return {w: overrides[w] if overrides[w] is not None else (getattr(plan, w) if plan else None) for w in WINDOWS}


# ---- status ----------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class WindowStatus:
    name: str
    limit: int | None
    used: int
    starts_at: datetime
    resets_at: datetime | None  # only filled for an exhausted window: when it frees up (approximately for rolling windows)

    @property
    def exhausted(self) -> bool:
        return self.limit is not None and self.used >= self.limit


def _starts(now: datetime, user: User) -> dict[str, datetime]:
    month_start, _ = month_bounds(now)
    raw = {"five_hour": now - FIVE_HOURS, "weekly": now - WEEK, "monthly": month_start}
    return {w: max(t, user.token_period_start) if user.token_period_start else t for w, t in raw.items()}


async def window_status(db: AsyncSession, user: User, limits: dict[str, int | None], now: datetime | None = None) -> list[WindowStatus]:
    now = now or datetime.now(timezone.utc)
    starts = _starts(now, user)
    cost = LlmUsage.cost_micro_usd
    sums = [func.coalesce(func.sum(cost).filter(LlmUsage.created_at >= starts[w]), 0) for w in WINDOWS]
    row = (await db.execute(
        select(*sums).where(LlmUsage.user_id == user.id, LlmUsage.billed_to == "user", LlmUsage.created_at >= min(starts.values()))
    )).one()
    statuses = [WindowStatus(w, limits[w], int(used), starts[w], None) for w, used in zip(WINDOWS, row)]
    out = []
    for st in statuses:
        if st.exhausted:
            st = WindowStatus(st.name, st.limit, st.used, st.starts_at, await _resets_at(db, user, st, now))
        out.append(st)
    return out


async def _resets_at(db: AsyncSession, user: User, st: WindowStatus, now: datetime) -> datetime:
    if st.name == "monthly":
        return month_bounds(now)[1]
    length = FIVE_HOURS if st.name == "five_hour" else WEEK
    rows = (await db.execute(
        select(LlmUsage.created_at, LlmUsage.cost_micro_usd)
        .where(LlmUsage.user_id == user.id, LlmUsage.billed_to == "user", LlmUsage.created_at >= st.starts_at, LlmUsage.cost_micro_usd > 0)
        .order_by(LlmUsage.created_at)
    )).all()
    used = st.used
    for created_at, c in rows:  # usage frees up as the oldest calls leave the window
        used -= c
        if used < (st.limit or 0):
            return created_at + length
    return now + length


async def blocking_window(db: AsyncSession, user: User) -> WindowStatus | None:
    """The first exhausted window, or None when the user may work (shadow mode, super admin, no caps, or still under)."""
    if user.role == UserRole.SUPER_ADMIN:
        return None
    enforced, plans = await load_config(db)
    if not enforced:
        return None
    if (org := await org_cap_block(db)) is not None:
        return org
    limits = effective_limits(user, plans)
    if all(v is None for v in limits.values()):
        return None
    return next((s for s in await window_status(db, user, limits) if s.exhausted), None)


async def user_quota(db: AsyncSession, user: User) -> dict:
    """Everything a client needs to show a user's dollar quota (used by /auth/me/quota and the admin screen)."""
    enforced, plans = await load_config(db)
    limits = effective_limits(user, plans)
    statuses = await window_status(db, user, limits)
    overrides = {"five_hour": user.quota_five_hour_override, "weekly": user.quota_weekly_override, "monthly": user.quota_monthly_override}
    return {
        "enforced": enforced,
        "unlimited": user.role == UserRole.SUPER_ADMIN or user.quota_unlimited,
        "windows": [{
            "name": s.name, "limit_usd": None if s.limit is None else s.limit / 1e6, "used_usd": round(s.used / 1e6, 6),
            "exhausted": s.exhausted, "overridden": overrides[s.name] is not None,
            "starts_at": s.starts_at, "resets_at": s.resets_at,
        } for s in statuses],
    }


async def my_usage(db: AsyncSession, user: User, days: int = 30) -> dict:
    """A user's own consumption for the profile page: this Jalali month by purpose (cost and calls, charged to the user), what the
    shared setup pool paid for their uploads, and the daily cost of the last `days` days. Informational: caps come from `user_quota`."""
    now = datetime.now(timezone.utc)
    month_start, month_next = month_bounds(now)
    cost = func.coalesce(func.sum(LlmUsage.cost_micro_usd), 0)
    own = (LlmUsage.user_id == user.id, LlmUsage.billed_to == "user")
    by_purpose = (await db.execute(
        select(LlmUsage.purpose, cost, func.count()).where(*own, LlmUsage.created_at >= month_start).group_by(LlmUsage.purpose).order_by(cost.desc())
    )).all()
    pool = await db.scalar(select(cost).where(LlmUsage.user_id == user.id, LlmUsage.billed_to == "org_setup", LlmUsage.created_at >= month_start))
    day = func.date_trunc("day", LlmUsage.created_at, "Asia/Tehran")
    daily = (await db.execute(
        select(day, cost).where(*own, LlmUsage.created_at >= now - timedelta(days=days)).group_by(day).order_by(day)
    )).all()
    return {
        "month": {"start": month_start, "next_start": month_next},
        "month_used_usd": round(sum(int(c) for _, c, _ in by_purpose) / 1e6, 6),
        "setup_pool_usd": round(int(pool or 0) / 1e6, 6),
        "by_purpose": [{"purpose": p, "cost_usd": round(int(c) / 1e6, 6), "calls": n} for p, c, n in by_purpose],
        "daily": [{"date": d.date().isoformat(), "cost_usd": round(int(c) / 1e6, 6)} for d, c in daily],
    }
