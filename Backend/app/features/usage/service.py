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
from app.features.usage.models import LlmUsage

logger = logging.getLogger(__name__)

MAX_LIMIT = 10**12
# Purposes that are recorded but never limited: stopping them half-way would leave an uploaded document half-processed.
UNMETERED_PURPOSES = {"ocr", "embedding"}


@dataclass(frozen=True)
class UsageScope:
    user_id: uuid.UUID
    purpose: str
    conversation_id: uuid.UUID | None = None


_scope: contextvars.ContextVar[UsageScope | None] = contextvars.ContextVar("llm_usage_scope", default=None)


def current_user_id() -> uuid.UUID | None:
    scope = _scope.get()
    return scope.user_id if scope else None


@contextlib.contextmanager
def usage_scope(user_id: uuid.UUID | None, purpose: str, conversation_id: uuid.UUID | None = None):
    """Attribute every model call inside the block to `user_id` (no-op when there is no user)."""
    token = _scope.set(UsageScope(user_id, purpose, conversation_id) if user_id is not None else None)
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
            db.add(LlmUsage(user_id=scope.user_id, purpose=purpose, model=model[:200], prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens, cached_tokens=cached_tokens, counts_toward_quota=counted,
                            conversation_id=scope.conversation_id))
            if counted:
                await db.execute(update(User).where(User.id == scope.user_id).values(tokens_used=User.tokens_used + prompt_tokens + completion_tokens))
            await db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Could not record LLM usage for user %s", scope.user_id)


# ---- enforcement -------------------------------------------------------------------------------------------------

def is_exhausted(user: User) -> bool:
    """Super admins are never limited; `token_limit` NULL = unlimited."""
    return user.role != UserRole.SUPER_ADMIN and user.token_limit is not None and user.tokens_used >= user.token_limit


def ensure_quota(user: User) -> None:
    """Raise 429 when `user` (already loaded for this request) has used up the quota."""
    if is_exhausted(user):
        raise QuotaExceededError()


async def quota_exhausted(user_id: uuid.UUID | None) -> bool:
    """Fresh check for long-running work (between agent steps, in workers). Unknown users and failures count as not exhausted."""
    if user_id is None:
        return False
    try:
        async with async_session_factory() as db:
            user = await db.get(User, user_id, populate_existing=True)
            return user is not None and is_exhausted(user)
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


async def usage_report(db: AsyncSession, user: User, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    total = func.coalesce(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens), 0)
    by_purpose = (await db.execute(
        select(LlmUsage.purpose, func.sum(LlmUsage.prompt_tokens), func.sum(LlmUsage.completion_tokens), func.count(), LlmUsage.counts_toward_quota)
        .where(LlmUsage.user_id == user.id, LlmUsage.created_at >= user.token_period_start)
        .group_by(LlmUsage.purpose, LlmUsage.counts_toward_quota).order_by(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens).desc())
    )).all()
    day = func.date_trunc("day", LlmUsage.created_at)
    daily = (await db.execute(
        select(day, total).where(LlmUsage.user_id == user.id, LlmUsage.created_at >= since, LlmUsage.counts_toward_quota.is_(True)).group_by(day).order_by(day)
    )).all()
    return {
        "limit": user.token_limit, "used": user.tokens_used, "period_start": user.token_period_start,
        "by_purpose": [{"purpose": p, "prompt_tokens": int(pt or 0), "completion_tokens": int(ct or 0), "calls": n, "counts_toward_quota": counted}
                       for p, pt, ct, n, counted in by_purpose],
        "daily": [{"date": d.date().isoformat(), "tokens": int(t)} for d, t in daily],
    }
