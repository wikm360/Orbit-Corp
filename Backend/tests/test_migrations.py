import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect, text

from app.core.database import Base, engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


async def test_alembic_upgrade_head_builds_the_orm_schema():
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=os.environ,
        check=True,
        capture_output=True,
    )

    def _schema(sync_conn) -> dict[str, set[str]]:
        inspector = inspect(sync_conn)
        return {t: {c["name"] for c in inspector.get_columns(t)} for t in inspector.get_table_names()}

    async with engine.connect() as conn:
        actual = await conn.run_sync(_schema)

    expected = {name: {c.name for c in table.columns} for name, table in Base.metadata.tables.items()}
    actual.pop("alembic_version", None)
    assert actual == expected
