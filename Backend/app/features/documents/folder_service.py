"""A project's folder tree: lookup, naming rules, listing and search.

The tree is small (hundreds of folders at most), so it is loaded once per request as an id -> row map and walked in
Python (paths, descendants, cycle checks) instead of with recursive SQL. Folders only organise; they never affect access.
"""
import re
import uuid
from collections import defaultdict
from pathlib import PurePosixPath

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.features.documents.models import ArchiveImport, Document, DocumentFolder, DocumentStatus

MAX_FOLDER_NAME_LENGTH = 255
MAX_DOCUMENT_NAME_LENGTH = 500

_INVALID_NAME_CHARS = re.compile(r"[/\\\x00-\x1f]")


def same_or_null(column, value):
    """`column == value`, or `IS NULL` when value is None (a bare `== None` is easy to get wrong; `IS <uuid>` is invalid)."""
    return column.is_(None) if value is None else column == value


def clean_name(raw: str, *, max_length: int) -> str:
    """A single path segment: stripped, no separators/control characters, not `.`/`..`."""
    name = (raw or "").strip()
    if not name or name in (".", ".."):
        raise BadRequestError("Name must not be empty")
    if _INVALID_NAME_CHARS.search(name):
        raise BadRequestError("Name must not contain '/', '\\' or control characters")
    if len(name) > max_length:
        raise BadRequestError(f"Name is longer than {max_length} characters")
    return name


def split_relative_path(raw: str) -> list[str]:
    """Segments of an uploaded file name that may carry a relative path (a browser folder upload sends
    `dir/sub/file.pdf`). Empty, `.` and `..` segments are dropped, so a path can never climb out of its folder."""
    parts = [p.strip() for p in re.split(r"[/\\]+", raw or "")]
    return [p for p in parts if p and p not in (".", "..") and not _INVALID_NAME_CHARS.search(p)]


def unique_name(name: str, taken_lower: set[str]) -> str:
    """`name` itself, or `stem (n).ext` for the first free n (Explorer/Finder style)."""
    if name.lower() not in taken_lower:
        return name
    path = PurePosixPath(name)
    stem, suffix = (path.stem, path.suffix) if path.suffix and path.stem else (name, "")
    n = 1
    while f"{stem} ({n}){suffix}".lower() in taken_lower:
        n += 1
    return f"{stem} ({n}){suffix}"


async def get_folder(db: AsyncSession, project_id: uuid.UUID, folder_id: uuid.UUID) -> DocumentFolder:
    """The folder, only if it belongs to `project_id` (another project's folder is reported as not found)."""
    folder = await db.get(DocumentFolder, folder_id)
    if folder is None or folder.project_id != project_id:
        raise NotFoundError("Folder not found")
    return folder


async def load_folders(db: AsyncSession, project_id: uuid.UUID) -> dict[uuid.UUID, DocumentFolder]:
    result = await db.execute(select(DocumentFolder).where(DocumentFolder.project_id == project_id))
    return {f.id: f for f in result.scalars().all()}


def path_of(folders: dict[uuid.UUID, DocumentFolder], folder_id: uuid.UUID | None) -> list[DocumentFolder]:
    """Root-first chain of folders leading to `folder_id` (empty for the project root)."""
    chain: list[DocumentFolder] = []
    seen: set[uuid.UUID] = set()
    while folder_id is not None and folder_id in folders and folder_id not in seen:
        seen.add(folder_id)
        chain.append(folders[folder_id])
        folder_id = folders[folder_id].parent_id
    return list(reversed(chain))


def subtree_ids(folders: dict[uuid.UUID, DocumentFolder], root_ids: set[uuid.UUID]) -> set[uuid.UUID]:
    """`root_ids` plus every folder below them."""
    children: dict[uuid.UUID | None, list[uuid.UUID]] = defaultdict(list)
    for folder in folders.values():
        children[folder.parent_id].append(folder.id)
    found: set[uuid.UUID] = set()
    stack = list(root_ids)
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(children.get(current, []))
    return found


