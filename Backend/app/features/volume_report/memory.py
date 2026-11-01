"""Decision memory beyond the exact match: embeddings, similar-decision search (for the agent) and revocation.

Similar decisions are examples only -- they are never applied automatically. Only the exact `key_hash` match is."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.features.retrieval.service import reciprocal_rank_fusion
from app.features.volume_report.extraction.normalize import normalize_text
from app.features.volume_report.models import Decision, Item, SiteKind
from app.features.volume_report.seed import bump_catalog_version
from app.providers.embedding_provider import get_embedding_provider

logger = logging.getLogger(__name__)

_CANDIDATES = 20


async def embed_text(text: str) -> list[float] | None:
    """None on any provider failure: the decision is still stored and found by trigram search (like schema hints)."""
    try:
        [vector] = await get_embedding_provider().embed([text])
        return vector
    except Exception as exc:
        logger.warning("Decision embedding failed (%s); stored without a vector", exc)
        return None


async def ensure_embedding(decision: Decision) -> None:
    if decision.embedding is None:
        decision.embedding = await embed_text(decision.description_norm)


async def search_similar(
    db: AsyncSession, text: str, unit: str | None = None, site_kind: str | None = None, limit: int = 5
) -> list[dict]:
    """Vector (cosine) + trigram rankings fused with RRF over active decisions."""
    query = normalize_text(text)
    if not query:
        return []
    base = select(Decision).where(Decision.revoked_at.is_(None))
    if unit:
        base = base.where(Decision.unit_norm == unit)
    if site_kind:
        base = base.where(Decision.site_kind == SiteKind(site_kind))

    rankings: list[list[str]] = []
    trigram = func.similarity(Decision.description_norm, query)
    rows = (await db.execute(base.where(Decision.description_norm.op("%")(query)).order_by(trigram.desc()).limit(_CANDIDATES))).scalars().all()
    rankings.append([str(d.id) for d in rows])
    by_id = {str(d.id): d for d in rows}

    vector = await embed_text(query)
    if vector and any(vector):  # a zero vector has no cosine distance
        distance = Decision.embedding.cosine_distance(vector)
        vrows = (await db.execute(
            base.where(Decision.embedding.is_not(None)).order_by(distance).limit(_CANDIDATES)
        )).scalars().all()
        rankings.append([str(d.id) for d in vrows])
        by_id.update({str(d.id): d for d in vrows})

    fused = reciprocal_rank_fusion([r for r in rankings if r])
    items = {i.id: i.key for i in (await db.execute(select(Item))).scalars()}
    top = sorted(fused, key=fused.get, reverse=True)[:limit]
    return [
        {"decision_id": by_id[i].id, "description": by_id[i].description_norm, "unit": by_id[i].unit_norm,
         "site_kind": by_id[i].site_kind.value, "disposition": by_id[i].disposition.value,
         "item_key": items.get(by_id[i].item_id), "role": by_id[i].role.value,
         "exclude_reason": by_id[i].exclude_reason.value if by_id[i].exclude_reason else None, "score": round(fused[i], 4)}
        for i in top
    ]


async def list_decisions(db: AsyncSession, q: str | None, include_revoked: bool, limit: int, offset: int) -> list[dict]:
    query = select(Decision).order_by(Decision.created_at.desc()).limit(limit).offset(offset)
    if not include_revoked:
        query = query.where(Decision.revoked_at.is_(None))
    if q:
        query = query.where(Decision.description_norm.contains(normalize_text(q)))
    items = {i.id: i.key for i in (await db.execute(select(Item))).scalars()}
    return [
        {"id": d.id, "description": d.description_norm, "unit": d.unit_norm, "site_kind": d.site_kind.value,
         "disposition": d.disposition.value, "item_key": items.get(d.item_id), "role": d.role.value,
         "exclude_reason": d.exclude_reason.value if d.exclude_reason else None, "hits": d.hits, "source": d.source.value,
         "confirmed_at": d.confirmed_at, "revoked_at": d.revoked_at, "has_embedding": d.embedding is not None}
        for d in (await db.execute(query)).scalars()
    ]


async def revoke_decision(db: AsyncSession, decision_id: uuid.UUID, user_id: uuid.UUID) -> Decision:
    """Reports already computed keep their classifications; the next run no longer finds the decision."""
    decision = await db.get(Decision, decision_id)
    if decision is None:
        raise NotFoundError("Decision not found")
    if decision.revoked_at is None:
        decision.revoked_at, decision.revoked_by = datetime.now(timezone.utc), user_id
        decision.catalog_version = await bump_catalog_version(db)
        await db.commit()
    return decision
