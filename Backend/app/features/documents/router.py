import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context, require_project_access, require_project_manager
from app.core.exceptions import BadRequestError
from app.features.documents import service
from app.features.documents.schemas import DocumentRead, DocumentUploadResponse
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
    project: Project = Depends(require_project_manager),
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise BadRequestError("File exceeds the maximum allowed upload size")

    document = await service.upload_project_document(
        db,
        project_id=project.id,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
        uploaded_by=context.id,
    )
    return DocumentUploadResponse(document=document)


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
