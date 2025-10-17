"""Role model for authorization."""

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Index, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship

from .base import BaseModel
from .user_role import user_roles


class Role(BaseModel):
    """
    Role model for role-based access control.

    Represents a named collection of permissions. Supports both system-wide
    default roles and custom tenant-specific roles.
    """

    __tablename__ = "roles"

    # Tenant isolation (NULL for system roles)
    tenant_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Role identification
    name = Column(
        String(100),
        nullable=False,
    )
    slug = Column(
        String(100),
        nullable=False,
        index=True,
    )
    description = Column(
        Text,
        nullable=True,
    )

    # Role properties
    is_system_role = Column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_default = Column(
        Boolean,
        nullable=False,
        default=False,
    )
    priority = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Audit fields
    created_by = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="roles")
    creator = relationship("User", foreign_keys=[created_by])
    # Many-to-many with users via user_roles table
    users = relationship(
        "User",
        secondary=user_roles,
        primaryjoin="Role.id==user_roles.c.role_id",
        secondaryjoin="User.id==user_roles.c.user_id",
        back_populates="roles",
    )

    # Indexes
    __table_args__ = (
        Index("idx_roles_tenant", "tenant_id"),
        Index("idx_roles_slug", "slug"),
        # Unique constraint: system roles have globally unique slugs,
        # tenant roles unique per tenant
        # Note: COALESCE for nullable tenant_id
        # This will be added in the Alembic migration with proper SQL
    )

    def __repr__(self):
        return (
            f"<Role {self.name} (slug={self.slug}) "
            f"system={self.is_system_role} priority={self.priority}>"
        )
