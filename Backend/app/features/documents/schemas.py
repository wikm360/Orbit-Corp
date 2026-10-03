import uuid
from typing import Literal
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


class BatchUploadItem(BaseModel):
    """Outcome for one file in a batch upload. A rejected file never fails the
    rest of the batch - check `status` per item."""

    filename: str
    status: Literal["accepted", "rejected"]
    document: DocumentRead | None = None
    error: str | None = None


class BatchUploadResponse(BaseModel):
    items: list[BatchUploadItem]
    accepted: int
    rejected: int

    @classmethod
    def from_items(cls, items: list[BatchUploadItem]) -> "BatchUploadResponse":
        accepted = sum(1 for item in items if item.status == "accepted")
        return cls(items=items, accepted=accepted, rejected=len(items) - accepted)
