"""User model for authentication and authorization."""

from sqlalchemy import Column, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, deferred
from .base import BaseModel
from .user_role import user_roles
import enum
from datetime import datetime


class UserRole(str, enum.Enum):
    """User role enumeration."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class User(BaseModel):
    """
    User model with tenant association.

    Users belong to a single tenant and have role-based permissions.
    """

    __tablename__ = "users"

    tenant_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.MEMBER)
    is_active = Column(Boolean, nullable=False, default=True)
    # Invitation / password reset
    password_reset_token = deferred(Column(String(255), nullable=True))
    password_reset_expires = deferred(Column(DateTime, nullable=True))
    require_password_change = deferred(Column(Boolean, nullable=False, default=False))

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    chat_sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    roles = relationship(
        "Role",
        secondary=user_roles,
        primaryjoin="User.id==user_roles.c.user_id",
        secondaryjoin="Role.id==user_roles.c.role_id",
        back_populates="users",
    )

    @property
    def primary_role_slug(self) -> str:
        """
        Get the primary role slug for this user.
        Returns the highest priority role slug from the roles relationship,
        or falls back to the legacy role enum column.
        """
        if self.roles:
            # Sort by priority (descending) and return the highest priority role
            sorted_roles = sorted(self.roles, key=lambda r: r.priority, reverse=True)
            return sorted_roles[0].slug
        # Fallback to legacy role column
        return getattr(self.role, 'value', str(self.role))

    @property
    def is_super_admin(self) -> bool:
        """Check if user has super-admin role."""
        return any(r.slug == "super-admin" for r in self.roles)

    @property
    def is_tenant_admin(self) -> bool:
        """Check if user has tenant-admin or super-admin role."""
        return any(r.slug in ("super-admin", "tenant-admin") for r in self.roles)

    @property
    def is_admin_any(self) -> bool:
        """Check if user has any admin role (super-admin, tenant-admin, or admin)."""
        return any(r.slug in ("super-admin", "tenant-admin", "admin") for r in self.roles)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
