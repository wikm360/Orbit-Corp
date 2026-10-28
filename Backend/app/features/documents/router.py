import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context, require_project_access, require_project_manager
from app.core.exceptions import BadRequestError
from app.features.documents import archive_service, file_ops, folder_service, service
from app.features.documents.schemas import (
    BatchUploadItem,
    BatchUploadResponse,
    BulkResult,
    DocumentRead,
    DocumentSearchHit,
    DocumentUpdate,
    DocumentUploadResponse,
    FilePlacement,
    FileSelection,
    FolderCreate,
    FolderListing,
    FolderRead,
    FolderUpdate,
)
from app.features.projects.models import Project

router = APIRouter(tags=["documents"])
settings = get_settings()


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
async def list_project_documents(
    project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_project_documents(db, project.id)


@router.post("/projects/{project_id}/documents", response_model=DocumentUploadResponse)
async def upload_project_document(
    file: UploadFile = File(...),
    folder_id: uuid.UUID | None = Form(None),
    project: Project = Depends(require_project_manager),
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Uploads one file (into `folder_id`, default the project root). A .zip/.rar/.7z is unpacked in the background
    into that folder: the response then carries `archive` instead of `document`."""
    if archive_service.is_archive(file.filename):
        archive = await archive_service.create_archive_import(
            db, file, project_id=project.id, folder_id=folder_id, uploaded_by=context.id
        )
        return DocumentUploadResponse(archive=archive, message="Archive accepted for extraction")

    file_bytes = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise BadRequestError("File exceeds the maximum allowed upload size")
    if folder_id is not None:
        await folder_service.get_folder(db, project.id, folder_id)

    document = await service._create_document(
        db,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
        uploaded_by=context.id,
        project_id=project.id,
        conversation_id=None,
        folder_id=folder_id,
        keep_unsupported=True,
    )
    return DocumentUploadResponse(document=document)


@router.post("/projects/{project_id}/documents/batch", response_model=BatchUploadResponse)
async def upload_project_documents_batch(
    files: list[UploadFile] = File(...),
    folder_id: uuid.UUID | None = Form(None),
    project: Project = Depends(require_project_manager),
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Uploads several files at once (a browser folder upload may send `dir/sub/file.pdf` names: the folders are
    created). Each accepted file is queued for ingestion independently; a rejected file doesn't fail the others.
    Archives are unpacked in the background (`archive` in the item); unsupported types are kept as `unsupported`."""
    outcomes = await file_ops.upload_project_files(
        db, files, uploaded_by=context.id, project_id=project.id, folder_id=folder_id
    )
    return BatchUploadResponse.from_items(
        [
            BatchUploadItem(
                filename=o.filename,
                status="rejected" if o.error is not None else "accepted",
                document=o.document,
                archive=o.archive,
                error=o.error,
            )
            for o in outcomes
        ]
    )


# ---------------------------------------------------------------------------
# File manager (project scope only; access is the project's, folders never narrow it)
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/files", response_model=FolderListing)
async def list_folder(
    folder_id: uuid.UUID | None = None,
    project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """One folder's contents (default: the project root): breadcrumb, subfolders with recursive status counts,
    documents with their processing status, and archive imports still running or failed."""
    return await folder_service.list_folder(db, project.id, folder_id)


@router.get("/projects/{project_id}/files/search", response_model=list[DocumentSearchHit])
async def search_files(
    q: str,
    project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    return await folder_service.search_documents(db, project.id, q)


@router.post("/projects/{project_id}/folders", response_model=FolderRead, status_code=201)
async def create_folder(
    body: FolderCreate,
    project: Project = Depends(require_project_manager),
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await folder_service.create_folder(db, project.id, body.name, body.parent_id, context.id)


@router.patch("/projects/{project_id}/folders/{folder_id}", response_model=FolderRead)
async def rename_folder(
    folder_id: uuid.UUID,
    body: FolderUpdate,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    return await folder_service.rename_folder(db, project.id, folder_id, body.name)


@router.patch("/projects/{project_id}/documents/{document_id}", response_model=DocumentRead)
async def rename_project_document(
    document_id: uuid.UUID,
    body: DocumentUpdate,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    return await folder_service.rename_document(db, project.id, document_id, body.filename)


@router.post("/projects/{project_id}/files/move", response_model=BulkResult)
async def move_files(
    body: FilePlacement,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    moved = await file_ops.move_items(
        db, project.id, body.document_ids, body.folder_ids, body.target_folder_id, body.on_conflict
    )
    return BulkResult(count=moved)


@router.post("/projects/{project_id}/files/copy", response_model=BulkResult)
async def copy_files(
    body: FilePlacement,
    project: Project = Depends(require_project_manager),
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    copied = await file_ops.copy_items(
        db, project.id, body.document_ids, body.folder_ids, body.target_folder_id, body.on_conflict, context.id
    )
    return BulkResult(count=copied)


@router.post("/projects/{project_id}/files/delete", response_model=BulkResult)
async def delete_files(
    body: FileSelection,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    return BulkResult(count=await file_ops.delete_items(db, project.id, body.document_ids, body.folder_ids))


@router.post("/projects/{project_id}/files/retry", response_model=BulkResult)
async def retry_files(
    body: FileSelection,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    retried, skipped = await file_ops.retry_items(db, project.id, body.document_ids, body.folder_ids)
    return BulkResult(count=retried, skipped=skipped)


@router.post("/projects/{project_id}/files/cancel", response_model=BulkResult)
async def cancel_files(
    body: FileSelection,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    cancelled, skipped = await file_ops.cancel_items(db, project.id, body.document_ids, body.folder_ids)
    return BulkResult(count=cancelled, skipped=skipped)


@router.delete("/projects/{project_id}/archives/{archive_id}", status_code=204)
async def dismiss_archive_import(
    archive_id: uuid.UUID,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    await file_ops.dismiss_archive(db, project.id, archive_id)


@router.post("/projects/{project_id}/documents/{document_id}/cancel", response_model=DocumentRead)
async def cancel_project_document(
    document_id: uuid.UUID,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    document = await service.get_document(db, document_id)
    if document.project_id != project.id:
        raise BadRequestError("This document does not belong to the given project")
    return await service.cancel_document(db, document)


@router.post("/projects/{project_id}/documents/{document_id}/retry", response_model=DocumentRead)
async def retry_project_document(
    document_id: uuid.UUID,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    document = await service.get_document(db, document_id)
    if document.project_id != project.id:
        raise BadRequestError("This document does not belong to the given project")
    return await service.retry_failed_document(db, document)


@router.delete("/projects/{project_id}/documents/{document_id}", status_code=204)
async def delete_project_document(
    document_id: uuid.UUID,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    document = await service.get_document(db, document_id)
    if document.project_id != project.id:
        raise BadRequestError("This document does not belong to the given project")
    await service.delete_document(db, document_id)
