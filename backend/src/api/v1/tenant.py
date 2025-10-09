"""Tenant settings endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ..middleware.auth import require_auth
from ...models import Tenant
from ...schemas.tenant_settings import (
    TenantSettingsResponse,
    TenantSettingsUpdate,
)


router = APIRouter()


def _ensure_admin(current_user: dict):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


def _safe_settings_get(t) -> dict:
    """Safely access tenant.settings, handling pre-migration cases."""
    try:
        return t.settings or {}
    except Exception:
        return {}


@router.get("", response_model=TenantSettingsResponse)
async def get_tenant(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Return current tenant details for the authenticated user."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user["tenant_id"]).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    status_val = getattr(tenant.status, 'value', tenant.status)
    return TenantSettingsResponse(
        id=tenant.id,
        name=tenant.name,
        schema_name=tenant.schema_name,
        status=status_val,
        max_users=tenant.max_users,
        max_agents=tenant.max_agents,
        max_flows=tenant.max_flows,
        settings=_safe_settings_get(tenant),
    )


@router.put("", response_model=TenantSettingsResponse)
async def update_tenant(
    update: TenantSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update current tenant settings (admin only)."""
    _ensure_admin(current_user)

    tenant = db.query(Tenant).filter(Tenant.id == current_user["tenant_id"]).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if update.name is not None:
        tenant.name = update.name
    if update.max_users is not None:
        tenant.max_users = int(update.max_users)
    if update.max_agents is not None:
        tenant.max_agents = int(update.max_agents)
    if update.max_flows is not None:
        tenant.max_flows = int(update.max_flows)
    if update.settings is not None:
        # Shallow merge; skip if settings column missing (pre-migration)
        try:
            current = tenant.settings or {}
            current.update(update.settings)
            tenant.settings = current
        except Exception:
            pass

    db.commit()
    db.refresh(tenant)

    status_val = getattr(tenant.status, 'value', tenant.status)
    return TenantSettingsResponse(
        id=tenant.id,
        name=tenant.name,
        schema_name=tenant.schema_name,
        status=status_val,
        max_users=tenant.max_users,
        max_agents=tenant.max_agents,
        max_flows=tenant.max_flows,
        settings=_safe_settings_get(tenant),
    )
