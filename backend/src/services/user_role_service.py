"""Service for managing user role assignments."""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from ..models.user import User
from ..models.role import Role
from ..models.user_role import user_roles


class UserRoleService:
    """Service for managing user-role relationships."""

    def __init__(self, db: Session):
        self.db = db

    def assign_role(
        self,
        user_id: UUID,
        role_slug: str,
        assigned_by_id: UUID,
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """
        Assign a role to a user.

        Args:
            user_id: ID of the user to assign the role to
            role_slug: Slug of the role to assign
            assigned_by_id: ID of the user making the assignment
            tenant_id: Tenant ID for tenant-specific roles (None for system roles)

        Returns:
            True if role was assigned, False if already assigned
        """
        # Find the role
        query = self.db.query(Role).filter(Role.slug == role_slug)
        if tenant_id:
            query = query.filter(Role.tenant_id == tenant_id)
        else:
            query = query.filter(Role.tenant_id == None, Role.is_system_role == True)

        role = query.first()
        if not role:
            raise ValueError(f"Role '{role_slug}' not found")

        # Check if user already has this role
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        if role in user.roles:
            return False  # Already assigned

        # Add role using direct SQL insert to user_roles table
        from sqlalchemy import insert
        stmt = insert(user_roles).values(
            user_id=user_id,
            role_id=role.id,
            assigned_by=assigned_by_id,
            assigned_at=datetime.utcnow(),
        )
        self.db.execute(stmt)
        self.db.commit()

        return True

    def remove_role(
        self,
        user_id: UUID,
        role_slug: str,
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: ID of the user to remove the role from
            role_slug: Slug of the role to remove
            tenant_id: Tenant ID for tenant-specific roles (None for system roles)

        Returns:
            True if role was removed, False if not assigned
        """
        # Find the role
        query = self.db.query(Role).filter(Role.slug == role_slug)
        if tenant_id:
            query = query.filter(Role.tenant_id == tenant_id)
        else:
            query = query.filter(Role.tenant_id == None, Role.is_system_role == True)

        role = query.first()
        if not role:
            raise ValueError(f"Role '{role_slug}' not found")

        # Check if user has this role
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        if role not in user.roles:
            return False  # Not assigned

        # Remove role using direct SQL delete from user_roles table
        from sqlalchemy import delete
        stmt = delete(user_roles).where(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == role.id,
        )
        self.db.execute(stmt)
        self.db.commit()

        return True

    def get_user_roles(self, user_id: UUID) -> List[Role]:
        """Get all roles assigned to a user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        return list(user.roles)

    def replace_user_roles(
        self,
        user_id: UUID,
        role_slugs: List[str],
        assigned_by_id: UUID,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """
        Replace all user roles with a new set.

        Args:
            user_id: ID of the user
            role_slugs: List of role slugs to assign
            assigned_by_id: ID of the user making the assignment
            tenant_id: Tenant ID for filtering tenant-specific roles
        """
        # Remove all existing roles
        from sqlalchemy import delete
        stmt = delete(user_roles).where(user_roles.c.user_id == user_id)
        self.db.execute(stmt)

        # Assign new roles
        for role_slug in role_slugs:
            self.assign_role(user_id, role_slug, assigned_by_id, tenant_id)

    def sync_legacy_role(self, user_id: UUID, assigned_by_id: UUID) -> None:
        """
        Sync the legacy role enum column to the roles relationship.
        This is a helper for migration from old role system to new.

        Args:
            user_id: ID of the user to sync
            assigned_by_id: ID of the user making the assignment (for audit)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get legacy role value
        legacy_role = getattr(user.role, 'value', str(user.role))

        # Map old role names to new slugs if needed
        role_mapping = {
            'admin': 'admin',
            'member': 'member',
            'viewer': 'viewer',
        }

        role_slug = role_mapping.get(legacy_role, 'member')

        # Assign the role if not already assigned
        try:
            self.assign_role(user_id, role_slug, assigned_by_id)
        except ValueError:
            pass  # Role might not exist yet during initial migration
