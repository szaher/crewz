"""Tenants management endpoints for super admins."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from ...db.postgres import get_db
from ..middleware.auth import require_auth
from ...models import Tenant, User
from ...models.tenant import TenantStatus


router = APIRouter()


def require_super_admin(current_user: dict = Depends(require_auth)):
    """Ensure the current user is a super admin."""
    if not current_user.get("is_super_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


# Pydantic schemas
class TenantListItem(BaseModel):
    id: str
    name: str
    schema_name: str
    status: str
    max_users: int
    max_agents: int
    max_flows: int
    user_count: int
    created_at: str
    updated_at: str


class TenantDetail(BaseModel):
    id: str
    name: str
    schema_name: str
    status: str
    api_key: str
    max_users: int
    max_agents: int
    max_flows: int
    settings: dict
    user_count: int
    created_at: str
    updated_at: str


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    max_users: Optional[int] = None
    max_agents: Optional[int] = None
    max_flows: Optional[int] = None
    settings: Optional[dict] = None


class TenantUsageStats(BaseModel):
    total_tenants: int
    active_tenants: int
    pending_tenants: int
    suspended_tenants: int


@router.get("/stats", response_model=TenantUsageStats)
async def get_tenant_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """Get overall tenant statistics."""
    total = db.query(Tenant).count()
    active = db.query(Tenant).filter(Tenant.status == TenantStatus.ACTIVE).count()
    pending = db.query(Tenant).filter(Tenant.status == TenantStatus.PENDING).count()
    suspended = db.query(Tenant).filter(Tenant.status == TenantStatus.SUSPENDED).count()

    return TenantUsageStats(
        total_tenants=total,
        active_tenants=active,
        pending_tenants=pending,
        suspended_tenants=suspended,
    )


@router.get("", response_model=dict)
async def list_tenants(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """List all tenants with pagination."""
    query = db.query(Tenant)

    # Filter by status if provided
    if status:
        try:
            status_enum = TenantStatus(status)
            query = query.filter(Tenant.status == status_enum)
        except ValueError:
            pass

    total = query.count()

    tenants = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for t in tenants:
        # Count users for this tenant
        user_count = db.query(User).filter(User.tenant_id == t.id).count()

        status_val = getattr(t.status, 'value', t.status)
        results.append(TenantListItem(
            id=str(t.id),
            name=t.name,
            schema_name=t.schema_name,
            status=status_val,
            max_users=t.max_users,
            max_agents=t.max_agents,
            max_flows=t.max_flows,
            user_count=user_count,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        ))

    return {"tenants": results, "total": total, "skip": skip, "limit": limit}


@router.get("/{tenant_id}", response_model=TenantDetail)
async def get_tenant_detail(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """Get detailed information about a specific tenant."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
    status_val = getattr(tenant.status, 'value', tenant.status)

    return TenantDetail(
        id=str(tenant.id),
        name=tenant.name,
        schema_name=tenant.schema_name,
        status=status_val,
        api_key=tenant.api_key,
        max_users=tenant.max_users,
        max_agents=tenant.max_agents,
        max_flows=tenant.max_flows,
        settings=tenant.settings or {},
        user_count=user_count,
        created_at=tenant.created_at.isoformat(),
        updated_at=tenant.updated_at.isoformat(),
    )


