"""Pydantic schemas for authorization endpoints."""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import re


class ActionEnum(str, Enum):
    """Action types for permission checks."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ALL = "*"


class DecisionEnum(str, Enum):
    """Authorization decision."""
    ALLOW = "allow"
    DENY = "deny"


class EffectEnum(str, Enum):
    """Permission/Policy effect."""
    ALLOW = "allow"
    DENY = "deny"


class PolicyScopeEnum(str, Enum):
    """Policy scope."""
    TENANT = "tenant"
    USER = "user"


class SubjectTypeEnum(str, Enum):
    """Permission subject type."""
    USER = "user"
    ROLE = "role"


# ============================================================================
# Permission Check Schemas
# ============================================================================

class PermissionCheckRequest(BaseModel):
    """Request schema for permission check."""
    resource_type: str = Field(..., description="Type of resource (e.g., 'crew', 'flow')")
    resource_id: Optional[UUID] = Field(None, description="Specific resource ID (null = any resource of type)")
    action: ActionEnum = Field(..., description="Action to perform")


class PermissionCheckResponse(BaseModel):
    """Response schema for permission check."""
    decision: DecisionEnum = Field(..., description="Authorization decision")
    reason: str = Field(..., description="Reason for decision (e.g., 'role:admin', 'default:deny')")
    latency_ms: int = Field(..., description="Check latency in milliseconds")


class BulkCheckRequest(BaseModel):
    """Request schema for bulk permission check."""
    checks: List[PermissionCheckRequest] = Field(..., max_length=20, min_length=1)


class BulkCheckResponse(BaseModel):
    """Response schema for bulk permission check."""
    results: List[PermissionCheckResponse]
    total_latency_ms: int


# ============================================================================
# Permission Schemas
# ============================================================================

class PermissionResponse(BaseModel):
    """Permission response schema."""
    id: UUID
    tenant_id: UUID
    subject_type: SubjectTypeEnum
    subject_id: UUID
    resource_type: str
    resource_id: Optional[UUID]
    action: ActionEnum
    effect: EffectEnum
    conditions: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    """Create permission schema."""
    resource_type: str = Field(..., max_length=100)
    resource_id: Optional[UUID] = None
    action: ActionEnum
    effect: EffectEnum = EffectEnum.ALLOW
    conditions: Optional[dict] = None


# ============================================================================
# Role Schemas
# ============================================================================

class RoleResponse(BaseModel):
    """Role response schema."""
    id: UUID
    tenant_id: Optional[UUID]
    name: str
    slug: str
    description: Optional[str]
    is_system_role: bool
    is_default: bool
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


class RoleDetailResponse(RoleResponse):
    """Detailed role response with permissions and user count."""
    permissions: List[PermissionResponse] = []
    user_count: int = 0


class RoleCreate(BaseModel):
    """Create role schema."""
    name: str = Field(..., max_length=100, min_length=1)
    slug: str = Field(..., max_length=100, min_length=1)
    description: Optional[str] = None
    is_default: bool = False
    priority: int = Field(500, ge=0, le=1000)

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v


class RoleUpdate(BaseModel):
    """Update role schema."""
    name: Optional[str] = Field(None, max_length=100, min_length=1)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)


class RoleListResponse(BaseModel):
    """Role list response with pagination."""
    roles: List[RoleResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Policy Schemas
# ============================================================================

class PolicyResponse(BaseModel):
    """Policy response schema."""
    id: UUID
    tenant_id: UUID
    scope: PolicyScopeEnum
    scope_id: Optional[UUID]
    name: str
    description: Optional[str]
    resource_pattern: str
    action_pattern: str
    effect: EffectEnum
    conditions: Optional[dict] = None
    priority: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PolicyCreate(BaseModel):
    """Create policy schema."""
    scope: PolicyScopeEnum
    scope_id: Optional[UUID] = None
    name: str = Field(..., max_length=100, min_length=1)
    description: Optional[str] = None
    resource_pattern: str = Field(..., max_length=200)
    action_pattern: str = Field(..., max_length=50)
    effect: EffectEnum
    conditions: Optional[dict] = None
    priority: int = Field(100, ge=0, le=1000)

    @field_validator('scope_id')
    @classmethod
    def validate_scope_id(cls, v, info):
        if info.data.get('scope') == PolicyScopeEnum.USER and v is None:
            raise ValueError('scope_id is required when scope is "user"')
        return v


class PolicyUpdate(BaseModel):
    """Update policy schema."""
    name: Optional[str] = Field(None, max_length=100, min_length=1)
    description: Optional[str] = None
    resource_pattern: Optional[str] = Field(None, max_length=200)
    action_pattern: Optional[str] = Field(None, max_length=50)
    effect: Optional[EffectEnum] = None
    conditions: Optional[dict] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    is_active: Optional[bool] = None


class PolicyListResponse(BaseModel):
    """Policy list response with pagination."""
    policies: List[PolicyResponse]
    total: int


# ============================================================================
# Audit Log Schemas
# ============================================================================

class AuditLogResponse(BaseModel):
    """Audit log response schema."""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    resource_type: str
    resource_id: Optional[UUID]
    action: str
    decision: DecisionEnum
    reason: str
    latency_ms: int
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Audit log list response with pagination."""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Session Management Schemas
# ============================================================================

class InvalidateSessionRequest(BaseModel):
    """Invalidate user sessions request."""
    user_id: UUID
    reason: Optional[str] = "Permissions changed"


class InvalidateSessionResponse(BaseModel):
    """Invalidate sessions response."""
    invalidated_sessions: int
    message: str
