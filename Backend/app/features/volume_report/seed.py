"""Idempotent seeding of catalog, lexicon and default conversion parameters (only into empty tables, so edits made
through the settings API are never overwritten)."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.volume_report.models import (
    Conversion, Dimension, Item, LexiconEntry, LexiconKind, Setting,
)
from app.features.volume_report.seed_data import CONVERSIONS_SEED, ITEMS_SEED, LEXICON_SEED, ROLLUPS_SEED


async def ensure_seeded(db: AsyncSession) -> None:
    changed = False
    # Items/tokens that a newer release added to the seed are inserted into an already-seeded database too (additive only:
    # existing rows -- possibly edited in the settings API -- are never touched, and items cannot be deleted, only deactivated).
    existing_keys = set((await db.execute(select(Item.key))).scalars())
    next_order = int(await db.scalar(select(func.coalesce(func.max(Item.sort_order), 0))) or 0)
    for order, (key, title, dim, unit, decimals, mining_only, desc) in enumerate(ITEMS_SEED, start=1):
        if key in existing_keys:
            continue
        rollup = ROLLUPS_SEED.get(key)
        next_order = order if not existing_keys else next_order + 1
        db.add(Item(
            key=key, title_fa=title, description_fa=desc, dimension=Dimension(dim), output_unit=unit, decimals=decimals,
            sort_order=next_order, is_rollup=rollup is not None, rollup_of=rollup or [], mining_only=mining_only,
        ))
        changed = True
    existing_tokens = set((await db.execute(select(LexiconEntry.token))).scalars())
    for token, kind, phrases in LEXICON_SEED:
        if token not in existing_tokens:
            db.add(LexiconEntry(token=token, kind=LexiconKind(kind), phrases=phrases))
            changed = True
    if changed:
        await db.flush()
    if not await db.scalar(select(func.count()).select_from(Conversion)):
        items = {i.key: i.id for i in (await db.execute(select(Item))).scalars()}
        for key, item_key, value, unit, note in CONVERSIONS_SEED:
            db.add(Conversion(key=key, item_id=items.get(item_key), value=Decimal(value), unit=unit, note=note))
        changed = True
    if await db.get(Setting, "catalog_version") is None:
        db.add(Setting(key="catalog_version", value=1))
        changed = True
    if changed:
        await db.commit()


async def bump_catalog_version(db: AsyncSession) -> int:
    """Call (without committing) whenever catalog/lexicon/conversions/decisions change; reports record the version they used."""
    row = await db.get(Setting, "catalog_version")
    if row is None:
        row = Setting(key="catalog_version", value=1)
        db.add(row)
    row.value = int(row.value) + 1
    return int(row.value)


async def current_catalog_version(db: AsyncSession) -> int:
    row = await db.get(Setting, "catalog_version")
    return int(row.value) if row else 1
