import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.features.auth.models import UserRole

_MAX_PASSWORD_LENGTH = 72  # bcrypt limit, same as auth.schemas


class ManagedUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    created_at: datetime
    # Whether the *caller* may change/delete this account (so the UI can hide the buttons).
    manageable: bool = False


class ManagedUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=_MAX_PASSWORD_LENGTH)
    full_name: str = Field(min_length=1, max_length=255)


class ManagedUserUpdate(BaseModel):
    """Only the fields sent change."""
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=_MAX_PASSWORD_LENGTH)
