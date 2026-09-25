import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.memory.models import MemoryCategory


class ProjectMemoryCreate(BaseModel):
    fact_text: str
    category: MemoryCategory


class ProjectMemoryUpdate(BaseModel):
    """All fields optional and update-if-provided. Changing `fact_text`
    re-embeds it, since a stale embedding would keep semantic search
    matching on the old wording."""

    fact_text: str | None = None
    category: MemoryCategory | None = None
    is_verified: bool | None = None


class ProjectMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    fact_text: str
    category: MemoryCategory
    confidence_score: float
    is_verified: bool
    created_at: datetime
    updated_at: datetime
