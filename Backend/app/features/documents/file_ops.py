"""File-manager operations on a project's documents and folders: upload, move (cut), copy, delete, retry, cancel.

All of them take a *selection* (document ids + folder ids, the way a file manager selects) and only ever touch items of
the given project. Moving/renaming changes `folder_id`/`filename` only - chunks and embeddings are untouched, so it never
triggers re-processing.
"""
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.features.documents import archive_service, service
from app.features.documents.folder_service import (
    get_folder,
    load_folders,
    sibling_names,
    subtree_ids,
    unique_name,
)
from app.features.documents.models import ArchiveImport, ArchiveImportStatus, Document, DocumentFolder, DocumentStatus

settings = get_settings()

OnConflict = Literal["fail", "rename"]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@dataclass
class UploadOutcome:
    filename: str
    document: Document | None = None
    archive: ArchiveImport | None = None
    error: str | None = None


async def upload_project_files(
    db: AsyncSession,
    files: Sequence[service.UploadedFileLike],
    *,
    uploaded_by: uuid.UUID,
    project_id: uuid.UUID,
    folder_id: uuid.UUID | None,
) -> list[UploadOutcome]:
    """Uploads into a project's file manager, one outcome per file, in input order.

    Differs from the conversation uploader in three ways: files of an unsupported type are kept (as UNSUPPORTED)
    instead of rejected, a relative path in the name creates folders, and an archive is queued for extraction into
    `folder_id` instead of becoming a document. A file that fails never affects the others."""
    if len(files) > settings.max_batch_upload_files:
        raise BadRequestError(
            f"At most {settings.max_batch_upload_files} files per request; send the rest in another request"
        )
    if folder_id is not None:
        await get_folder(db, project_id, folder_id)

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    outcomes: list[UploadOutcome] = []
    for upload in files:
        filename = upload.filename or "untitled"
        if len(filename) > service._MAX_FILENAME_LENGTH:
            outcomes.append(UploadOutcome(filename[:80] + "…", error="File name is too long"))
            continue
        try:
            if archive_service.is_archive(filename):
                archive = await archive_service.create_archive_import(
                    db, upload, project_id=project_id, folder_id=folder_id, uploaded_by=uploaded_by
                )
                outcomes.append(UploadOutcome(filename, archive=archive))
                continue

            file_bytes = await upload.read()
            if not file_bytes:
                outcomes.append(UploadOutcome(filename, error="File is empty"))
                continue
            if len(file_bytes) > max_bytes:
                outcomes.append(UploadOutcome(filename, error="File exceeds the maximum allowed upload size"))
                continue
            document = await service._create_document(
                db,
                filename=filename,
                content_type=upload.content_type or "application/octet-stream",
                file_bytes=file_bytes,
                uploaded_by=uploaded_by,
                project_id=project_id,
                conversation_id=None,
                folder_id=folder_id,
                keep_unsupported=True,
            )
            outcomes.append(UploadOutcome(filename, document=document))
        except BadRequestError as exc:  # raised by validation, before any DB write
            outcomes.append(UploadOutcome(filename, error=str(exc.detail)))
    return outcomes


# ---------------------------------------------------------------------------
# Selections
# ---------------------------------------------------------------------------


@dataclass
class Selection:
    """Resolved, de-nested selection: `folders` are top-level (none has a selected ancestor) and `documents` are the
    selected files that are not already inside a selected folder."""

    folders: list[DocumentFolder] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    all_folders: dict[uuid.UUID, DocumentFolder] = field(default_factory=dict)


async def resolve_selection(
    db: AsyncSession, project_id: uuid.UUID, document_ids: Sequence[uuid.UUID], folder_ids: Sequence[uuid.UUID]
) -> Selection:
    if not document_ids and not folder_ids:
        raise BadRequestError("Nothing selected")
    folders = await load_folders(db, project_id)
    wanted_folders = set(folder_ids)
    if not wanted_folders <= folders.keys():
        raise NotFoundError("Some selected folders were not found")

    documents: list[Document] = []
    if document_ids:
        found = (
            (await db.execute(select(Document).where(Document.id.in_(set(document_ids)), Document.project_id == project_id)))
            .scalars()
            .all()
        )
        if len(found) != len(set(document_ids)):
            raise NotFoundError("Some selected documents were not found")
        documents = list(found)

    covered = subtree_ids(folders, wanted_folders)
    top = [
        folders[fid]
        for fid in wanted_folders
        if not any(anc.id in wanted_folders and anc.id != fid for anc in _ancestors(folders, fid))
    ]
    documents = [d for d in documents if d.folder_id not in covered]
    return Selection(folders=sorted(top, key=lambda f: f.name.lower()), documents=documents, all_folders=folders)


def _ancestors(folders: dict[uuid.UUID, DocumentFolder], folder_id: uuid.UUID) -> list[DocumentFolder]:
    chain, seen = [], {folder_id}
    parent = folders[folder_id].parent_id
    while parent is not None and parent in folders and parent not in seen:
        seen.add(parent)
        chain.append(folders[parent])
        parent = folders[parent].parent_id
    return chain


