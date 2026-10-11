import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.features.db_connector.models import QueryStatus


class DbQueryFeedbackRequest(BaseModel):
    feedback: int = Field(..., ge=-1, le=1, description="1 for helpful (thumbs up), -1 for wrong/unhelpful (thumbs down), 0 to clear")
    note: str | None = Field(default=None, max_length=2000, description="Optional note or explanation")


class DbQueryLogRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    question: str
    hint_keys: list[str]
    sql_text: str | None
    attempts: int
    status: QueryStatus
    error_message: str | None
    row_count: int | None
    truncated: bool
    duration_ms: int | None
    feedback: int | None
    feedback_note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DbQueryStats(BaseModel):
    total_queries: int
    successful_queries: int
    rejected_queries: int
    error_queries: int
    positive_feedback: int
    negative_feedback: int
    avg_duration_ms: float | None


class IngestResponse(BaseModel):
    total: int
    unchanged: int
    embedded: int
    stored_without_embedding: int
    deleted: int
