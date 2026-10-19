"""Shared setup for the retrieval evaluation tools. Importing this module points the app at the scratch database,
so it must be imported before any `app.*` module."""

import json
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(os.environ.get("EVAL_DIR", BACKEND / "eval")) / "Sohrab"
WORKDIR = Path(os.environ.get("EVAL_WORKDIR", "/tmp/orbit_retrieval_eval"))
DB_NAME = os.environ.get("EVAL_DB", "eval_scratch")
PG_BASE = os.environ.get("EVAL_PG_BASE")  # e.g. postgresql+asyncpg://postgres:pw@host:5432   (no database name)
if not PG_BASE:
    sys.exit("Set EVAL_PG_BASE=postgresql+asyncpg://user:password@host:port (the scratch database is created/overwritten: " + DB_NAME + ")")
os.environ["DATABASE_URL"] = f"{PG_BASE}/{DB_NAME}"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).parent))
WORKDIR.mkdir(parents=True, exist_ok=True)

import logging  # noqa: E402

logging.disable(logging.CRITICAL)

from app.core.text_normalization import normalize  # noqa: E402


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", normalize(text)).strip()


def relevant(must: list[str], content: str) -> bool:
    haystack = norm(content)
    return all(norm(item) in haystack for item in must)


def project_id():
    import uuid

    return uuid.UUID(json.loads((WORKDIR / "project.json").read_text())["project_id"])
