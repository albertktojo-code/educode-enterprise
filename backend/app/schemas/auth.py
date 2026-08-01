from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.auth import OrganizationRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    session_id: UUID | None = None
    remember_me: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=40, max_length=300)
    new_password: str = Field(min_length=10, max_length=128)
    confirm_password: str = Field(min_length=10, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("A confirmação da senha não confere")
        return self


class SessionRead(BaseModel):
    id: UUID
    device_name: str
    last_ip_masked: str
    remember_me: bool
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    idle_expires_at: datetime
    current: bool


class RevokeAllSessionsRequest(BaseModel):
    keep_current: bool = True


class OrganizationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class OrganizationRead(OrganizationSummary):
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    slug: str | None = Field(default=None, min_length=2, max_length=100)


class MembershipSummary(BaseModel):
    id: UUID
    role: OrganizationRole
    organization: OrganizationSummary


class UserMe(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    memberships: list[MembershipSummary]


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=10, max_length=128)
    role: OrganizationRole = OrganizationRole.MEMBER


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=160)
    role: OrganizationRole | None = None
    is_active: bool | None = None


class UserPasswordReset(BaseModel):
    new_password: str = Field(min_length=10, max_length=128)


class UserListItem(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    role: OrganizationRole
    created_at: datetime
