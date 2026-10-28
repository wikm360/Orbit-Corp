"""The folder path of a document, kept on each of its chunks.

`chunk_metadata["path"]` (e.g. "امور مربوط به تعدیل/تعدیل شماره2/تائید کارفرما.pdf") is shown with search results, and the
normalized path is prepended to `search_text`, so full-text and trigram search also match folder and file names - a question
that names a folder ("تعدیل ۲ ... تایید کارفرما") finds the file even when its body never says so. Embeddings are untouched
(no re-embedding when a path changes).

A move/rename/copy changes the path of every document below the item, so those operations call `refresh_chunk_paths`."""

import uuid
from collections.abc import Iterable

from sqlalchemy import bindparam, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text_normalization import normalize
from app.features.documents.folder_service import load_folders, path_of
from app.features.documents.models import Document, DocumentChunk, DocumentFolder

PATH_KEY = "path"


def document_path(folders: dict[uuid.UUID, DocumentFolder], document: Document) -> str:
    """"folder/subfolder/file name" ("file name" alone for a document at the root or outside a project)."""
    return "/".join([*(f.name for f in path_of(folders, document.folder_id)), document.filename])


def chunk_search_text(path: str | None, content: str) -> str:
    return f"{normalize(path)} {normalize(content)}" if path else normalize(content)


async def path_for_new_chunks(db: AsyncSession, document_id: uuid.UUID) -> str | None:
    """The path to stamp on chunks about to be inserted for `document_id` (None if the document is gone)."""
    document = await db.get(Document, document_id)
    if document is None:
        return None
    folders = await load_folders(db, document.project_id) if document.project_id is not None else {}
    return document_path(folders, document)


async def refresh_chunk_paths(db: AsyncSession, project_id: uuid.UUID, document_ids: Iterable[uuid.UUID] | None = None) -> int:
    """Rewrites path metadata + `search_text` on chunks whose stored path is stale. `document_ids=None` = the whole project.
    Returns the number of chunks updated. Commits."""
    folders = await load_folders(db, project_id)
    query = select(Document).where(Document.project_id == project_id)
    if document_ids is not None:
        ids = list(document_ids)
        if not ids:
            return 0
        query = query.where(Document.id.in_(ids))

    statement = (
        update(DocumentChunk.__table__)  # Core, not ORM: an ORM executemany update is a by-primary-key bulk update
        .where(DocumentChunk.__table__.c.id == bindparam("b_id"))
        .values(chunk_metadata=bindparam("b_meta"), search_text=bindparam("b_search"))
    )
    updated = 0
    for document in (await db.execute(query)).scalars().all():
        path = document_path(folders, document)
        rows = (
            await db.execute(
                select(DocumentChunk.id, DocumentChunk.content, DocumentChunk.chunk_metadata).where(
                    DocumentChunk.document_id == document.id
                )
            )
        ).all()
        batch = [
            {"b_id": row.id, "b_meta": {**(row.chunk_metadata or {}), PATH_KEY: path}, "b_search": chunk_search_text(path, row.content)}
            for row in rows
            if (row.chunk_metadata or {}).get(PATH_KEY) != path
        ]
        if batch:
            await db.execute(statement, batch)
            updated += len(batch)
    await db.commit()
    return updated
