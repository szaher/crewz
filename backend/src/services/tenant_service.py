"""Tenant service for multi-tenancy management."""

import secrets
import re
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Tenant
from ..db.postgres import create_tenant_schema, drop_tenant_schema


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