async def _documents_in_folders(db: AsyncSession, project_id: uuid.UUID, folder_ids: set[uuid.UUID]) -> list[Document]:
    if not folder_ids:
        return []
    result = await db.execute(
        select(Document).where(Document.project_id == project_id, Document.folder_id.in_(folder_ids))
    )
    return list(result.scalars().all())


def _check_target(selection: Selection, target_folder_id: uuid.UUID | None) -> None:
    """A folder can't go into itself or one of its own subfolders."""
    if target_folder_id is None:
        return
    for folder in selection.folders:
        if target_folder_id in subtree_ids(selection.all_folders, {folder.id}):
            raise BadRequestError("A folder cannot be moved or copied into itself or one of its subfolders")


# ---------------------------------------------------------------------------
# Move / copy
# ---------------------------------------------------------------------------


async def _place_names(
    db: AsyncSession,
    project_id: uuid.UUID,
    target_folder_id: uuid.UUID | None,
    selection: Selection,
    on_conflict: OnConflict,
    skip_ids: set[uuid.UUID] = frozenset(),
) -> tuple[dict[uuid.UUID, str], dict[uuid.UUID, str]]:
    """Final name for each selected folder/document in the target, resolving clashes with what is already there (and
    between the selected items themselves). Returns ({folder_id: name}, {document_id: name}). With `fail` any clash
    raises 409 before anything has been changed."""
    taken_folders, taken_documents = await sibling_names(db, project_id, target_folder_id)
    folder_names: dict[uuid.UUID, str] = {}
    document_names: dict[uuid.UUID, str] = {}
    clashes: list[str] = []

    for folder in selection.folders:
        if folder.id in skip_ids:
            continue
        name = folder.name
        if name.lower() in taken_folders:
            if on_conflict == "fail":
                clashes.append(name)
                continue
            name = unique_name(name, taken_folders)
        taken_folders.add(name.lower())
        folder_names[folder.id] = name
    for document in selection.documents:
        if document.id in skip_ids:
            continue
        name = document.filename
        if name.lower() in taken_documents:
            if on_conflict == "fail":
                clashes.append(name)
                continue
            name = unique_name(name, taken_documents)
        taken_documents.add(name.lower())
        document_names[document.id] = name

    if clashes:
        raise ConflictError("Already exists in the destination: " + ", ".join(sorted(clashes)[:10]))
    return folder_names, document_names


async def move_items(
    db: AsyncSession,
    project_id: uuid.UUID,
    document_ids: Sequence[uuid.UUID],
    folder_ids: Sequence[uuid.UUID],
    target_folder_id: uuid.UUID | None,
    on_conflict: OnConflict,
) -> int:
    """Cut + paste. Items already in the target are left alone. Returns how many items were moved."""
    if target_folder_id is not None:
        await get_folder(db, project_id, target_folder_id)
    selection = await resolve_selection(db, project_id, document_ids, folder_ids)
    _check_target(selection, target_folder_id)

    already = {f.id for f in selection.folders if f.parent_id == target_folder_id} | {
        d.id for d in selection.documents if d.folder_id == target_folder_id
    }
    folder_names, document_names = await _place_names(db, project_id, target_folder_id, selection, on_conflict, already)

    for folder in selection.folders:
        if folder.id in folder_names:
            folder.parent_id = target_folder_id
            folder.name = folder_names[folder.id]
    for document in selection.documents:
        if document.id in document_names:
            document.folder_id = target_folder_id
            document.filename = document_names[document.id]
    await db.commit()
    return len(folder_names) + len(document_names)


