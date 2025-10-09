"""Schemas for user profile endpoints."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List


class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    tenant_id: int
    is_active: bool


class UserProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)


class UserAdminResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: str


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field('member', pattern=r'^(admin|member|viewer)$')
    password: str = Field(..., min_length=8)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, pattern=r'^(admin|member|viewer)$')
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserListResponse(BaseModel):
    users: List[UserAdminResponse]
    total: int
    page: int
    page_size: int
