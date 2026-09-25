import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.features.agent.schemas import SourceCitation  # noqa: F401 - re-exported for existing importers
from app.features.chat.models import ConversationType, SenderType


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_type: SenderType
    sender_id: uuid.UUID | None
    content: str
    sources: list[SourceCitation]
    reply_to_message_id: uuid.UUID | None
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ConversationType
    project_id: uuid.UUID | None
    linked_project_id: uuid.UUID | None
    created_by: uuid.UUID | None
    title: str
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class ConversationCreate(BaseModel):
    type: ConversationType
    project_id: uuid.UUID | None = None
    linked_project_id: uuid.UUID | None = None
    title: str | None = None

    @model_validator(mode="after")
    def _validate_scope(self) -> "ConversationCreate":
        if self.type == ConversationType.PROJECT_GROUP:
            if self.project_id is None:
                raise ValueError("project_id is required for a project_group conversation")
            if self.linked_project_id is not None:
                raise ValueError("linked_project_id only applies to personal conversations")
        else:
            if self.project_id is not None:
                raise ValueError("project_id only applies to project_group conversations")
        return self


class ConversationUpdate(BaseModel):
    """`title` can be changed on any conversation - group or personal - and
    is left untouched if omitted. `linked_project_id` only applies to
    personal conversations; it's required (but nullable) so the caller must
    be explicit about attaching vs. clearing it, rather than an omitted
    field silently clearing it - a group conversation's PATCH must still
    send it as `null`.
    """

    linked_project_id: uuid.UUID | None
    title: str | None = None


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str


class GroupMessageCreate(BaseModel):
    content: str