async def _clone_document(
    db: AsyncSession,
    source: Document,
    *,
    name: str,
    folder_id: uuid.UUID | None,
    created_by: uuid.UUID,
) -> Document:
    """A new document pointing at the same stored file. A READY source with current embeddings gets its chunks copied
    (no OCR/embedding cost); a source still being processed - or embedded with another model - is processed again
    on its own; a failed/cancelled/unsupported source is cloned in that state."""
    reuse_chunks = source.status == DocumentStatus.READY and source.embedding_model == settings.embedding_model
    status = source.status
    if source.status == DocumentStatus.READY and not reuse_chunks:
        status = DocumentStatus.PROCESSING
    clone = Document(
        filename=name,
        file_path=source.file_path,
        content_type=source.content_type,
        status=status,
        error_message=source.error_message if status in (DocumentStatus.FAILED, DocumentStatus.UNSUPPORTED) else None,
        content_hash=source.content_hash,
        embedding_model=source.embedding_model if reuse_chunks else None,
        project_id=source.project_id,
        folder_id=folder_id,
        uploaded_by=created_by,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    if reuse_chunks:
        await service._copy_chunks(db, source, clone)
    elif status == DocumentStatus.PROCESSING:
        service._enqueue_ingestion(clone)
    return clone


async def copy_items(
    db: AsyncSession,
    project_id: uuid.UUID,
    document_ids: Sequence[uuid.UUID],
    folder_ids: Sequence[uuid.UUID],
    target_folder_id: uuid.UUID | None,
    on_conflict: OnConflict,
    created_by: uuid.UUID,
) -> int:
    """Copy + paste, including whole folder trees. Returns the number of documents created."""
    if target_folder_id is not None:
        await get_folder(db, project_id, target_folder_id)
    selection = await resolve_selection(db, project_id, document_ids, folder_ids)
    _check_target(selection, target_folder_id)
    folder_names, document_names = await _place_names(db, project_id, target_folder_id, selection, on_conflict)

    created = 0
    for document in selection.documents:
        await _clone_document(db, document, name=document_names[document.id], folder_id=target_folder_id, created_by=created_by)
        created += 1
    for folder in selection.folders:
        created += await _copy_tree(db, project_id, selection.all_folders, folder, target_folder_id, folder_names[folder.id], created_by)
    return created


async def _copy_tree(
    db: AsyncSession,
    project_id: uuid.UUID,
    folders: dict[uuid.UUID, DocumentFolder],
    source: DocumentFolder,
    parent_id: uuid.UUID | None,
    name: str,
    created_by: uuid.UUID,
) -> int:
    new_folder = DocumentFolder(project_id=project_id, parent_id=parent_id, name=name, created_by=created_by)
    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)

    created = 0
    for document in await _documents_in_folders(db, project_id, {source.id}):
        await _clone_document(db, document, name=document.filename, folder_id=new_folder.id, created_by=created_by)
        created += 1
    for child in sorted((f for f in folders.values() if f.parent_id == source.id), key=lambda f: f.name.lower()):
        created += await _copy_tree(db, project_id, folders, child, new_folder.id, child.name, created_by)
    return created


# ---------------------------------------------------------------------------
# Delete / retry / cancel
# ---------------------------------------------------------------------------


async def _expand(db: AsyncSession, project_id: uuid.UUID, selection: Selection) -> list[Document]:
    """Every document in the selection, including the contents of selected folders."""
    covered = subtree_ids(selection.all_folders, {f.id for f in selection.folders})
    return [*selection.documents, *await _documents_in_folders(db, project_id, covered)]


async def delete_items(
    db: AsyncSession, project_id: uuid.UUID, document_ids: Sequence[uuid.UUID], folder_ids: Sequence[uuid.UUID]
) -> int:
    """Deletes the selected documents and folders (with everything inside). Returns the number of documents deleted.
    Each document goes through `service.delete_document`, so a stored file shared with another document stays."""
    selection = await resolve_selection(db, project_id, document_ids, folder_ids)
    documents = await _expand(db, project_id, selection)
    for document in documents:
        await service.delete_document(db, document.id)
    if selection.folders:
        # Child folders (and anything left in them) go through the FK cascade.
        await db.execute(delete(DocumentFolder).where(DocumentFolder.id.in_([f.id for f in selection.folders])))
        await db.commit()
    return len(documents)


async def retry_items(
    db: AsyncSession, project_id: uuid.UUID, document_ids: Sequence[uuid.UUID], folder_ids: Sequence[uuid.UUID]
) -> tuple[int, int]:
    """Re-queues every failed/cancelled (or newly supported) document in the selection. Returns (retried, skipped);
    documents in any other state, or of a still-unsupported type, count as skipped."""
    selection = await resolve_selection(db, project_id, document_ids, folder_ids)
    retried = skipped = 0
    for document in await _expand(db, project_id, selection):
        try:
            await service.retry_failed_document(db, document)
            retried += 1
        except BadRequestError:
            skipped += 1
    return retried, skipped


async def cancel_items(
    db: AsyncSession, project_id: uuid.UUID, document_ids: Sequence[uuid.UUID], folder_ids: Sequence[uuid.UUID]
) -> tuple[int, int]:
    """Cancels every document in the selection that is being processed. Returns (cancelled, skipped)."""
    selection = await resolve_selection(db, project_id, document_ids, folder_ids)
    cancelled = skipped = 0
    for document in await _expand(db, project_id, selection):
        try:
            await service.cancel_document(db, document)
            cancelled += 1
        except BadRequestError:
            skipped += 1
    return cancelled, skipped


async def dismiss_archive(db: AsyncSession, project_id: uuid.UUID, archive_id: uuid.UUID) -> None:
    """Removes a finished/failed archive-import record from the listing (running imports can't be dismissed)."""
    archive = await db.get(ArchiveImport, archive_id)
    if archive is None or archive.project_id != project_id:
        raise NotFoundError("Archive import not found")
    if archive.status == ArchiveImportStatus.EXTRACTING:
        raise BadRequestError("This archive is still being extracted")
    await db.delete(archive)
    await db.commit()
