import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context
from app.core.exceptions import BadRequestError
from app.features.access_control.service import get_user_teams
from app.features.documents import service
from app.features.documents.schemas import DocumentRead, DocumentUploadResponse, TeamOption

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_documents(db, context)


@router.get("/teams/mine", response_model=list[TeamOption])
async def my_teams(
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Teams the current user belongs to, used to populate the upload form."""
    return await get_user_teams(db, context.id)


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    team_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise BadRequestError("File exceeds the maximum allowed upload size")

    document = await service.upload_document(
        db,
        context,
        team_id=team_id,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
    )
    return DocumentUploadResponse(document=document)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    document = await service.get_document(db, document_id)
    if document.team_id not in context.team_ids:
        raise BadRequestError("You do not have access to this document")
    await service.delete_document(db, document_id)
