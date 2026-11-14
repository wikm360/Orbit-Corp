"""Model price table -> cost of one call, in micro-USD (tokens x USD per million tokens = micro-USD exactly).

Prices live in `model_prices` (super-admin editable) and are cached briefly in memory. A model that is not in the table is
charged at the most expensive row rather than at zero, so a renamed model on the gateway never makes usage look free."""

import logging
import math
import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.usage.models import ModelPrice

logger = logging.getLogger(__name__)

_TTL_SECONDS = 60.0
_cache: tuple[float, dict[str, tuple[Decimal, Decimal]]] | None = None
_page_prices: dict[str, Decimal] = {}
_warned: set[str] = set()


def _key(model: str) -> str:
    return model.strip().lower()


def invalidate_cache() -> None:
    global _cache
    _cache = None


async def load_prices(db: AsyncSession) -> dict[str, tuple[Decimal, Decimal]]:
    global _cache
    now = time.monotonic()
    if _cache is not None and now - _cache[0] < _TTL_SECONDS:
        return _cache[1]
    rows = (await db.execute(select(ModelPrice))).scalars().all()
    prices = {_key(r.model): (Decimal(r.input_per_m), Decimal(r.output_per_m)) for r in rows}
    _page_prices.clear()
    _page_prices.update({_key(r.model): Decimal(r.per_page_usd) for r in rows if r.per_page_usd is not None})
    _cache = (now, prices)
    return prices


def _lookup(prices: dict[str, tuple[Decimal, Decimal]], model: str) -> tuple[Decimal, Decimal] | None:
    key = _key(model)
    if key in prices:
        return prices[key]
    if "/" in key and key.rsplit("/", 1)[1] in prices:  # gateways sometimes prefix the vendor ("google/gemini-...")
        return prices[key.rsplit("/", 1)[1]]
    return None


def cost_micro_usd(prices: dict[str, tuple[Decimal, Decimal]], model: str, prompt_tokens: int, completion_tokens: int) -> int:
    """Rounded up, so many tiny calls are never charged as free. Empty table -> 0 (logged)."""
    price = _lookup(prices, model)
    if price is None:
        if not prices:
            logger.warning("model_prices is empty: usage cost recorded as 0")
            return 0
        price = (max(p[0] for p in prices.values()), max(p[1] for p in prices.values()))
        if model not in _warned:
            _warned.add(model)
            logger.warning("No price for model %r: charged at the most expensive known price", model)
    return math.ceil(prompt_tokens * price[0] + completion_tokens * price[1])


async def page_cost_micro(db: AsyncSession, model: str, pages: int) -> int:
    """Per-page priced call (Mistral OCR). No page price set -> 0 with a one-time warning (never guessed)."""
    await load_prices(db)
    price = _page_prices.get(_key(model))
    if price is None:
        if model not in _warned:
            _warned.add(model)
            logger.warning("No per-page price for %r: its cost is recorded as 0 (set per_page_usd in /admin/model-prices)", model)
        return 0
    return math.ceil(pages * price * 1_000_000)
