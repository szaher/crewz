"""Authentication and authorization schemas."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


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

    sub: int  # user_id
    tenant_id: int
    tenant_schema: str
    role: str
    exp: datetime


class LoginResponse(BaseModel):
    """Login response schema."""

    access_token: str
    token_type: str = "bearer"
    user_id: int
    tenant_id: int
    role: str


class RegisterResponse(BaseModel):
    """Registration response schema."""

    user_id: int
    tenant_id: int
    email: str
    message: str = "Registration successful"
