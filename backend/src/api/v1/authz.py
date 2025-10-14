"""Authorization API endpoints."""

from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ...api.middleware.auth import require_auth
from ...schemas.authorization import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    BulkCheckRequest,
    BulkCheckResponse,
    RoleResponse,
    RoleCreate,
    RoleUpdate,
    RoleListResponse,
    RoleDetailResponse,
    PermissionCreate,
    PermissionResponse,
    PolicyResponse,
    PolicyCreate,
    PolicyUpdate,
    PolicyListResponse,
    AuditLogResponse,
    AuditLogListResponse,
    InvalidateSessionRequest,
    InvalidateSessionResponse,
)
from ...services.authorization_service import AuthorizationService
from ...services.role_service import RoleService
from ...services.policy_service import PolicyService
from ...models import AuthorizationAuditLog

router = APIRouter()


@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(
    request_body: PermissionCheckRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Check if user has permission to perform action on resource.

    Performance target: <50ms at p95

    Args:
        request_body: Permission check request
        request: FastAPI request object for IP/user agent
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Permission decision with reason and latency
    """
    # Extract user info
    user_id = current_user["id"]
    tenant_id = current_user["tenant_id"]

    # Extract request metadata
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Check permission
    authz_service = AuthorizationService(db)
    result = authz_service.check_permission(
        user_id=user_id,
        tenant_id=tenant_id,
        resource_type=request_body.resource_type,
        resource_id=request_body.resource_id,
        action=request_body.action.value,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return PermissionCheckResponse(**result)


@router.post("/bulk-check", response_model=BulkCheckResponse)
async def bulk_check_permissions(
    request_body: BulkCheckRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Check multiple permissions in batch.

    Useful for UI rendering (show/hide actions based on permissions).
    Maximum 20 checks per request.

    Args:
        request_body: Bulk check request with list of checks
        request: FastAPI request object for IP/user agent
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        List of permission decisions with total latency
    """
    # Extract user info
    user_id = current_user["id"]
    tenant_id = current_user["tenant_id"]

    # Extract request metadata
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Convert checks to format expected by service
    checks = [
        {
            "resource_type": check.resource_type,
            "resource_id": check.resource_id,
            "action": check.action.value,
        }
        for check in request_body.checks
    ]

    # Bulk check permissions
    authz_service = AuthorizationService(db)
    result = authz_service.bulk_check_permissions(
        user_id=user_id,
        tenant_id=tenant_id,
        checks=checks,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return BulkCheckResponse(**result)


# ============================================================================
# Role Management Endpoints
# ============================================================================

@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    include_system: bool = Query(True, description="Include system roles"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List roles for tenant (system + custom roles)."""
    tenant_id = current_user["tenant_id"]

    role_service = RoleService(db)
    result = role_service.list_roles(
        tenant_id=tenant_id,
        include_system=include_system,
        page=page,
        page_size=page_size,
    )

    return RoleListResponse(**result)


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create custom role (tenant-admin only)."""
    # Check if user is tenant admin
    if current_user.get("role") not in ["admin", "tenant-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin role required"
        )

    tenant_id = current_user["tenant_id"]

    role_service = RoleService(db)
    role = role_service.create_role(
        tenant_id=tenant_id,
        name=role_data.name,
        slug=role_data.slug,
        description=role_data.description,
        is_default=role_data.is_default,
        priority=role_data.priority,
    )

    return RoleResponse.model_validate(role)


@router.get("/roles/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    role_id: UUID,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get role details with permissions and user count."""
    tenant_id = current_user["tenant_id"]

    role_service = RoleService(db)
    result = role_service.get_role(role_id=role_id, tenant_id=tenant_id)

    return RoleDetailResponse(
        **result["role"].__dict__,
        permissions=[PermissionResponse.model_validate(p) for p in result["permissions"]],
        user_count=result["user_count"]
    )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update role (tenant-admin only, cannot modify system roles)."""
    # Check if user is tenant admin
    if current_user.get("role") not in ["admin", "tenant-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin role required"
        )

    tenant_id = current_user["tenant_id"]

    role_service = RoleService(db)
    role = role_service.update_role(
        role_id=role_id,
        tenant_id=tenant_id,
        name=role_data.name,
        description=role_data.description,
        is_default=role_data.is_default,
        priority=role_data.priority,
    )

    return RoleResponse.model_validate(role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete role (tenant-admin only, cannot delete system roles)."""
    # Check if user is tenant admin
    if current_user.get("role") not in ["admin", "tenant-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin role required"
        )

    tenant_id = current_user["tenant_id"]

    role_service = RoleService(db)
    role_service.delete_role(role_id=role_id, tenant_id=tenant_id)


@router.post("/roles/{role_id}/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def add_role_permission(
    role_id: UUID,
    permission_data: PermissionCreate,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add permission to role (tenant-admin only)."""
    # Check if user is tenant admin
    if current_user.get("role") not in ["admin", "tenant-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin role required"
        )

    tenant_id = current_user["tenant_id"]

    role_service = RoleService(db)
    permission = role_service.add_role_permission(
        role_id=role_id,
        tenant_id=tenant_id,
        resource_type=permission_data.resource_type,
        resource_id=permission_data.resource_id,
        action=permission_data.action.value,
        effect=permission_data.effect.value,
        conditions=permission_data.conditions,
    )

    return PermissionResponse.model_validate(permission)


# ============================================================================
# Policy Management Endpoints
# ============================================================================

@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    scope: Optional[str] = Query(None, regex="^(tenant|user|all)$"),
    active_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List policies (tenant-level and user-level for current user)."""
    tenant_id = current_user["tenant_id"]
    user_id = current_user["id"]

    # Map "all" to None for service layer
    scope_filter = None if scope == "all" else scope

    policy_service = PolicyService(db)
    result = policy_service.list_policies(
        tenant_id=tenant_id,
        user_id=user_id,
        scope=scope_filter,
        active_only=active_only,
        page=page,
        page_size=page_size,
    )

    return PolicyListResponse(**result)


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy_data: PolicyCreate,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create policy (tenant policies require tenant-admin role)."""
    tenant_id = current_user["tenant_id"]

    # Tenant-level policies require tenant-admin
    if policy_data.scope.value == "tenant":
        if current_user.get("role") not in ["admin", "tenant-admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admin role required for tenant-level policies"
            )

    policy_service = PolicyService(db)
    policy = policy_service.create_policy(
        tenant_id=tenant_id,
        scope=policy_data.scope.value,
        name=policy_data.name,
        resource_pattern=policy_data.resource_pattern,
        action_pattern=policy_data.action_pattern,
        effect=policy_data.effect.value,
        scope_id=policy_data.scope_id,
        description=policy_data.description,
        conditions=policy_data.conditions,
        priority=policy_data.priority,
    )

    return PolicyResponse.model_validate(policy)


@router.put("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: UUID,
    policy_data: PolicyUpdate,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update policy."""
    tenant_id = current_user["tenant_id"]

    policy_service = PolicyService(db)
    policy = policy_service.update_policy(
        policy_id=policy_id,
        tenant_id=tenant_id,
        name=policy_data.name,
        description=policy_data.description,
        resource_pattern=policy_data.resource_pattern,
        action_pattern=policy_data.action_pattern,
        effect=policy_data.effect.value if policy_data.effect else None,
        conditions=policy_data.conditions,
        priority=policy_data.priority,
        is_active=policy_data.is_active,
    )

    return PolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: UUID,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete policy."""
    tenant_id = current_user["tenant_id"]

    policy_service = PolicyService(db)
    policy_service.delete_policy(policy_id=policy_id, tenant_id=tenant_id)


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get("/audit", response_model=AuditLogListResponse)
async def query_audit_logs(
    user_id: Optional[UUID] = Query(None),
    resource_type: Optional[str] = Query(None),
    decision: Optional[str] = Query(None, regex="^(allow|deny)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Query authorization audit logs (tenant admins see their tenant, super admins see all)."""
    tenant_id = current_user["tenant_id"]

    # Build query
    query = db.query(AuthorizationAuditLog).filter(
        AuthorizationAuditLog.tenant_id == tenant_id
    )

    # Apply filters
    if user_id:
        query = query.filter(AuthorizationAuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuthorizationAuditLog.resource_type == resource_type)
    if decision:
        query = query.filter(AuthorizationAuditLog.decision == decision)
    if start_time:
        query = query.filter(AuthorizationAuditLog.timestamp >= start_time)
    if end_time:
        query = query.filter(AuthorizationAuditLog.timestamp <= end_time)

    # Order by timestamp descending
    query = query.order_by(AuthorizationAuditLog.timestamp.desc())

    total = query.count()

    # Pagination
    offset = (page - 1) * page_size
    logs = query.offset(offset).limit(page_size).all()

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post("/sessions/invalidate", response_model=InvalidateSessionResponse)
async def invalidate_sessions(
    request_data: InvalidateSessionRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Invalidate user sessions (clear permission cache)."""
    # Tenant admins can invalidate any user in their tenant
    if current_user.get("role") not in ["admin", "tenant-admin"]:
        # Regular users can only invalidate their own sessions
        if request_data.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot invalidate other users' sessions"
            )

    # Invalidate cache
    authz_service = AuthorizationService(db)
    cache_count = authz_service.invalidate_cache(request_data.user_id, "*")

    return InvalidateSessionResponse(
        invalidated_sessions=cache_count,
        message=f"Invalidated {cache_count} cached permission checks. Reason: {request_data.reason}"
    )
