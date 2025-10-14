"""Seed system roles for authorization."""

from sqlalchemy.orm import Session
from ..models.role import Role
from uuid import uuid4
import structlog

logger = structlog.get_logger(__name__)


SYSTEM_ROLES = [
    {
        "slug": "super-admin",
        "name": "Super Administrator",
        "description": "Platform super administrator with full system access",
        "is_system_role": True,
        "is_default": False,
        "priority": 1000,
    },
    {
        "slug": "tenant-admin",
        "name": "Tenant Administrator",
        "description": "Tenant administrator with full tenant management access",
        "is_system_role": True,
        "is_default": False,
        "priority": 900,
    },
    {
        "slug": "admin",
        "name": "Administrator",
        "description": "Administrator with management access within the tenant",
        "is_system_role": True,
        "is_default": False,
        "priority": 800,
    },
    {
        "slug": "member",
        "name": "Member",
        "description": "Standard member with read and execute access",
        "is_system_role": True,
        "is_default": True,
        "priority": 500,
    },
    {
        "slug": "viewer",
        "name": "Viewer",
        "description": "Read-only access to resources",
        "is_system_role": True,
        "is_default": False,
        "priority": 100,
    },
]


def seed_system_roles(db: Session) -> None:
    """
    Seed system roles if they don't exist.

    This creates the default system roles that are available across all tenants.
    System roles have tenant_id = NULL and is_system_role = True.
    """
    try:
        for role_data in SYSTEM_ROLES:
            # Check if role already exists
            existing = db.query(Role).filter(
                Role.slug == role_data["slug"],
                Role.is_system_role == True,
                Role.tenant_id == None,
            ).first()

            if not existing:
                role = Role(
                    id=uuid4(),
                    tenant_id=None,  # System role
                    slug=role_data["slug"],
                    name=role_data["name"],
                    description=role_data["description"],
                    is_system_role=role_data["is_system_role"],
                    is_default=role_data["is_default"],
                    priority=role_data["priority"],
                    created_by=None,  # System-created
                )
                db.add(role)
                logger.info("Created system role", slug=role_data["slug"])

        db.commit()
        logger.info("System roles seeded successfully")
    except Exception as e:
        logger.error("Failed to seed system roles", error=str(e))
        db.rollback()
        raise
