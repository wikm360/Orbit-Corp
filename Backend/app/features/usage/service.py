"""Per-user token quota: metering, enforcement and the admin operations.

Metering is ambient: an entry point opens `usage_scope(user_id, purpose)` and every model call inside it (the provider
reports usage after each call) is recorded for that user, so no call signature changes. Usage that counts toward the quota
is added to `users.tokens_used` with one atomic UPDATE (concurrent calls cannot lose updates). The quota is soft: the check
runs before a turn and between agent steps, so a limit can be overshot by at most one model call."""

import contextlib
import contextvars
import logging
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError, QuotaExceededError
from app.features.auth.models import User, UserRole
from app.features.usage import pricing, quota
from app.features.usage.models import LlmUsage, ModelPrice, QuotaConfig, QuotaPlan

logger = logging.getLogger(__name__)

MAX_LIMIT = 10**12
# Purposes that are recorded but never limited: stopping them half-way would leave an uploaded document half-processed.
UNMETERED_PURPOSES = {"ocr", "embedding"}


@dataclass(frozen=True)
class UsageScope:
    user_id: uuid.UUID
    purpose: str
    conversation_id: uuid.UUID | None = None
    billed_to: str = "user"  # `org_setup` = charged to the shared setup pool (project-upload ingestion), not to the user's quota


_scope: contextvars.ContextVar[UsageScope | None] = contextvars.ContextVar("llm_usage_scope", default=None)


def current_user_id() -> uuid.UUID | None:
    scope = _scope.get()
    return scope.user_id if scope else None


@contextlib.contextmanager
def usage_scope(user_id: uuid.UUID | None, purpose: str, conversation_id: uuid.UUID | None = None, billed_to: str = "user"):
    """Attribute every model call inside the block to `user_id` (no-op when there is no user)."""
    token = _scope.set(UsageScope(user_id, purpose, conversation_id, billed_to) if user_id is not None else None)
    try:
        yield
    finally:
        _scope.reset(token)


@contextlib.contextmanager
def usage_purpose(purpose: str):
    """Relabel the calls inside the block (e.g. SQL generation inside a chat turn); keeps the user. No-op outside a scope."""
    scope = _scope.get()
    token = _scope.set(replace(scope, purpose=purpose) if scope else None)
    try:
        yield
    finally:
        _scope.reset(token)


async def record_usage(model: str, prompt_tokens: int, completion_tokens: int = 0, cached_tokens: int = 0, *, purpose: str | None = None) -> None:
    """Called by the providers after each model call. Never raises: metering must not break an answer."""
    scope = _scope.get()
    if scope is None or not (prompt_tokens or completion_tokens):
        return
    purpose = purpose or scope.purpose
    counted = purpose not in UNMETERED_PURPOSES
    try:
        async with async_session_factory() as db:
            cost = pricing.cost_micro_usd(await pricing.load_prices(db), model, prompt_tokens, completion_tokens)
            db.add(LlmUsage(user_id=scope.user_id, purpose=purpose, model=model[:200], prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens, cached_tokens=cached_tokens, counts_toward_quota=counted,
                            conversation_id=scope.conversation_id, cost_micro_usd=cost, billed_to=scope.billed_to))
            if counted:
                await db.execute(update(User).where(User.id == scope.user_id).values(tokens_used=User.tokens_used + prompt_tokens + completion_tokens))
            await db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Could not record LLM usage for user %s", scope.user_id)


async def record_pages(model: str, pages: int = 1, *, purpose: str | None = None) -> None:
    """Per-page priced call (Mistral OCR layout analysis): recorded with its flat cost, never limited. Never raises."""
    scope = _scope.get()
    if scope is None or pages <= 0:
        return
    try:
        async with async_session_factory() as db:
            cost = await pricing.page_cost_micro(db, model, pages)
            db.add(LlmUsage(user_id=scope.user_id, purpose=purpose or scope.purpose, model=model[:200], prompt_tokens=0, completion_tokens=0,
                            cached_tokens=0, counts_toward_quota=False, conversation_id=scope.conversation_id, cost_micro_usd=cost,
                            billed_to=scope.billed_to, pages=pages))
            await db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Could not record page usage for user %s", scope.user_id)