async def sibling_names(
    db: AsyncSession, project_id: uuid.UUID, parent_id: uuid.UUID | None
) -> tuple[set[str], set[str]]:
    """Lower-cased names of the folders and of the documents directly inside `parent_id`."""
    folder_rows = await db.execute(
        select(func.lower(DocumentFolder.name)).where(
            DocumentFolder.project_id == project_id, same_or_null(DocumentFolder.parent_id, parent_id)
        )
    )
    document_rows = await db.execute(
        select(func.lower(Document.filename)).where(
            Document.project_id == project_id, same_or_null(Document.folder_id, parent_id)
        )
    )
    return set(folder_rows.scalars().all()), set(document_rows.scalars().all())


async def create_folder(
    db: AsyncSession,
    project_id: uuid.UUID,
    name: str,
    parent_id: uuid.UUID | None,
    created_by: uuid.UUID | None,
) -> DocumentFolder:
    name = clean_name(name, max_length=MAX_FOLDER_NAME_LENGTH)
    if parent_id is not None:
        await get_folder(db, project_id, parent_id)
    folder = DocumentFolder(project_id=project_id, parent_id=parent_id, name=name, created_by=created_by)
    db.add(folder)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(f"A folder named '{name}' already exists here") from None
    await db.refresh(folder)
    return folder


async def ensure_folder_path(
    db: AsyncSession,
    project_id: uuid.UUID,
    parent_id: uuid.UUID | None,
    parts: list[str],
    created_by: uuid.UUID | None,
    cache: dict[tuple[uuid.UUID | None, str], uuid.UUID] | None = None,
) -> uuid.UUID | None:
    """Folder at `parts` below `parent_id`, creating the missing ones (get-or-create, case-insensitive). `cache` lets a
    bulk import resolve thousands of files without a query per path segment."""
    current = parent_id
    for raw in parts:
        name = clean_name(raw, max_length=MAX_FOLDER_NAME_LENGTH)
        key = (current, name.lower())
        if cache is not None and key in cache:
            current = cache[key]
            continue
        found = (
            await db.execute(
                select(DocumentFolder.id).where(
                    DocumentFolder.project_id == project_id,
                    same_or_null(DocumentFolder.parent_id, current),
                    func.lower(DocumentFolder.name) == name.lower(),
                )
            )
        ).scalar_one_or_none()
        if found is None:
            try:
                found = (await create_folder(db, project_id, name, current, created_by)).id
            except ConflictError:  # created concurrently by another upload: use theirs
                found = (
                    await db.execute(
                        select(DocumentFolder.id).where(
                            DocumentFolder.project_id == project_id,
                            same_or_null(DocumentFolder.parent_id, current),
                            func.lower(DocumentFolder.name) == name.lower(),
                        )
                    )
                ).scalar_one()
        if cache is not None:
            cache[key] = found
        current = found
    return current


async def rename_folder(db: AsyncSession, project_id: uuid.UUID, folder_id: uuid.UUID, name: str) -> DocumentFolder:
    folder = await get_folder(db, project_id, folder_id)
    folder.name = clean_name(name, max_length=MAX_FOLDER_NAME_LENGTH)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(f"A folder named '{name.strip()}' already exists here") from None
    await db.refresh(folder)
    from app.features.documents.chunk_paths import refresh_chunk_paths  # (chunk_paths imports this module)

    subtree = subtree_ids(await load_folders(db, project_id), {folder.id})
    ids = (await db.execute(select(Document.id).where(Document.project_id == project_id, Document.folder_id.in_(subtree)))).scalars().all()
    await refresh_chunk_paths(db, project_id, ids)
    return folder