@router.put("/{tenant_id}", response_model=TenantDetail)
async def update_tenant(
    tenant_id: str,
    update: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """Update tenant settings (super admin only)."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Update fields
    if update.name is not None:
        tenant.name = update.name
    if update.status is not None:
        try:
            tenant.status = TenantStatus(update.status)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    if update.max_users is not None:
        tenant.max_users = update.max_users
    if update.max_agents is not None:
        tenant.max_agents = update.max_agents
    if update.max_flows is not None:
        tenant.max_flows = update.max_flows
    if update.settings is not None:
        current_settings = tenant.settings or {}
        current_settings.update(update.settings)
        tenant.settings = current_settings

    db.commit()
    db.refresh(tenant)

    user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
    status_val = getattr(tenant.status, 'value', tenant.status)

    return TenantDetail(
        id=str(tenant.id),
        name=tenant.name,
        schema_name=tenant.schema_name,
        status=status_val,
        api_key=tenant.api_key,
        max_users=tenant.max_users,
        max_agents=tenant.max_agents,
        max_flows=tenant.max_flows,
        settings=tenant.settings or {},
        user_count=user_count,
        created_at=tenant.created_at.isoformat(),
        updated_at=tenant.updated_at.isoformat(),
    )


@router.post("/{tenant_id}/approve")
async def approve_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """Approve a pending tenant."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if tenant.status != TenantStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending tenants can be approved")

    tenant.status = TenantStatus.ACTIVE
    db.commit()

    return {"message": "Tenant approved successfully", "tenant_id": str(tenant.id)}


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """Suspend an active tenant."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant.status = TenantStatus.SUSPENDED
    db.commit()

    return {"message": "Tenant suspended successfully", "tenant_id": str(tenant.id)}


@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """Activate a suspended tenant."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant.status = TenantStatus.ACTIVE
    db.commit()

    return {"message": "Tenant activated successfully", "tenant_id": str(tenant.id)}


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """Delete a tenant (soft delete by setting status to DELETED)."""
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Soft delete
    tenant.status = TenantStatus.DELETED
    db.commit()

    return {"message": "Tenant deleted successfully", "tenant_id": str(tenant.id)}


# ============================================================================
# T049: GET /api/v1/tenants/{id}/storage/quota - Storage quota status
# ============================================================================

class StorageQuotaResponse(BaseModel):
    """Storage quota status response."""
    tenant_id: str
    current_usage_bytes: int
    total_quota_bytes: int
    usage_percentage: float
    is_over_warning: bool
    is_over_alert: bool
    is_over_quota: bool
    warning_threshold: float
    alert_threshold: float
    cleanup_strategy: str
    trace_retention_days: int
    artifact_retention_days: int


@router.get("/{tenant_id}/storage/quota", response_model=StorageQuotaResponse)
async def get_storage_quota(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get storage quota status for a tenant.

    Returns:
    - current_usage_bytes: Current storage used
    - total_quota_bytes: Total allowed storage
    - usage_percentage: Percentage of quota used
    - is_over_warning: True if over warning threshold (default 80%)
    - is_over_alert: True if over alert threshold (default 95%)
    - is_over_quota: True if quota exceeded
    """
    from ...models.tenant_config import TenantConfig
    from ...models.artifact import Artifact
    from sqlalchemy import and_

    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")

    # Check if user belongs to this tenant (or is super admin)
    if not current_user.get("is_super_admin", False):
        if current_user.get("tenant_id") != tenant_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    # Get tenant config
    tenant_config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == tenant_uuid
    ).first()

    if not tenant_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found"
        )

    # Calculate current storage usage (non-deleted artifacts)
    current_usage = db.query(func.sum(Artifact.file_size_bytes)).filter(
        and_(
            Artifact.tenant_id == tenant_uuid,
            Artifact.deleted_at.is_(None)
        )
    ).scalar() or 0

    # Calculate percentage
    usage_percentage = (current_usage / tenant_config.total_storage_quota_bytes) * 100 if tenant_config.total_storage_quota_bytes > 0 else 0

    # Check thresholds
    warning_threshold = float(tenant_config.quota_warning_threshold) * 100
    alert_threshold = float(tenant_config.quota_alert_threshold) * 100

    return StorageQuotaResponse(
        tenant_id=str(tenant_uuid),
        current_usage_bytes=current_usage,
        total_quota_bytes=tenant_config.total_storage_quota_bytes,
        usage_percentage=round(usage_percentage, 2),
        is_over_warning=usage_percentage >= warning_threshold,
        is_over_alert=usage_percentage >= alert_threshold,
        is_over_quota=current_usage > tenant_config.total_storage_quota_bytes,
        warning_threshold=warning_threshold,
        alert_threshold=alert_threshold,
        cleanup_strategy=tenant_config.cleanup_strategy.value,
        trace_retention_days=tenant_config.trace_retention_days,
        artifact_retention_days=tenant_config.artifact_retention_days
    )
