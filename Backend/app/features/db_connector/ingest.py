"""CLI entrypoint to ingest schema hints from sql/rahkaran/hints/out/hints.jsonl into PostgreSQL."""

import asyncio
import logging

from app.core.database import async_session_factory
from app.features.db_connector.hints import ingest_hints

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Starting schema hints ingestion...")
    async with async_session_factory() as session:
        stats = await ingest_hints(session)
        logger.info("Ingestion completed: %s", stats)


if __name__ == "__main__":
    asyncio.run(main())

