"""Tenant registration and super admin approval endpoints."""

import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime

from ...db.postgres import get_db
from ..middleware.auth import require_auth
from ...models import (
    Tenant, TenantRegistration, User
)
from ...schemas.tenant_registration import (
    TenantRegistrationRequest,
    TenantRegistrationResponse,
    RegistrationStatusResponse,
    PendingRegistrationsResponse,
    ApprovalNotesRequest,
    RejectionRequest,
    ApprovalResponse,
    TenantInfo,
    AdminUserInfo,
    SampleDataResponse
)
from ...models.tenant_registration import RegistrationStatus
from ...models.tenant import TenantStatus
from ...services.auth_service import AuthService
from ...services.tenant_service import TenantService

# Import seeder script
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from scripts.seed_sample_data import seed_sample_data


router = APIRouter()


def _ensure_super_admin(current_user: dict):
    """Ensure user is a super admin."""
    if not current_user.get("is_super_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )


def generate_temporary_password(length: int = 16) -> str:
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_schema_name(company_name: str) -> str:
    """Generate schema name from company name."""
    # Convert to lowercase, replace spaces with underscores, remove special chars
    schema = company_name.lower().replace(' ', '_')
    schema = ''.join(c for c in schema if c.isalnum() or c == '_')
    # Ensure uniqueness by appending timestamp
    from time import time
    return f"{schema}_{int(time())}"


# Public endpoints (no authentication)

@router.post("/tenants/register", response_model=TenantRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    registration: TenantRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Submit tenant registration (public endpoint).
    Creates pending registration for super admin approval.
    """
    # Check if email already registered
    existing = db.query(TenantRegistration).filter(
        TenantRegistration.admin_email == registration.admin_email
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please check your registration status or use a different email."
        )

    # Create registration
    new_registration = TenantRegistration(
        company_name=registration.company_name,
        admin_email=registration.admin_email,
        admin_name=registration.admin_name,
        reason=registration.reason,
        sample_data_requested=registration.sample_data_requested,
        company_size=registration.company_size,
        use_case=registration.use_case,
        status=RegistrationStatus.PENDING
    )

    db.add(new_registration)
    db.commit()
    db.refresh(new_registration)

    return TenantRegistrationResponse.from_orm(new_registration)


@router.get("/tenants/register/status", response_model=RegistrationStatusResponse)
async def check_registration_status(
    email: str = Query(..., description="Admin email to check"),
    db: Session = Depends(get_db)
):
    """
    Check registration status by email (public, rate-limited).
    """
    registration = db.query(TenantRegistration).filter(
        TenantRegistration.admin_email == email
    ).first()

    if not registration:
        return RegistrationStatusResponse(
            status="not_found",
            submitted_at=None,
            message="No registration found for this email"
        )

    status_messages = {
        RegistrationStatus.PENDING: "Registration pending approval",
        RegistrationStatus.APPROVED: "Registration approved! Check your email for login credentials.",
        RegistrationStatus.REJECTED: f"Registration rejected. Reason: {registration.rejection_reason}"
    }

    return RegistrationStatusResponse(
        status=registration.status.value,
        submitted_at=registration.created_at,
        message=status_messages.get(registration.status, "Unknown status")
    )


# Super admin endpoints

@router.get("/admin/tenants", response_model=list)
async def list_all_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="Filter by status: active, inactive, suspended"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    List all tenants (super admin only).
    """
    _ensure_super_admin(current_user)

    # Build query
    query = db.query(Tenant)

    # Apply filters
    if status_filter:
        query = query.filter(Tenant.status == status_filter)

    if search:
        query = query.filter(Tenant.name.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Get paginated results
    tenants = query.order_by(Tenant.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Get user counts for each tenant
    result = []
    for tenant in tenants:
        user_count = db.query(User).filter(User.tenant_id == tenant.id).count()

        status_val = getattr(tenant.status, 'value', str(tenant.status))

        result.append({
            "id": str(tenant.id),
            "name": tenant.name,
            "schema_name": tenant.schema_name,
            "status": status_val,
            "user_count": user_count,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            "api_key": tenant.api_key,
            "max_users": tenant.max_users,
            "max_agents": tenant.max_agents,
            "max_flows": tenant.max_flows,
        })

    return result


@router.get("/admin/tenants/{tenant_id}")
async def get_tenant_details(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get detailed tenant information (super admin only).
    """
    _ensure_super_admin(current_user)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Get statistics
    user_count = db.query(User).filter(User.tenant_id == tenant_id).count()

    status_val = getattr(tenant.status, 'value', str(tenant.status))

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "schema_name": tenant.schema_name,
        "status": status_val,
        "user_count": user_count,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "api_key": tenant.api_key,
        "max_users": tenant.max_users,
        "max_agents": tenant.max_agents,
        "max_flows": tenant.max_flows,
    }


@router.patch("/admin/tenants/{tenant_id}")
async def update_tenant_admin(
    tenant_id: UUID,
    name: Optional[str] = None,
    status: Optional[str] = None,
    max_users: Optional[int] = None,
    max_agents: Optional[int] = None,
    max_flows: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Update tenant settings (super admin only).
    """
    _ensure_super_admin(current_user)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Update fields
    if name is not None:
        tenant.name = name
    if status is not None:
        tenant.status = TenantStatus(status)
    if max_users is not None:
        tenant.max_users = max_users
    if max_agents is not None:
        tenant.max_agents = max_agents
    if max_flows is not None:
        tenant.max_flows = max_flows

    db.commit()
    db.refresh(tenant)

    status_val = getattr(tenant.status, 'value', str(tenant.status))

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "schema_name": tenant.schema_name,
        "status": status_val,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "api_key": tenant.api_key,
        "max_users": tenant.max_users,
        "max_agents": tenant.max_agents,
        "max_flows": tenant.max_flows,
    }


@router.get("/admin/tenants/pending", response_model=PendingRegistrationsResponse)
async def list_pending_registrations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    List pending tenant registrations (super admin only).
    """
    _ensure_super_admin(current_user)

    # Get total count
    total = db.query(TenantRegistration).filter(
        TenantRegistration.status == RegistrationStatus.PENDING
    ).count()

    # Get paginated results
    registrations = db.query(TenantRegistration).filter(
        TenantRegistration.status == RegistrationStatus.PENDING
    ).order_by(TenantRegistration.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return PendingRegistrationsResponse(
        registrations=[TenantRegistrationResponse.from_orm(r) for r in registrations],
        total=total
    )


@router.post("/admin/tenants/{registration_id}/approve", response_model=ApprovalResponse)
async def approve_registration(
    registration_id: UUID,
    approval: ApprovalNotesRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Approve tenant registration (super admin only).
    Creates tenant, admin user, and optionally loads sample data.
    """
    _ensure_super_admin(current_user)

    # Get registration
    registration = db.query(TenantRegistration).filter(
        TenantRegistration.id == registration_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    if registration.status != RegistrationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration already {registration.status.value}"
        )

    # Create tenant
    schema_name = generate_schema_name(registration.company_name)
    api_key = TenantService.generate_api_key()
    tenant = Tenant(
        name=registration.company_name,
        schema_name=schema_name,
        status=TenantStatus.ACTIVE,
        api_key=api_key
    )
    db.add(tenant)
    db.flush()

    # Generate temporary password
    temp_password = generate_temporary_password()

    # Create admin user
    admin_user = User(
        tenant_id=tenant.id,
        email=registration.admin_email,
        password_hash=AuthService.hash_password(temp_password),
        full_name=registration.admin_name,
        role="admin",
        is_active=True,
        require_password_change=True  # Force password change on first login
    )
    db.add(admin_user)
    db.flush()

    # Update registration
    registration.status = RegistrationStatus.APPROVED
    registration.approved_by = current_user["id"]
    registration.approved_at = datetime.utcnow()
    registration.tenant_id = tenant.id

    db.commit()
    db.refresh(registration)
    db.refresh(tenant)
    db.refresh(admin_user)

    # Load sample data if requested
    sample_data_loaded = False
    if registration.sample_data_requested:
        try:
            seed_sample_data(tenant.id, db)
            sample_data_loaded = True
        except Exception as e:
            # Log error but don't fail approval
            print(f"Warning: Failed to load sample data: {str(e)}")

    return ApprovalResponse(
        registration=TenantRegistrationResponse.from_orm(registration),
        tenant=TenantInfo(
            id=tenant.id,
            name=tenant.name,
            status="active"
        ),
        admin_user=AdminUserInfo(
            id=admin_user.id,
            email=admin_user.email,
            temporary_password=temp_password
        ),
        sample_data_loaded=sample_data_loaded
    )


@router.post("/admin/tenants/{registration_id}/reject", response_model=TenantRegistrationResponse)
async def reject_registration(
    registration_id: UUID,
    rejection: RejectionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Reject tenant registration (super admin only).
    """
    _ensure_super_admin(current_user)

    # Get registration
    registration = db.query(TenantRegistration).filter(
        TenantRegistration.id == registration_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    if registration.status != RegistrationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration already {registration.status.value}"
        )

    # Update registration
    registration.status = RegistrationStatus.REJECTED
    registration.rejection_reason = rejection.reason
    registration.approved_by = current_user["id"]  # Track who rejected
    registration.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(registration)

    return TenantRegistrationResponse.from_orm(registration)


@router.post("/admin/tenants/{tenant_id}/seed-data", response_model=SampleDataResponse)
async def seed_tenant_data(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Install sample data for existing tenant (admin/super admin only).
    """
    # Allow tenant admins to seed their own data
    if not current_user.get("is_super_admin", False):
        if current_user.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only seed data for your own tenant"
            )
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required"
            )

    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Load sample data
    try:
        result = seed_sample_data(tenant_id, db)
        return SampleDataResponse(
            message="Sample data installed successfully",
            sample_data=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to install sample data: {str(e)}"
        )
