import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.features.auth.models import UserRole

# bcrypt silently ignores bytes beyond 72; newer bcrypt versions raise instead
# of truncating, so this is enforced at the API boundary to fail with a clean
# 422 rather than a 500 from inside the hashing call.
_MAX_PASSWORD_LENGTH = 72


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=_MAX_PASSWORD_LENGTH)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(max_length=_MAX_PASSWORD_LENGTH)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    # Effective access to the Rahkaran accounting tools (super admins always; others only when granted).
    accounting_access: bool = Field(validation_alias="has_accounting_access")
    accounting_access_granted_at: datetime | None = None
    # Token quota (`token_limit` None = unlimited; super admins are never limited).
    token_limit: int | None = None
    tokens_used: int = 0
    token_period_start: datetime | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshTokenRequest(BaseModel):
    refresh_token: str