# ---- enforcement -------------------------------------------------------------------------------------------------

def is_exhausted(user: User) -> bool:
    """Super admins are never limited; `token_limit` NULL = unlimited."""
    return user.role != UserRole.SUPER_ADMIN and user.token_limit is not None and user.tokens_used >= user.token_limit


def ensure_quota(user: User) -> None:
    """Raise 429 when `user` (already loaded for this request) has used up the quota."""
    if is_exhausted(user):
        raise QuotaExceededError()


async def _blocked(db: AsyncSession, user: User) -> quota.WindowStatus | bool | None:
    """The reason `user` may not start new work: the legacy token limit (True) or an exhausted dollar window; None = free to go."""
    if is_exhausted(user):
        return True
    return await quota.blocking_window(db, user)


async def enforce_quota(user: User) -> None:
    """Raise 429 when `user` (loaded for this request) is over the legacy token limit or an enforced dollar window.
    Uses its own short session so callers need no `db`. Super admins are never limited."""
    if user.role == UserRole.SUPER_ADMIN:
        return
    async with async_session_factory() as db:
        reason = await _blocked(db, user)
    if reason is True:
        raise QuotaExceededError()
    if reason:
        raise QuotaExceededError(window=reason.name, resets_at=reason.resets_at)


async def pool_status(db: AsyncSession) -> dict:
    """The shared setup pool: budget, what project-upload ingestion has charged to it so far (all time), and what is left."""
    config = await db.get(QuotaConfig, 1, populate_existing=True)
    used = int(await db.scalar(select(func.coalesce(func.sum(LlmUsage.cost_micro_usd), 0)).where(LlmUsage.billed_to == "org_setup")) or 0)
    budget = int(config.setup_pool_micro) if config else 0
    enabled = bool(config and config.setup_pool_enabled)
    return {"enabled": enabled, "enforced": bool(config and config.enforced), "budget": budget, "used": used, "remaining": max(budget - used, 0)}


async def pool_covers_project_uploads() -> bool:
    async with async_session_factory() as db:
        return (await pool_status(db))["enabled"]


async def enforce_upload_quota(user: User, *, project_upload: bool) -> None:
    """Gate for uploads (and retries). Project uploads are charged to the setup pool while it is enabled: they are refused with
    429 `setup_pool_exhausted` when it is used up (only while the quota is enforced), and then do not touch the uploader's own
    quota. Conversation uploads, and project uploads without a pool, use the uploader's dollar quota. Super admins pass."""
    if user.role == UserRole.SUPER_ADMIN:
        return
    if project_upload:
        async with async_session_factory() as db:
            pool = await pool_status(db)
            if pool["enabled"]:
                if pool["enforced"] and pool["remaining"] <= 0:
                    raise QuotaExceededError("setup_pool_exhausted")
                org = await quota.org_cap_block(db) if pool["enforced"] else None
                if org:
                    raise QuotaExceededError(window=org.name, resets_at=org.resets_at)
                return
    await enforce_quota(user)


async def is_blocked(user: User) -> bool:
    """Same check without raising (group chat notice)."""
    try:
        await enforce_quota(user)
    except QuotaExceededError:
        return True
    return False


async def quota_exhausted(user_id: uuid.UUID | None) -> bool:
    """Fresh check for long-running work (between agent steps, in workers). Unknown users and failures count as not exhausted."""
    if user_id is None:
        return False
    try:
        async with async_session_factory() as db:
            user = await db.get(User, user_id, populate_existing=True)
            return user is not None and bool(await _blocked(db, user))
    except Exception:  # noqa: BLE001
        logger.exception("Quota check failed for user %s", user_id)
        return False


async def ensure_quota_by_id(user_id: uuid.UUID) -> None:
    if await quota_exhausted(user_id):
        raise QuotaExceededError()


# ---- admin operations ---------------------------------------------------------------------------------------------

