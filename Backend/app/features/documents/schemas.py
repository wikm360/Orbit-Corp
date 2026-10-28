import uuid
from typing import Literal
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.documents.models import ArchiveImportStatus, DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    status: DocumentStatus
    error_message: str | None
    project_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    folder_id: uuid.UUID | None = None
    uploaded_by: uuid.UUID | None
    created_at: datetime


class ArchiveImportRead(BaseModel):
    """An uploaded .zip/.rar/.7z being unpacked into `folder_id` (None = project root). Its members appear as ordinary
    documents; `failed_files` lists members that could not be imported ({path, error})."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    folder_id: uuid.UUID | None
    filename: str
    status: ArchiveImportStatus
    error_message: str | None
    total_files: int
    imported_files: int
    skipped_files: int
    failed_files: list[dict]
    created_at: datetime
    finished_at: datetime | None


class DocumentUploadResponse(BaseModel):
    """Exactly one of `document` / `archive` is set (an archive upload is unpacked in the background)."""

    document: DocumentRead | None = None
    archive: ArchiveImportRead | None = None
    message: str = "Document accepted for processing"


class BatchUploadItem(BaseModel):
    """Outcome for one file in a batch upload. A rejected file never fails the
    rest of the batch - check `status` per item."""

    filename: str
    status: Literal["accepted", "rejected"]
    document: DocumentRead | None = None
    archive: ArchiveImportRead | None = None
    error: str | None = None


class BatchUploadResponse(BaseModel):
    items: list[BatchUploadItem]
    accepted: int
    rejected: int

    @classmethod
    def from_items(cls, items: list[BatchUploadItem]) -> "BatchUploadResponse":
        accepted = sum(1 for item in items if item.status == "accepted")
        return cls(items=items, accepted=accepted, rejected=len(items) - accepted)


# ---------------------------------------------------------------------------
# File manager
# ---------------------------------------------------------------------------


class FolderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    created_at: datetime


class FolderEntry(BaseModel):
    """A subfolder in a listing. `status_counts` = documents by status over the folder and everything below it
    (e.g. {"ready": 40, "processing": 7, "failed": 1}); statuses with no documents are omitted."""

    folder: FolderRead
    status_counts: dict[str, int]


class FolderListing(BaseModel):
    folder_id: uuid.UUID | None
    breadcrumb: list[FolderRead]
    folders: list[FolderEntry]
    documents: list[DocumentRead]
    archives: list[ArchiveImportRead]


class DocumentSearchHit(BaseModel):
    document: DocumentRead
    path: list[str]


class FolderCreate(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None


class FolderUpdate(BaseModel):
    name: str


class DocumentUpdate(BaseModel):
    filename: str


class FileSelection(BaseModel):
    """What a file manager has selected. Folders include everything inside them."""

    document_ids: list[uuid.UUID] = []
    folder_ids: list[uuid.UUID] = []


class FilePlacement(FileSelection):
    """Move/copy `FileSelection` into `target_folder_id` (None = project root). `on_conflict`: `fail` answers 409
    without changing anything if a name is taken; `rename` keeps both by adding ` (n)`."""

    target_folder_id: uuid.UUID | None = None
    on_conflict: Literal["fail", "rename"] = "fail"


class BulkResult(BaseModel):
    """`count` items changed (moved, copied documents, deleted documents, retried, cancelled); `skipped` = items that
    were not in a state the action applies to."""

    count: int
    skipped: int = 0
