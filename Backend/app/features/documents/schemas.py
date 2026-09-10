import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.documents.models import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    status: DocumentStatus
    error_message: str | None
    project_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    uploaded_by: uuid.UUID | None
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    message: str = "Document accepted for processing"