async def rename_document(db: AsyncSession, project_id: uuid.UUID, document_id: uuid.UUID, name: str) -> Document:
    document = await db.get(Document, document_id)
    if document is None or document.project_id != project_id:
        raise NotFoundError("Document not found")
    name = clean_name(name, max_length=MAX_DOCUMENT_NAME_LENGTH)
    _, taken = await sibling_names(db, project_id, document.folder_id)
    taken.discard(document.filename.lower())
    if name.lower() in taken:
        raise ConflictError(f"A file named '{name}' already exists here")
    document.filename = name
    await db.commit()
    await db.refresh(document)
    from app.features.documents.chunk_paths import refresh_chunk_paths  # (chunk_paths imports this module)

    await refresh_chunk_paths(db, project_id, [document.id])
    return document


def count_statuses(
    folders: dict[uuid.UUID, DocumentFolder], rows: list[tuple[uuid.UUID | None, DocumentStatus, int]]
) -> dict[uuid.UUID, dict[str, int]]:
    """Per folder, document counts by status over the folder and everything below it (rows: folder_id, status, n)."""
    totals: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for folder_id, status, n in rows:
        for folder in path_of(folders, folder_id):
            totals[folder.id][status.value] += n
    return {k: dict(v) for k, v in totals.items()}


async def list_folder(db: AsyncSession, project_id: uuid.UUID, folder_id: uuid.UUID | None) -> dict:
    """Contents of one folder (None = project root): breadcrumb, subfolders with recursive status counts, documents,
    and the archive imports uploaded here that are still running or failed."""
    folders = await load_folders(db, project_id)
    if folder_id is not None and folder_id not in folders:
        raise NotFoundError("Folder not found")

    status_rows = (
        await db.execute(
            select(Document.folder_id, Document.status, func.count())
            .where(Document.project_id == project_id, Document.folder_id.is_not(None))
            .group_by(Document.folder_id, Document.status)
        )
    ).all()
    counts = count_statuses(folders, [tuple(r) for r in status_rows])

    children = sorted((f for f in folders.values() if f.parent_id == folder_id), key=lambda f: f.name.lower())
    documents = (
        (
            await db.execute(
                select(Document)
                .where(Document.project_id == project_id, same_or_null(Document.folder_id, folder_id))
                .order_by(func.lower(Document.filename))
            )
        )
        .scalars()
        .all()
    )
    archives = (
        (
            await db.execute(
                select(ArchiveImport)
                .where(ArchiveImport.project_id == project_id, same_or_null(ArchiveImport.folder_id, folder_id))
                .order_by(ArchiveImport.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "folder_id": folder_id,
        "breadcrumb": path_of(folders, folder_id),
        "folders": [{"folder": f, "status_counts": counts.get(f.id, {})} for f in children],
        "documents": list(documents),
        "archives": list(archives),
    }


async def search_documents(db: AsyncSession, project_id: uuid.UUID, query: str, limit: int = 100) -> list[dict]:
    """Documents of the project whose file name contains `query` (case-insensitive), with their folder path."""
    needle = (query or "").strip()
    if not needle:
        raise BadRequestError("Search text must not be empty")
    escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = (
        (
            await db.execute(
                select(Document)
                .where(Document.project_id == project_id, Document.filename.ilike(f"%{escaped}%", escape="\\"))
                .order_by(func.lower(Document.filename))
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    folders = await load_folders(db, project_id)
    return [{"document": d, "path": [f.name for f in path_of(folders, d.folder_id)]} for d in rows]


def resolve_path(folders: dict[uuid.UUID, DocumentFolder], path: str | None) -> uuid.UUID | None:
    """The folder a "a/b/c" path points to (case-insensitive, `/` or backslash separators);
    None for the project root (empty path). Raises NotFoundError naming the part that does not exist."""
    parts = split_relative_path(path or "")
    current: uuid.UUID | None = None
    for index, part in enumerate(parts):
        wanted = part.strip().lower()
        match = next((f for f in folders.values() if f.parent_id == current and f.name.lower() == wanted), None)
        if match is None:
            raise NotFoundError(f"Folder '{part}' not found" + (f" inside '{'/'.join(parts[:index])}'" if index else " at the top level"))
        current = match.id
    return current
