"""Schemas for user profile endpoints."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from uuid import UUID


class RoleInfo(BaseModel):
    """Role information for user responses."""
    id: UUID
    slug: str
    name: str
    is_system_role: bool


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str  # Legacy field - primary role slug
    roles: List[RoleInfo] = []  # New field - all assigned roles
    tenant_id: UUID
    is_active: bool


class UserProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)


class UserAdminResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str  # Legacy field - primary role slug
    roles: List[RoleInfo] = []  # New field - all assigned roles
    is_active: bool
    created_at: str


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role_slugs: List[str] = Field(default=['member'], description="List of role slugs to assign")
    password: str = Field(..., min_length=8)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role_slugs: Optional[List[str]] = Field(None, description="List of role slugs to assign (replaces all current roles)")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserListResponse(BaseModel):
    users: List[UserAdminResponse]
    total: int
    page: int
    page_size: int
