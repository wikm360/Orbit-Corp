"""Stamps the folder path on chunks indexed before paths existed (no OCR, no embedding calls - only metadata and
`search_text` are rewritten). Idempotent; safe to re-run. Run once after deploying the path-aware search:

    python -m app.features.documents.backfill_chunk_paths [--project <uuid>]
"""

import argparse
import asyncio
import uuid

from sqlalchemy import select

from app.core import model_registry  # noqa: F401 - registers all models
from app.core.database import async_session_factory
from app.features.documents.chunk_paths import refresh_chunk_paths
from app.features.projects.models import Project


async def main(only_project: uuid.UUID | None) -> None:
    async with async_session_factory() as db:
        query = select(Project.id, Project.name)
        if only_project is not None:
            query = query.where(Project.id == only_project)
        total = 0
        for project_id, name in (await db.execute(query)).all():
            updated = await refresh_chunk_paths(db, project_id)
            total += updated
            print(f"{name}: {updated} chunks updated")
        print(f"done: {total} chunks updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=uuid.UUID, default=None, help="only this project")
    asyncio.run(main(parser.parse_args().project))
