import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.chat.models import MessageRole


class SourceCitation(BaseModel):
    document_id: str
    document_filename: str
    chunk_index: int
    snippet: str
    score: float


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    sources: list[SourceCitation]
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str
