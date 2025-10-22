"""Authentication and authorization schemas."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)
    tenant_name: Optional[str] = Field(None, max_length=255)


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str  # user_id as string (UUID)
    tenant_id: str  # tenant_id as string (UUID)
    tenant_schema: str
    role: str
    is_super_admin: bool = False
    exp: datetime


class LoginResponse(BaseModel):
    """Login response schema."""

    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: UUID
    role: str
    is_super_admin: bool = False


class RegisterResponse(BaseModel):
    """Registration response schema."""

    user_id: UUID
    tenant_id: UUID
    email: str
    message: str = "Registration successful"