async def _target(db: AsyncSession, actor: User, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.role == UserRole.SUPER_ADMIN:
        raise BadRequestError("A super admin is never limited")
    if user.role == UserRole.ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise ForbiddenError("Only super admins can manage an admin's token limit")
    return user


def _stamp(user: User, actor: User) -> None:
    user.token_limit_set_by, user.token_limit_set_at = actor.id, datetime.now(timezone.utc)


async def set_limit(db: AsyncSession, actor: User, user_id: uuid.UUID, limit: int | None) -> User:
    """`None` removes the limit (unlimited); the counter is left alone."""
    if limit is not None and not (0 < limit <= MAX_LIMIT):
        raise BadRequestError(f"The limit must be between 1 and {MAX_LIMIT}")
    user = await _target(db, actor, user_id)
    user.token_limit = limit
    _stamp(user, actor)
    await db.commit()
    await db.refresh(user)
    logger.info("Token limit of %s set to %s by %s", user.id, limit, actor.id)
    return user


async def extend_limit(db: AsyncSession, actor: User, user_id: uuid.UUID, add: int) -> User:
    """Raise the limit by `add` tokens without touching the usage counter."""
    if not (0 < add <= MAX_LIMIT):
        raise BadRequestError(f"The amount must be between 1 and {MAX_LIMIT}")
    user = await _target(db, actor, user_id)
    if user.token_limit is None:
        raise BadRequestError("This user has no limit to extend")
    user.token_limit = min(user.token_limit + add, MAX_LIMIT)
    _stamp(user, actor)
    await db.commit()
    await db.refresh(user)
    logger.info("Token limit of %s extended by %s by %s", user.id, add, actor.id)
    return user


async def reset_usage(db: AsyncSession, actor: User, user_id: uuid.UUID) -> User:
    """Zero the counter and start a new period. The usage rows stay for reporting."""
    user = await _target(db, actor, user_id)
    user.tokens_used = 0
    user.token_period_start = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    logger.info("Token usage of %s reset by %s", user.id, actor.id)
    return user


def micro_to_usd(micro) -> float:
    return round(int(micro or 0) / 1_000_000, 6)


async def cost_summary(db: AsyncSession, days: int = 30) -> dict:
    """Org-wide cost over the last `days` days (monitoring): per purpose, model and user."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cost = func.coalesce(func.sum(LlmUsage.cost_micro_usd), 0)
    base = LlmUsage.created_at >= since

    async def group(*cols):
        return (await db.execute(select(*cols, func.sum(LlmUsage.prompt_tokens), func.sum(LlmUsage.completion_tokens), func.count(), cost)
                                 .where(base).group_by(*cols).order_by(cost.desc()))).all()

    def rows(data, keys):
        return [{**dict(zip(keys, r[:len(keys)])), "prompt_tokens": int(r[len(keys)] or 0), "completion_tokens": int(r[len(keys) + 1] or 0),
                 "calls": r[len(keys) + 2], "cost_usd": micro_to_usd(r[len(keys) + 3])} for r in data]

    by_user = (await db.execute(
        select(User.id, User.email, cost, func.count()).join(User, User.id == LlmUsage.user_id).where(base)
        .group_by(User.id, User.email).order_by(cost.desc())
    )).all()
    total = await db.scalar(select(cost).where(base))
    return {
        "days": days, "total_usd": micro_to_usd(total),
        "by_purpose": rows(await group(LlmUsage.purpose), ["purpose"]),
        "by_model": rows(await group(LlmUsage.model), ["model"]),
        "by_user": [{"user_id": str(uid), "email": email, "cost_usd": micro_to_usd(c), "calls": n} for uid, email, c, n in by_user],
    }


async def list_prices(db: AsyncSession) -> list[ModelPrice]:
    return list((await db.execute(select(ModelPrice).order_by(ModelPrice.model))).scalars().all())


async def set_price(db: AsyncSession, actor: User, model: str, input_per_m: float, output_per_m: float, per_page_usd: float | None = None) -> ModelPrice:
    from decimal import Decimal

    model = model.strip()
    if not model or len(model) > 200:
        raise BadRequestError("Invalid model name")
    if not (0 <= input_per_m <= 10_000 and 0 <= output_per_m <= 10_000):
        raise BadRequestError("Prices are USD per million tokens, between 0 and 10000")
    if per_page_usd is not None and not (0 <= per_page_usd <= 100):
        raise BadRequestError("per_page_usd is USD per page, between 0 and 100")
    page = None if per_page_usd is None else Decimal(str(per_page_usd))
    row = await db.get(ModelPrice, model)
    if row is None:
        row = ModelPrice(model=model, input_per_m=Decimal(str(input_per_m)), output_per_m=Decimal(str(output_per_m)), per_page_usd=page)
        db.add(row)
    else:
        row.input_per_m, row.output_per_m, row.per_page_usd = Decimal(str(input_per_m)), Decimal(str(output_per_m)), page
    row.updated_by, row.updated_at = actor.id, datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    pricing.invalidate_cache()
    logger.info("Price of %s set to %s/%s by %s", model, input_per_m, output_per_m, actor.id)
    return row


async def delete_price(db: AsyncSession, model: str) -> None:
    row = await db.get(ModelPrice, model)
    if row is None:
        raise NotFoundError("Price not found")
    await db.delete(row)
    await db.commit()
    pricing.invalidate_cache()


async def usage_report(db: AsyncSession, user: User, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    total = func.coalesce(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens), 0)
    cost = func.coalesce(func.sum(LlmUsage.cost_micro_usd), 0)
    by_purpose = (await db.execute(
        select(LlmUsage.purpose, func.sum(LlmUsage.prompt_tokens), func.sum(LlmUsage.completion_tokens), func.count(), LlmUsage.counts_toward_quota, cost)
        .where(LlmUsage.user_id == user.id, LlmUsage.created_at >= user.token_period_start)
        .group_by(LlmUsage.purpose, LlmUsage.counts_toward_quota).order_by(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens).desc())
    )).all()
    by_model = (await db.execute(
        select(LlmUsage.model, func.sum(LlmUsage.prompt_tokens), func.sum(LlmUsage.completion_tokens), func.count(), cost)
        .where(LlmUsage.user_id == user.id, LlmUsage.created_at >= user.token_period_start)
        .group_by(LlmUsage.model).order_by(cost.desc())
    )).all()
    day = func.date_trunc("day", LlmUsage.created_at)
    daily = (await db.execute(
        select(day, total).where(LlmUsage.user_id == user.id, LlmUsage.created_at >= since, LlmUsage.counts_toward_quota.is_(True)).group_by(day).order_by(day)
    )).all()
    return {
        "limit": user.token_limit, "used": user.tokens_used, "period_start": user.token_period_start,
        "by_purpose": [{"purpose": p, "prompt_tokens": int(pt or 0), "completion_tokens": int(ct or 0), "calls": n, "counts_toward_quota": counted}
                       | {"cost_usd": micro_to_usd(c)} for p, pt, ct, n, counted, c in by_purpose],
        "by_model": [{"model": m, "prompt_tokens": int(pt or 0), "completion_tokens": int(ct or 0), "calls": n, "cost_usd": micro_to_usd(c)}
                     for m, pt, ct, n, c in by_model],
        "cost_usd": micro_to_usd(sum(int(row[5] or 0) for row in by_purpose)),
        "daily": [{"date": d.date().isoformat(), "tokens": int(t)} for d, t in daily],
    }


# ---- dollar quota administration (super admins only; the router enforces that) -------------------------------------------

def _usd_to_micro(value: float | None, name: str) -> int | None:
    if value is None:
        return None
    micro = round(value * 1_000_000)
    if not (0 < micro <= quota.MAX_MICRO):
        raise BadRequestError(f"{name} must be a positive amount in USD")
    return micro


async def quota_overview(db: AsyncSession) -> dict:
    enforced, plans = await quota.load_config(db)
    start, nxt = quota.month_bounds(datetime.now(timezone.utc))
    pool = await pool_status(db)
    config = await db.get(QuotaConfig, 1)
    cap = config.org_monthly_cap_micro if config else None
    org_used = await quota.org_month_used(db)
    return {
        "enforced": enforced,
        "setup_pool": {"enabled": pool["enabled"], "budget_usd": pool["budget"] / 1e6, "used_usd": pool["used"] / 1e6, "remaining_usd": pool["remaining"] / 1e6},
        "org": {"monthly_cap_usd": None if cap is None else cap / 1e6, "month_used_usd": org_used / 1e6,
                "percent": None if not cap else round(100 * org_used / cap, 1)},
        "plans": {role: {"five_hour_usd": p.five_hour / 1e6, "weekly_usd": p.weekly / 1e6, "monthly_usd": p.monthly / 1e6} for role, p in plans.items()},
        "month": {"start": start, "next_start": nxt},
    }


async def set_enforced(db: AsyncSession, actor: User, enforced: bool) -> dict:
    config = await db.get(QuotaConfig, 1)
    if config is None:
        config = QuotaConfig(id=1)
        db.add(config)
    config.enforced, config.updated_by, config.updated_at = enforced, actor.id, datetime.now(timezone.utc)
    await db.commit()
    quota.invalidate_cache()
    logger.warning("Dollar quota enforcement %s by %s", "ENABLED" if enforced else "disabled", actor.id)
    return await quota_overview(db)


async def set_plan(db: AsyncSession, actor: User, role: str, five_hour_usd: float, weekly_usd: float, monthly_usd: float) -> dict:
    if role not in ("user", "admin"):
        raise BadRequestError("Plans exist for the roles user and admin")
    five, week, month = (_usd_to_micro(v, n) for v, n in ((five_hour_usd, "five_hour_usd"), (weekly_usd, "weekly_usd"), (monthly_usd, "monthly_usd")))
    if not (five <= week <= month):
        raise BadRequestError("Caps must not decrease: 5 hours <= week <= month")
    plan = await db.get(QuotaPlan, role)
    if plan is None:
        plan = QuotaPlan(role=role, five_hour_micro=five, weekly_micro=week, monthly_micro=month)
        db.add(plan)
    plan.five_hour_micro, plan.weekly_micro, plan.monthly_micro = five, week, month
    plan.updated_by, plan.updated_at = actor.id, datetime.now(timezone.utc)
    await db.commit()
    quota.invalidate_cache()
    logger.info("Quota plan of %s set to %s/%s/%s micro-USD by %s", role, five, week, month, actor.id)
    return await quota_overview(db)


async def set_user_quota(db: AsyncSession, actor: User, user_id: uuid.UUID, five_hour_usd: float | None, weekly_usd: float | None,
                         monthly_usd: float | None, unlimited: bool) -> User:
    """Per-user exception. A null cap follows the role's plan; `unlimited` removes every cap. Never for a super admin."""
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.role == UserRole.SUPER_ADMIN:
        raise BadRequestError("A super admin is never limited")
    user.quota_five_hour_override = _usd_to_micro(five_hour_usd, "five_hour_usd")
    user.quota_weekly_override = _usd_to_micro(weekly_usd, "weekly_usd")
    user.quota_monthly_override = _usd_to_micro(monthly_usd, "monthly_usd")
    user.quota_unlimited = unlimited
    await db.commit()
    await db.refresh(user)
    logger.info("Quota override of %s set by %s (unlimited=%s)", user.id, actor.id, unlimited)
    return user


async def set_setup_pool(db: AsyncSession, actor: User, enabled: bool | None, budget_usd: float | None) -> dict:
    """Turn the pool on/off and/or set its total budget (raise it to top up: used is all-time)."""
    config = await db.get(QuotaConfig, 1)
    if config is None:
        config = QuotaConfig(id=1)
        db.add(config)
    if budget_usd is not None:
        config.setup_pool_micro = _usd_to_micro(budget_usd, "budget_usd")
    if enabled is not None:
        config.setup_pool_enabled = enabled
    config.updated_by, config.updated_at = actor.id, datetime.now(timezone.utc)
    await db.commit()
    quota.invalidate_cache()
    logger.warning("Setup pool set (enabled=%s, budget=%s USD) by %s", enabled, budget_usd, actor.id)
    return await quota_overview(db)


async def set_org_cap(db: AsyncSession, actor: User, monthly_cap_usd: float | None) -> dict:
    """Whole-organisation cap per Jalali month; null removes it. Only applies while the quota is enforced."""
    config = await db.get(QuotaConfig, 1)
    if config is None:
        config = QuotaConfig(id=1)
        db.add(config)
    config.org_monthly_cap_micro = _usd_to_micro(monthly_cap_usd, "monthly_cap_usd")
    config.updated_by, config.updated_at = actor.id, datetime.now(timezone.utc)
    await db.commit()
    quota.invalidate_cache()
    logger.warning("Organisation monthly cap set to %s USD by %s", monthly_cap_usd, actor.id)
    return await quota_overview(db)
