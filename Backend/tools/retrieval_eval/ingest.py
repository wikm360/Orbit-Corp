"""Create the scratch database and ingest corpus.FILES with the REAL pipeline (real embeddings, real vision OCR).

    EVAL_PG_BASE=postgresql+asyncpg://postgres:pw@127.0.0.1:5432 python tools/retrieval_eval/ingest.py

Files are copied into the work dir first: the pipeline writes `.reconstructed.*` next to the stored file and must never
touch the originals. WARNING: page text and page images go to the LLM / embedding provider configured in .env.
"""

import asyncio
import json
import shutil
import time
import uuid

import common  # noqa: F401  (sets DATABASE_URL, must come first)
from corpus import FILES
from sqlalchemy import text

from app.core import model_registry  # noqa: F401
from app.core.database import Base, async_session_factory, engine
from app.features.access_control.models import Team
from app.features.documents.ingestion.pipeline import run_ingestion_pipeline
from app.features.documents.models import Document, DocumentStatus
from app.features.projects.models import Project


async def main() -> None:
    uploads = common.WORKDIR / "uploads"
    uploads.mkdir(exist_ok=True)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION vector"))
        await conn.execute(text("CREATE EXTENSION pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        team = Team(name="eval")
        db.add(team)
        await db.flush()
        project = Project(team_id=team.id, name="eval")
        db.add(project)
        await db.flush()
        documents = []
        for relative in FILES:
            source = common.EVAL_DIR / relative
            target = uploads / f"{uuid.uuid4()}{source.suffix.lower()}"
            shutil.copy(source, target)
            document = Document(
                filename=source.name, file_path=str(target), content_type="application/octet-stream",
                status=DocumentStatus.PROCESSING, content_hash=uuid.uuid4().hex, project_id=project.id,
            )
            db.add(document)
            documents.append(document)
        await db.commit()
        for document in documents:
            await db.refresh(document)
        (common.WORKDIR / "project.json").write_text(json.dumps({"project_id": str(project.id)}))
        todo = [(d.id, d.file_path, d.filename) for d in documents]

    semaphore = asyncio.Semaphore(3)

    async def one(document_id, path, name):
        async with semaphore:
            started = time.time()
            try:
                await run_ingestion_pipeline(document_id, path)
                print(f"OK  {time.time() - started:6.0f}s {name}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"ERR {time.time() - started:6.0f}s {name}: {str(exc)[:120]}", flush=True)

    await asyncio.gather(*[one(*item) for item in todo])
    await engine.dispose()


asyncio.run(main())
