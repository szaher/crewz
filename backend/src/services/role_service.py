"""Role management service for RBAC."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from fastapi import HTTPException, status

from ..models import Role, Permission, User, user_roles
from ..models.permission import SubjectType, Action, Effect
from ..utils.uuid import generate_uuid_v7


class RoleService:
    """Service for managing roles and role permissions."""

    def __init__(self, db: Session):
        """Initialize role service."""
        self.db = db

    def list_roles(
        self,
        tenant_id: UUID,
        include_system: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        List roles for tenant with pagination.

        Args:
            tenant_id: Tenant ID
            include_system: Include system roles (default True)
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            {roles: [...], total: int, page: int, page_size: int}
        """
        query = self.db.query(Role)

        if include_system:
            # Include system roles (tenant_id is NULL) and tenant-specific roles
            query = query.filter(
                or_(
                    Role.tenant_id == tenant_id,
                    Role.tenant_id.is_(None)
                )
            )
        else:
            # Only tenant-specific roles
            query = query.filter(Role.tenant_id == tenant_id)

        # Order by priority descending (higher priority first)
        query = query.order_by(Role.priority.desc(), Role.name)

        total = query.count()

        # Pagination
        offset = (page - 1) * page_size
        roles = query.offset(offset).limit(page_size).all()

        return {
            "roles": roles,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create_role(
        self,
        tenant_id: UUID,
        name: str,
        slug: str,
        description: Optional[str] = None,
        is_default: bool = False,
        priority: int = 500,
    ) -> Role:
        """
        Create custom tenant role.

        Args:
            tenant_id: Tenant ID
            name: Role name
            slug: Role slug (unique per tenant)
            description: Optional description
            is_default: Whether this role is default for new users
            priority: Role priority (0-1000)

        Returns:
            Created role

        Raises:
            HTTPException: If slug already exists
        """
        # Check for duplicate slug (system roles + tenant roles)
        existing = self.db.query(Role).filter(
            or_(
                and_(Role.tenant_id == tenant_id, Role.slug == slug),
                and_(Role.tenant_id.is_(None), Role.slug == slug)
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role with slug '{slug}' already exists"
            )

        # Create role
        role = Role(
            id=generate_uuid_v7(),
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            description=description,
            is_system_role=False,
            is_default=is_default,
            priority=priority,
        )

        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)

        return role

    def get_role(
        self,
        role_id: UUID,
        tenant_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get role details with permissions and user count.

        Args:
            role_id: Role ID
            tenant_id: Tenant ID (for access control)

        Returns:
            Role with permissions list and user count

        Raises:
            HTTPException: If role not found or access denied
        """
        # Get role (system role or tenant role)
        role = self.db.query(Role).filter(
            Role.id == role_id,
            or_(
                Role.tenant_id == tenant_id,
                Role.tenant_id.is_(None)
            )
        ).first()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        # Get permissions for this role
        permissions = self.db.query(Permission).filter(
            Permission.subject_type == SubjectType.ROLE,
            Permission.subject_id == role_id,
            Permission.tenant_id == tenant_id,
        ).all()

        # Get user count
        user_count = self.db.query(func.count(user_roles.c.user_id)).filter(
            user_roles.c.role_id == role_id
        ).scalar() or 0

        return {
            "role": role,
            "permissions": permissions,
            "user_count": user_count,
        }

    def update_role(
        self,
        role_id: UUID,
        tenant_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_default: Optional[bool] = None,
        priority: Optional[int] = None,
    ) -> Role:
        """
        Update role properties.

        Args:
            role_id: Role ID
            tenant_id: Tenant ID (for access control)
            name: Updated name
            description: Updated description
            is_default: Updated default flag
            priority: Updated priority

        Returns:
            Updated role

        Raises:
            HTTPException: If role not found, system role, or access denied
        """
        # Get role (must be tenant role, not system role)
        role = self.db.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
        ).first()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system role"
            )

        # Update fields
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if is_default is not None:
            role.is_default = is_default
        if priority is not None:
            role.priority = priority

        self.db.commit()
        self.db.refresh(role)

        return role

    def delete_role(
        self,
        role_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """
        Delete role.

        Args:
            role_id: Role ID
            tenant_id: Tenant ID (for access control)

        Raises:
            HTTPException: If role not found, system role, or access denied
        """
        # Get role (must be tenant role, not system role)
        role = self.db.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
        ).first()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system role"
            )

        # Delete role (this will cascade to user_roles via SQLAlchemy relationship)
        self.db.delete(role)
        self.db.commit()

    def add_role_permission(
        self,
        role_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
        effect: str = "allow",
        conditions: Optional[Dict] = None,
    ) -> Permission:
        """
        Add permission to role.

        Args:
            role_id: Role ID
            tenant_id: Tenant ID
            resource_type: Resource type (e.g., "crew", "flow")
            resource_id: Optional specific resource ID
            action: Action (read, write, execute, delete, *)
            effect: Effect (allow, deny)
            conditions: Optional conditions dict

        Returns:
            Created permission

        Raises:
            HTTPException: If role not found or access denied
        """
        # Verify role exists and user has access
        role = self.db.query(Role).filter(
            Role.id == role_id,
            or_(
                Role.tenant_id == tenant_id,
                Role.tenant_id.is_(None)
            )
        ).first()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        # Cannot modify system role permissions directly
        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system role permissions"
            )

        # Create permission
        permission = Permission(
            id=generate_uuid_v7(),
            tenant_id=tenant_id,
            subject_type=SubjectType.ROLE,
            subject_id=role_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=Action(action),
            effect=Effect(effect),
            conditions=conditions,
        )

        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)

        return permission
