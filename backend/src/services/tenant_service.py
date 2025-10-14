"""Tenant service for multi-tenancy management."""

import secrets
import re
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Tenant
from ..models.tenant import TenantStatus
from ..db.postgres import create_tenant_schema, drop_tenant_schema
from datetime import datetime


class TenantService:
    """Service for tenant management and schema isolation."""

    @staticmethod
    def generate_schema_name(tenant_name: str) -> str:
        """
        Generate a valid PostgreSQL schema name from tenant name.

        Args:
            tenant_name: Human-readable tenant name

        Returns:
            Valid schema name (lowercase, alphanumeric + underscores)
        """
        # Convert to lowercase and replace spaces with underscores
        schema_name = tenant_name.lower().strip()
        schema_name = re.sub(r"[^a-z0-9_]", "_", schema_name)

        # Remove consecutive underscores
        schema_name = re.sub(r"_+", "_", schema_name)

        # Ensure it starts with a letter
        if not schema_name[0].isalpha():
            schema_name = "tenant_" + schema_name

        # Add random suffix for uniqueness
        suffix = secrets.token_hex(4)
        schema_name = f"{schema_name}_{suffix}"

        # PostgreSQL schema names max 63 characters
        if len(schema_name) > 63:
            schema_name = schema_name[:55] + "_" + suffix

        return schema_name

    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure API key for tenant.

        Returns:
            Random API key string
        """
        return f"crewai_{secrets.token_urlsafe(32)}"

    async def create_tenant(
        self,
        db: Session,
        name: str,
        max_users: int = 10,
        max_agents: int = 50,
        max_flows: int = 100,
    ) -> Tenant:
        """
        Create a new tenant with isolated PostgreSQL schema.

        Args:
            db: Database session
            name: Tenant name
            max_users: Maximum number of users
            max_agents: Maximum number of agents
            max_flows: Maximum number of flows

        Returns:
            Created Tenant object

        Raises:
            HTTPException: If tenant creation fails
        """
        # Generate unique schema name
        schema_name = self.generate_schema_name(name)

        # Check for duplicates (unlikely but possible)
        existing = db.query(Tenant).filter(Tenant.schema_name == schema_name).first()
        if existing:
            # Regenerate with new suffix
            schema_name = self.generate_schema_name(name)

        # Generate API key
        api_key = self.generate_api_key()

        # Create tenant record
        tenant = Tenant(
            name=name,
            schema_name=schema_name,
            status="active",
            api_key=api_key,
            max_users=max_users,
            max_agents=max_agents,
            max_flows=max_flows,
        )

        db.add(tenant)
        db.commit()

        # Create PostgreSQL schema
        try:
            create_tenant_schema(schema_name)
        except Exception as e:
            # Rollback tenant creation if schema creation fails
            db.delete(tenant)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create tenant schema: {str(e)}",
            )

        db.refresh(tenant)
        return tenant

    async def delete_tenant(self, db: Session, tenant_id: int) -> None:
        """
        Delete a tenant and its schema.

        Args:
            db: Database session
            tenant_id: Tenant ID

        Raises:
            HTTPException: If tenant not found
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        # Mark as deleted (soft delete)
        tenant.status = "deleted"
        db.commit()

        # Optionally drop schema (hard delete)
        # drop_tenant_schema(tenant.schema_name)

    async def suspend_tenant(self, db: Session, tenant_id: int) -> Tenant:
        """
        Suspend a tenant (disable access).

        Args:
            db: Database session
            tenant_id: Tenant ID

        Returns:
            Updated tenant

        Raises:
            HTTPException: If tenant not found
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        tenant.status = "suspended"
        db.commit()
        db.refresh(tenant)

        return tenant

    async def activate_tenant(self, db: Session, tenant_id: int) -> Tenant:
        """
        Activate a suspended tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID

        Returns:
            Updated tenant

        Raises:
            HTTPException: If tenant not found
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        tenant.status = "active"
        db.commit()
        db.refresh(tenant)

        return tenant

    async def request_tenant(
        self,
        db: Session,
        name: str,
        admin_email: str,
        admin_full_name: str,
        max_users: int = 10,
        max_agents: int = 50,
        max_flows: int = 100,
    ) -> Tenant:
        """
        Request a new tenant (creates tenant in PENDING status awaiting approval).

        Args:
            db: Database session
            name: Tenant name
            admin_email: Email of tenant admin
            admin_full_name: Full name of tenant admin
            max_users: Maximum number of users
            max_agents: Maximum number of agents
            max_flows: Maximum number of flows

        Returns:
            Created Tenant object in PENDING status

        Raises:
            HTTPException: If tenant creation fails
        """
        # Generate unique schema name
        schema_name = self.generate_schema_name(name)

        # Check for duplicates (unlikely but possible)
        existing = db.query(Tenant).filter(Tenant.schema_name == schema_name).first()
        if existing:
            # Regenerate with new suffix
            schema_name = self.generate_schema_name(name)

        # Generate API key (but don't activate until approved)
        api_key = self.generate_api_key()

        # Create tenant record in PENDING status
        tenant = Tenant(
            name=name,
            schema_name=schema_name,
            status=TenantStatus.PENDING,
            api_key=api_key,
            max_users=max_users,
            max_agents=max_agents,
            max_flows=max_flows,
            settings={
                "admin_email": admin_email,
                "admin_full_name": admin_full_name,
                "requested_at": datetime.utcnow().isoformat()
            }
        )

        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        # TODO: Send notification to super admins
        # from backend.src.db.redis import get_redis_client
        # redis_client = get_redis_client()
        # redis_client.publish("notifications:admins:tenant_requests", ...)

        return tenant

    async def approve_tenant(
        self,
        db: Session,
        tenant_id: int,
        approved_by_user_id: int
    ) -> Tenant:
        """
        Approve a pending tenant (creates schema and activates).

        Args:
            db: Database session
            tenant_id: Tenant ID
            approved_by_user_id: User ID of approver (super admin)

        Returns:
            Activated tenant

        Raises:
            HTTPException: If tenant not found or not in PENDING status
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        if tenant.status != TenantStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant is not pending approval (current status: {tenant.status.value})",
            )

        # Create PostgreSQL schema
        try:
            create_tenant_schema(tenant.schema_name)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create tenant schema: {str(e)}",
            )

        # Update tenant status
        tenant.status = TenantStatus.ACTIVE
        tenant.settings = tenant.settings or {}
        tenant.settings["approved_at"] = datetime.utcnow().isoformat()
        tenant.settings["approved_by"] = approved_by_user_id
        db.commit()
        db.refresh(tenant)

        # TODO: Send notification to tenant admin
        # Notify the admin email that their tenant is approved

        return tenant

    async def reject_tenant(
        self,
        db: Session,
        tenant_id: int,
        rejected_by_user_id: int,
        reason: Optional[str] = None
    ) -> None:
        """
        Reject a pending tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID
            rejected_by_user_id: User ID of rejector (super admin)
            reason: Optional rejection reason

        Raises:
            HTTPException: If tenant not found or not in PENDING status
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        if tenant.status != TenantStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant is not pending approval (current status: {tenant.status.value})",
            )

        # Mark as deleted (rejected)
        tenant.status = TenantStatus.DELETED
        tenant.settings = tenant.settings or {}
        tenant.settings["rejected_at"] = datetime.utcnow().isoformat()
        tenant.settings["rejected_by"] = rejected_by_user_id
        if reason:
            tenant.settings["rejection_reason"] = reason
        db.commit()

        # TODO: Send notification to tenant admin
        # Notify the admin email that their request was rejected

    async def list_pending_tenants(self, db: Session):
        """
        List all tenants awaiting approval.

        Args:
            db: Database session

        Returns:
            List of pending tenants
        """
        return db.query(Tenant).filter(Tenant.status == TenantStatus.PENDING).all()
